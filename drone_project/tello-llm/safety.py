# safety.py
import threading, sys
from pynput import keyboard  # pip install pynput

class SafetyWatchdog:
    def __init__(self, drone_controller):
        self.drone = drone_controller
        self.abort = threading.Event()

    def start(self):
        """Start a background thread listening for ESC key."""
        t = threading.Thread(target=self._listen, daemon=True)
        t.start()

    def _listen(self):
        def on_press(key):
            if key == keyboard.Key.esc:
                print("\n🚨 ABORT triggered — landing now")
                self.abort.set()
                self.drone.emergency()
                sys.exit(0)

        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()

    def check(self):
        """Call this in your main loop to respect abort signal."""
        if self.abort.is_set():
            raise InterruptedError("Abort signal received")