import http.server
import threading
import time


class MajorThreadedHttpServerException(Exception):
    """
    ThreadingHTTPServer has encountered a major server side exception
    Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
    """

    pass


class TimeoutThreadingHTTPServer(http.server.ThreadingHTTPServer):
    last_activity_time = time.time()
    inactivity_timeout = 60 * 5
    timeout = False
    stopping = False

    def __init__(self, server_address: tuple, RequestHandlerClass) -> None:
        try:
            super().__init__(server_address, RequestHandlerClass)
        except:
            raise MajorThreadedHttpServerException("Unable to initiate server class")

    def server_activate(self) -> None:
        """
        Starts the server and spawns a separate thread to monitor inactivity.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            super().server_activate()
            threading.Thread(target=self.monitor_inactivity).start()
            self.last_activity_time = time.time()
        except:
            raise MajorThreadedHttpServerException("Unable to start server")

    def process_request(self, request, client_address) -> None:
        """
        Processes an incoming request and updates the last activity timestamp.

        This method is called to handle each incoming request to the server. It
        updates the `last_activity_time` to the current time to indicate that there
        has been recent activity, and then delegates the actual processing of the
        request to the parent class's `process_request` method.

        Parameters:
            request: The incoming request to be processed.
            client_address: The address of the client making the request.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        try:
            self.last_activity_time = time.time()
            super().process_request(request, client_address)
        except:
            raise MajorThreadedHttpServerException("Unable to process request")

    def monitor_inactivity(self) -> None:
        """
        Monitors server inactivity and shuts it down if it has been idle for too long.

        This method runs in its own thread and continuously checks if the server
        has been idle for longer than the specified inactivity timeout. If it has,
        it prints a message, sets the timeout flag and shuts down the server.

        The inactivity timeout is in seconds and defaults to 5 minutes.

        Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
        """
        while not (self.stopping):
            # Check if the server has been idle for too long
            if time.time() - self.last_activity_time > self.inactivity_timeout:
                print("No activity for 5 minutes, shutting down the server.")
                self.timeout = True
                break
            time.sleep(15)  # Check every 15 seconds
        self.shutdown()
