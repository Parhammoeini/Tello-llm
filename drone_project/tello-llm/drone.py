from djitellopy import Tello
import logging, time
import threading

log = logging.getLogger(__name__)

class DroneController:
    def __init__(self):
        self.tello = Tello()
        self.is_flying = False
        self.current_frame = None
        self.keep_recording = True

    def _video_thread(self):
        """Background thread to update the current_frame variable."""
        # Get the frame reader
        frame_read = self.tello.get_frame_read()
        while self.keep_recording:
            if frame_read.frame is not None:
                self.current_frame = frame_read.frame
            time.sleep(0.01) # Avoid maxing out CPU

    def connect(self):
        self.tello.connect()
        self.tello.streamon() 
        log.info("Warming up camera...")
        time.sleep(2.0) 
        
        # Start the background frame fetcher
        self.video_thread = threading.Thread(target=self._video_thread)
        self.video_thread.daemon = True
        self.video_thread.start()
        log.info(f"Battery: {self.tello.get_battery()}%")

    def get_telemetry(self) -> dict:
        return {
            "battery": self.tello.get_battery(),
            "height": self.tello.get_height(),
            "temp": self.tello.get_temperature(),
            "yaw": self.tello.get_yaw(),
        }

    def get_frame(self):
        return self.current_frame

    def takeoff(self):
        self.tello.takeoff()
        self.is_flying = True

    def land(self):
        self.keep_recording = False
        self.tello.land()
        self.is_flying = False

    def move(self, direction: str, cm: int):
        getattr(self.tello, f"move_{direction}")(cm)

    def rotate(self, direction: str, degrees: int):
        if direction == "cw":
            self.tello.rotate_clockwise(degrees)
        else:
            self.tello.rotate_counter_clockwise(degrees)

    def hover(self, seconds: float):
        time.sleep(seconds)