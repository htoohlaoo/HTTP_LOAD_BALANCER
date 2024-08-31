import time
import threading

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
 
class ControlledThread(threading.Thread):
    def __init__(self, target=None, args=(), kwargs=None):
        super().__init__()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Initially, the thread is not paused
        self.target = target
        self.args = args
        self.kwargs = kwargs if kwargs is not None else {}

    def run(self):
        if self.target:  # Ensure there's a target function
            while not self._stop_event.is_set():
                self._pause_event.wait()  # Block if paused
                self.target(*self.args, **self.kwargs)  # Call the target function
                time.sleep(1)  # Optional: Add a sleep if necessary

    def stop(self):
        self._stop_event.set()
        self.resume()  # Resume to allow the thread to exit if paused

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

