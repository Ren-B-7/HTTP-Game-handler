"""
Chess engine pool manager with auto-scaling and load balancing.

This module manages a pool of chess engine subprocess instances, distributing
game analysis tasks across available engines and scaling the engine count if
needed

Classes:
    EngineTask: Data class for engine tasks
    EngineInstance: Data class for engine process metadata
    EnginePool: Main pool manager with auto-scaling

Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
"""

import queue
import threading
import subprocess
from dataclasses import dataclass
import time
from typing import Dict, Optional
import select
import json
import traceback
import sys
import os

from .exceptions import MajorServerSideException, InstanceInoperable

# Set environment for Rust engine (limits thread pool size)
env = os.environ.copy()
if not env.get("RAYON_MAX_THREADS"):
    env["RAYON_MAX_THREADS"] = "3"  # Limit parallelism to avoid CPU saturation


@dataclass
class EngineTask:
    """
    Represents a task to send to an engine instance.

    Attributes:
        game_id: Unique identifier for the game
        message: JSON-serializable message to send to engine
        response_queue: Queue to receive the engine's response
        created_at: Unix timestamp when task was created
    """

    game_id: str
    message: dict
    response_queue: queue.Queue
    created_at: float


@dataclass
class EngineInstance:
    """
    Represents a single chess engine subprocess instance.

    Attributes:
        process: Subprocess handle for the engine
        task_queue: Queue of tasks waiting for this instance
        thread: Worker thread processing this instance's tasks
        created_at: Unix timestamp when instance was spawned
        last_used: Unix timestamp of last task completion
        tasks_processed: Total number of tasks completed by this instance
    """

    process: subprocess.Popen
    task_queue: queue.Queue
    thread: threading.Thread
    created_at: float
    last_used: float
    tasks_processed: int = 0


class EnginePool:
    """
    Manages a pool of chess engine instances with auto-scaling.

    This class provides intelligent load balancing and automatic scaling:
    - Distributes tasks to the instance with the shortest queue
    - Spawns new instances when all queues are >90% full for >5 seconds
    - Kills idle instances after 10 seconds of all queues being empty
    - Maintains minimum of min_instances (default: 1) at all times

    Auto-scaling thresholds:
        Scale UP: All instance queues >90% full for >5 seconds
        Scale DOWN: All queues empty for >10 seconds (and count > min_instances)

    Attributes:
        game_handler (str): Command to execute engine subprocess
        server_state: Server state manager for shutdown coordination
        min_instances (int): Minimum instances to keep alive
        max_instances (int): Maximum instances to spawn
        queue_size (int): Maximum tasks per instance queue
        instances (Dict[int, EngineInstance]): Active engine instances
    """

    __slots__ = (
        "game_handler",
        "server_state",
        "min_instances",
        "max_instances",
        "queue_size",
        "instances",
        "instance_counter",
        "lock",
        "queue_full_since",
        "queue_empty_since",
        "_scale_threshold_full",
        "_scale_threshold_empty",
    )

    def __init__(
        self,
        game_handler: str,
        server_state,
        min_instances=1,
        max_instances=10,
        queue_size=100,
    ):
        """
        Initialize the engine pool.

        Args:
            game_handler: Command to execute engine (can include arguments)
            server_state: ServerState instance for shutdown coordination
            min_instances: Minimum instances to keep alive (default: 1)
            max_instances: Maximum instances to spawn (default: 10)
            queue_size: Maximum tasks per instance queue (default: 100)
        """
        self.game_handler = game_handler
        self.server_state = server_state
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.queue_size = queue_size

        self.instances: Dict[int, EngineInstance] = {}
        self.instance_counter = 0
        self.lock = threading.Lock()

        # Pre-calculate scaling thresholds (90% full, 0% full)
        self._scale_threshold_full = queue_size * 0.9
        self._scale_threshold_empty = 0

        # Metrics for auto-scaling decisions
        self.queue_full_since: Optional[float] = None
        self.queue_empty_since: Optional[float] = None

        # Start minimum instances immediately
        for _ in range(min_instances):
            self._spawn_instance()

    def _spawn_instance(self) -> Optional[int]:
        """
        Spawn a new engine instance and initialize it.

        This method:
        1. Checks if we're under max_instances limit
        2. Spawns subprocess with game_handler command
        3. Sends initialization message to verify it works
        4. Creates worker thread to process tasks
        5. Adds instance to the pool

        Returns:
            int: Instance ID if successful
            None: If spawn failed or at max_instances
        """
        with self.lock:
            if len(self.instances) >= self.max_instances:
                return None

            try:
                # Spawn subprocess with pipes for communication
                process = subprocess.Popen(
                    self.game_handler.split(),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,  # Include RAYON_MAX_THREADS setting
                    text=True,  # Use text mode for easier JSON handling
                    bufsize=1,  # Line buffered
                )

                if not (process.stdin and process.stdout):
                    raise InstanceInoperable("Engine pipes not available")

                # Initialize the engine with starting position
                init_message = {
                    "reason": "ping",
                }
                process.stdin.write(json.dumps(init_message) + "\n")
                process.stdin.flush()

                # Read initialization response to verify engine is working
                response_line = process.stdout.readline()
                if not response_line:
                    raise MajorServerSideException("Engine failed to initialize")

                response = json.loads(response_line)
                if response.get("message") != "valid":
                    raise MajorServerSideException(
                        f"Engine initialization failed: {response}"
                    )

                # Create instance metadata
                instance_id = self.instance_counter
                self.instance_counter += 1

                task_queue = queue.Queue(maxsize=self.queue_size)
                now = time.time()

                # Create instance object first
                instance = EngineInstance(
                    process=process,
                    task_queue=task_queue,
                    thread=None,  # Set immediately after
                    created_at=now,
                    last_used=now,
                )

                # Create and start worker thread for this instance
                thread = threading.Thread(
                    target=self._instance_worker,
                    args=(instance_id, instance),
                    daemon=True,
                    name=f"EngineWorker-{instance_id}",
                )
                instance.thread = thread
                thread.start()

                self.instances[instance_id] = instance
                print(
                    f"✓ Spawned engine instance {instance_id} (total: {len(self.instances)})"
                )
                return instance_id

            except Exception as e:
                print(f"Failed to spawn engine instance: {e}")
                traceback.print_exc()
                return None

    def _instance_worker(self, instance_id: int, instance: EngineInstance):
        """
        Worker thread that processes tasks for a single engine instance.

        This method runs in a dedicated thread per instance and:
        1. Pulls tasks from the instance's queue
        2. Sends them to the engine subprocess
        3. Reads responses with timeout
        4. Returns results to the caller

        Args:
            instance_id: Unique ID for this instance
            instance: EngineInstance object with process and queue
        """

        def read_with_timeout(stdout, timeout=2.0):
            """
            Read a line from stdout with timeout using threading.

            This is more portable than select() which doesn't work on Windows.

            Args:
                stdout: File object to read from
                timeout: Maximum seconds to wait

            Returns:
                str: Line read from stdout
                None: If timeout occurred
            """
            result = [None]
            exception = [None]

            def read_line():
                try:
                    result[0] = stdout.readline()
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=read_line, daemon=True)
            thread.start()
            thread.join(timeout=timeout)

            if thread.is_alive():
                # Thread still running = timeout occurred
                return None

            if exception[0]:
                raise exception[0]

            return result[0]

        # Main worker loop
        while not self.server_state.should_shutdown():
            try:
                if not (instance.process.stdin and instance.process.stdout):
                    raise InstanceInoperable("Failed to read from instance")

                # Get next task with timeout to allow periodic shutdown checks
                try:
                    task: EngineTask = instance.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Update instance metrics
                instance.last_used = time.time()
                instance.tasks_processed += 1

                # Process the task
                try:
                    # Send message to engine
                    instance.process.stdin.write(json.dumps(task.message) + "\n")
                    instance.process.stdin.flush()

                    # Read response with 2 second timeout
                    response_line = read_with_timeout(
                        instance.process.stdout, timeout=2.0
                    )

                    if response_line is None:
                        # Timeout occurred - check stderr for error messages
                        if sys.platform != "win32" and instance.process.stderr:

                            ready, _, _ = select.select(
                                [instance.process.stderr], [], [], 0
                            )
                            if ready:
                                stderr_output = instance.process.stderr.readline()
                                if stderr_output:
                                    print(
                                        f"Engine {instance_id} stderr: {stderr_output.strip()}"
                                    )

                        raise MajorServerSideException(
                            "Engine did not respond within 2 seconds"
                        )

                    if not response_line:
                        raise MajorServerSideException("Engine returned empty response")

                    response = json.loads(response_line)

                    # Send successful response back to caller
                    task.response_queue.put(("success", response))

                except Exception as e:
                    print(f"Engine {instance_id} error processing task: {e}")
                    task.response_queue.put(("error", str(e)))

                finally:
                    # Always mark task as done
                    instance.task_queue.task_done()

            except InstanceInoperable:
                # Instance is dead - exit worker loop
                break
            except Exception as e:
                print(f"Engine worker {instance_id} loop error: {e}")
                time.sleep(0.1)  # Brief pause to avoid tight error loop

        print(f"Engine worker {instance_id} shutting down")
        self._close_instance(instance_id)

    def _close_instance(self, instance_id: int):
        """
        Gracefully close an engine instance.

        Args:
            instance_id: ID of instance to close
        """
        with self.lock:
            instance = self.instances.pop(instance_id, None)
            if not instance:
                return

        # Close process outside lock to avoid blocking other operations
        try:
            # Try graceful shutdown first
            if instance.process.stdin and not instance.process.stdin.closed:
                instance.process.stdin.write(
                    json.dumps({"reason": "exit", "fen": "", "moves": ""}) + "\n"
                )
                instance.process.stdin.flush()

            # Wait up to 2 seconds for clean exit
            instance.process.wait(timeout=2)
        except:
            # Forceful kill if graceful shutdown fails
            try:
                instance.process.kill()
            except:
                pass
        finally:
            # Clean up all pipes
            try:
                if instance.process.stdin:
                    instance.process.stdin.close()
                if instance.process.stdout:
                    instance.process.stdout.close()
                if instance.process.stderr:
                    instance.process.stderr.close()
            except:
                pass

        print(f"✓ Closed engine instance {instance_id}")

    def submit_task(
        self, game_id: str, message: dict, timeout: float = 5.0
    ) -> Optional[dict]:
        """
        Submit a task to the pool and wait for response.

        Args:
            game_id: Game identifier (for logging/debugging)
            message: JSON-serializable message to send to engine
            timeout: Maximum seconds to wait for response (default: 5.0)

        Returns:
            dict: Engine response if successful
            None: If submission failed, queue full, or timeout
        """
        response_queue = queue.Queue()
        task = EngineTask(
            game_id=game_id,
            message=message,
            response_queue=response_queue,
            created_at=time.time(),
        )

        # Find instance with shortest queue (single lock acquisition)
        with self.lock:
            if not self.instances:
                return None

            # Select instance with least load
            best_instance = min(
                self.instances.values(), key=lambda inst: inst.task_queue.qsize()
            )

        # Submit task outside lock to avoid blocking
        try:
            best_instance.task_queue.put(task, timeout=0.5)

            # Wait for response
            status, result = response_queue.get(timeout=timeout)

            if status == "success":
                return result
            print(f"Engine task failed: {result}")
            return None

        except queue.Full:
            print("Engine queue full!")
            return None
        except queue.Empty:
            print(f"Engine task timed out after {timeout}s")
            return None
        except Exception as e:
            print(f"Error submitting task: {e}")
            return None

    def auto_scale(self):
        """
        Check if we need to spawn or kill instances based on load.

        Scaling logic:
        - Scale UP: If all queues are >90% full for >5 seconds
        - Scale DOWN: If all queues are empty for >10 seconds (and count > min)

        This method should be called periodically (e.g., every 5 seconds)
        from a monitoring thread.
        """
        with self.lock:
            if not self.instances:
                # No instances at all - spawn at least one
                self._spawn_instance()
                return

            # Calculate aggregate queue metrics in single pass
            total_queue_size = 0
            queue_count = len(self.instances)

            for inst in self.instances.values():
                total_queue_size += inst.task_queue.qsize()

            avg_queue_size = total_queue_size / queue_count if queue_count else 0
            all_full = total_queue_size >= (queue_count * self._scale_threshold_full)
            all_empty = total_queue_size == 0

            now = time.time()

            # Scale UP logic
            if all_full:
                if self.queue_full_since is None:
                    self.queue_full_since = now
                elif now - self.queue_full_since > 5.0:
                    if len(self.instances) < self.max_instances:
                        print(f"Scaling up: avg queue size {avg_queue_size:.1f}")
                        self._spawn_instance()
                    self.queue_full_since = None
            else:
                self.queue_full_since = None

            # Scale DOWN logic
            if all_empty and len(self.instances) > self.min_instances:
                if self.queue_empty_since is None:
                    self.queue_empty_since = now
                elif now - self.queue_empty_since > 10.0:
                    # Kill oldest (least recently used) instance
                    oldest_id = min(
                        self.instances.keys(), key=lambda k: self.instances[k].last_used
                    )
                    print(f"Scaling down: killing idle instance {oldest_id}")
                    self._close_instance(oldest_id)
                    self.queue_empty_since = None
            else:
                self.queue_empty_since = None

    def get_stats(self) -> dict:
        """
        Get pool statistics for monitoring and debugging.

        Returns:
            dict: Statistics including instance count and per-instance metrics
        """
        with self.lock:
            return {
                "instance_count": len(self.instances),
                "instances": {
                    inst_id: {
                        "queue_size": inst.task_queue.qsize(),
                        "tasks_processed": inst.tasks_processed,
                        "uptime": time.time() - inst.created_at,
                        "idle_time": time.time() - inst.last_used,
                    }
                    for inst_id, inst in self.instances.items()
                },
            }

    def shutdown(self):
        """
        Shutdown all instances gracefully.

        This method closes all instances and should be called during
        server shutdown to ensure clean termination of subprocesses.
        """
        with self.lock:
            instance_ids = list(self.instances.keys())

        for instance_id in instance_ids:
            self._close_instance(instance_id)
