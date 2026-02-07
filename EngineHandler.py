import queue
import threading
import subprocess
from dataclasses import dataclass
import time
from typing import Dict, Optional
import json
import traceback


class MajorServerSideException(Exception):
    """Custom exception to signal extreme cli game fault."""


class InstanceInoperable(Exception):
    """In the event that an instance drops off."""


@dataclass
class EngineTask:
    """Represents a task to send to an engine instance."""

    game_id: str
    message: dict
    response_queue: queue.Queue
    created_at: float


@dataclass
class EngineInstance:
    """Represents a single chess engine instance."""

    process: subprocess.Popen
    task_queue: queue.Queue
    thread: threading.Thread
    created_at: float
    last_used: float
    tasks_processed: int = 0


class EnginePool:
    """
    Manages a pool of chess engine instances.

    Features:
    - Distributes tasks across available instances
    - Spawns new instances when queues are full for >5 seconds
    - Kills idle instances after 10 seconds of inactivity
    - Minimum 1 instance always running
    """

    __slots__ = ('game_handler', 'server_state', 'min_instances', 'max_instances',
                 'queue_size', 'instances', 'instance_counter', 'lock',
                 'queue_full_since', 'queue_empty_since', '_scale_threshold_full',
                 '_scale_threshold_empty')

    def __init__(
        self,
        game_handler: str,
        server_state,
        min_instances=1,
        max_instances=10,
        queue_size=100,
    ):
        self.game_handler = game_handler
        self.server_state = server_state
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.queue_size = queue_size

        self.instances: Dict[int, EngineInstance] = {}
        self.instance_counter = 0
        self.lock = threading.Lock()

        # Pre-calculate thresholds
        self._scale_threshold_full = queue_size * 0.9
        self._scale_threshold_empty = 0

        # Metrics for auto-scaling
        self.queue_full_since: Optional[float] = None
        self.queue_empty_since: Optional[float] = None

        # Start minimum instances
        for _ in range(min_instances):
            self._spawn_instance()

    def _spawn_instance(self) -> Optional[int]:
        """Spawn a new engine instance. Returns instance ID or None on failure."""
        with self.lock:
            if len(self.instances) >= self.max_instances:
                return None

            try:
                process = subprocess.Popen(
                    self.game_handler.split(),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )

                if not (process.stdin and process.stdout):
                    raise InstanceInoperable("Engine pipes not available")

                # Initialize the engine
                init_message = {
                    "reason": "start",
                    "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                    "moves": "",
                }
                process.stdin.write(json.dumps(init_message) + "\n")
                process.stdin.flush()

                # Read initialization response
                response_line = process.stdout.readline()
                if not response_line:
                    raise MajorServerSideException("Engine failed to initialize")

                response = json.loads(response_line)
                if response.get("message") != "valid":
                    raise MajorServerSideException(
                        f"Engine initialization failed: {response}"
                    )

                # Create instance object
                instance_id = self.instance_counter
                self.instance_counter += 1

                task_queue = queue.Queue(maxsize=self.queue_size)
                now = time.time()

                # Create instance first
                instance = EngineInstance(
                    process=process,
                    task_queue=task_queue,
                    thread=None,  # Will be set immediately after
                    created_at=now,
                    last_used=now,
                )

                # Create and start worker thread
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
        """Worker thread that processes tasks for a single engine instance."""
        while not self.server_state.should_shutdown():
            try:
                if not (instance.process.stdin and instance.process.stdout):
                    raise InstanceInoperable("Failed to read from instance")
                
                try:
                    task: EngineTask = instance.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Update metrics (no lock needed - atomic operations)
                instance.last_used = time.time()
                instance.tasks_processed += 1

                # Process task
                try:
                    # Send message to engine
                    instance.process.stdin.write(json.dumps(task.message) + "\n")
                    instance.process.stdin.flush()

                    # Read response
                    response_line = instance.process.stdout.readline()
                    if not response_line:
                        raise MajorServerSideException("Engine did not respond")

                    response = json.loads(response_line)

                    # Send response back
                    task.response_queue.put(("success", response))

                except Exception as e:
                    print(f"Engine {instance_id} error processing task: {e}")
                    task.response_queue.put(("error", str(e)))

                finally:
                    instance.task_queue.task_done()
                    
            except InstanceInoperable:
                break
            except Exception as e:
                print(f"Engine worker {instance_id} loop error: {e}")
                time.sleep(0.1)

        print(f"Engine worker {instance_id} shutting down")
        self._close_instance(instance_id)

    def _close_instance(self, instance_id: int):
        """Close an engine instance."""
        with self.lock:
            instance = self.instances.pop(instance_id, None)
            if not instance:
                return

        # Close process outside lock
        try:
            if instance.process.stdin and not instance.process.stdin.closed:
                instance.process.stdin.write(
                    json.dumps({"reason": "exit", "fen": "", "moves": ""}) + "\n"
                )
                instance.process.stdin.flush()

            instance.process.wait(timeout=2)
        except:
            try:
                instance.process.kill()
            except:
                pass
        finally:
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
            game_id: Game identifier
            message: Message to send to engine
            timeout: Max time to wait for response

        Returns:
            Engine response dict or None on error
        """
        response_queue = queue.Queue()
        task = EngineTask(
            game_id=game_id,
            message=message,
            response_queue=response_queue,
            created_at=time.time(),
        )

        # Find instance with shortest queue (read lock once)
        with self.lock:
            if not self.instances:
                return None
            
            # Find best instance
            best_instance = min(
                self.instances.values(),
                key=lambda inst: inst.task_queue.qsize()
            )

        # Submit task (outside lock)
        try:
            best_instance.task_queue.put(task, timeout=0.5)

            # Wait for response
            status, result = response_queue.get(timeout=timeout)

            if status == "success":
                return result
            else:
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
        """Check if we need to spawn or kill instances based on load."""
        with self.lock:
            if not self.instances:
                self._spawn_instance()
                return

            # Check queue states (single pass)
            total_queue_size = 0
            queue_count = len(self.instances)
            
            for inst in self.instances.values():
                qsize = inst.task_queue.qsize()
                total_queue_size += qsize

            avg_queue_size = total_queue_size / queue_count if queue_count else 0
            all_full = total_queue_size >= (queue_count * self._scale_threshold_full)
            all_empty = total_queue_size == 0

            now = time.time()

            # Scale up if queues full for >5 seconds
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

            # Scale down if queues empty for >10 seconds AND we have more than min
            if all_empty and len(self.instances) > self.min_instances:
                if self.queue_empty_since is None:
                    self.queue_empty_since = now
                elif now - self.queue_empty_since > 10.0:
                    # Kill oldest instance
                    oldest_id = min(
                        self.instances.keys(), 
                        key=lambda k: self.instances[k].last_used
                    )
                    print(f"Scaling down: killing idle instance {oldest_id}")
                    self._close_instance(oldest_id)
                    self.queue_empty_since = None
            else:
                self.queue_empty_since = None

    def get_stats(self) -> dict:
        """Get pool statistics."""
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
        """Shutdown all instances."""
        with self.lock:
            instance_ids = list(self.instances.keys())

        for instance_id in instance_ids:
            self._close_instance(instance_id)
