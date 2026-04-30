import json, time, logging, cv2
from drone import DroneController
from vision import analyze_frame
from llm import plan_next_commands
from safety import SafetyWatchdog

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def refresh_window(drone):
    """Helper to keep the OpenCV window alive on macOS."""
    frame = drone.get_frame()
    if frame is not None:
        cv2.imshow("Tello Live Feed", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return False
    return True

def execute_command(drone: DroneController, cmd: dict) -> bool:
    c = cmd["cmd"]
    log.info(f"▶ Executing: {cmd}")
    try:
        # Keep window alive during motor commands
        refresh_window(drone)

        if c == "takeoff":        drone.takeoff()
        elif c == "land":         drone.land(); return False
        elif c == "hover":        drone.hover(cmd["seconds"])
        elif c == "move":         drone.move(cmd["direction"], cmd["cm"])
        elif c == "rotate":       drone.rotate(cmd["direction"], cmd["degrees"])
        
    except Exception as e:
        log.error(f"❌ Command failed: {e}")
    return True

def run_mission(goal: str):
    drone = DroneController()
    watchdog = SafetyWatchdog(drone)
    drone.connect()
    watchdog.start()

    try:
        drone.takeoff()
        while True:
            watchdog.check()

            # 1. Sense & Display (Keeping the window alive)
            # We refresh multiple times to clear the Tello's internal buffer
            for _ in range(5):
                if not refresh_window(drone):
                    drone.land()
                    return

            frame = drone.get_frame()
            if frame is None: continue

            # 2. Perceive
            log.info("🤔 AI analyzing scene...")
            vision = analyze_frame(frame, goal, drone.get_telemetry())
            
            # Refresh again so the window doesn't go white during planning
            refresh_window(drone)

            # 3. Reason
            commands = plan_next_commands(goal, drone.get_telemetry(), vision)
            
            # 4. Act
            for cmd in commands:
                if not execute_command(drone, cmd):
                    log.info("✅ Mission complete.")
                    return

    except Exception as e:
        log.error(f"Error: {e}")
        drone.land()
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    goal = input("Enter mission goal: ")
    run_mission(goal)