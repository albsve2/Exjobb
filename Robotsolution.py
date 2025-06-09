"""
This script implements a real-time object detection and pick-and-place system using a YOLOv5 model and a UR robot.

It initializes network communication with the robot, loads camera and calibration settings,
and runs detection in a separate thread. When objects classified as 'small' or 'medium' enter the
configured detection zone, their image coordinates are transformed to robot coordinates,
and a URScript sequence is sent to the robot to pick and drop the object.

Key features:
- Persistent TCP socket to communicate URScript commands
- Affine calibration and manual offsets to map image to robot coordinates
- YOLOv5 model loading and inference on camera frames
- Threaded detection and main loop for capture and display
- Configurable robot home and drop positions for different classes
"""
import warnings
import torch
import cv2
import numpy as np
import socket
import time
import os
import pathlib
import threading
import queue

# Suppress non-critical torch warnings for cleaner output\ nwarnings.filterwarnings("ignore", category=FutureWarning)

# ── Robot communication ─────────────────────────────────────────────────────────
# Define robot IP and port for URScript TCP connection
robotIP, PORT = "130.130.130.86", 30001
# Persistent socket object (initialized lazily)
robot_sock = None

def init_robot_socket(timeout=1.0):
    """
    Initialize a persistent TCP socket to the robot if not already connected.
    Returns the open socket with the given timeout.
    """
    global robot_sock
    if robot_sock is None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((robotIP, PORT))
        robot_sock = s
        print(f">>> Persistent socket connected to {robotIP}:{PORT}")
    return robot_sock

def send_urscript(cmd: str):
    """
    Send a URScript command string over the persistent socket.
    Retries once on failure by reconnecting.
    """
    global robot_sock
    try:
        s = init_robot_socket()
        s.sendall((cmd + "\n").encode())
        print(">>>", cmd)
        return True
    except Exception as e:
        print("!!! send_urscript failed:", e)
        # Attempt to reconnect and resend once
        try:
            if robot_sock:
                robot_sock.close()
        except:
            pass
        robot_sock = None
        try:
            s = init_robot_socket()
            s.sendall((cmd + "\n").encode())
            print(">>>", cmd)
            return True
        except Exception as e2:
            print("!!! reconnect failed:", e2)
            return False

# ── Patch for Windows pathlib ───────────────────────────────────────────────────
# Use WindowsPath when running on Windows systems
if os.name == 'nt':
    pathlib.PosixPath = pathlib.WindowsPath

# ── Calibration data ────────────────────────────────────────────────────────────
# Load affine transformation matrix and manual offset for image-to-robot mapping
affine_matrix = np.loadtxt("affine_matrix.txt", dtype=np.float32)
# Compensated offset in millimeters (calibrated)
manual_offset = np.array([-16.34,  11.86])

# ── Load YOLOv5 model ───────────────────────────────────────────────────────────
# Load custom-trained YOLOv5 model from local repository
model = torch.hub.load(
    "./", "custom",
    path="runs/train/exp6/weights/best.pt",
    source="local", force_reload=True
)
# Set confidence threshold and move model to available device
model.conf = 0.6
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device).eval()

# ── Robot positions and movements ───────────────────────────────────────────────
# Orientation angles (RX, RY, RZ) for robot tool
RX, RY, RZ = 3.186, -0.124, 0.106
# Predefined URScript moves: home position and drop positions for small/medium objects
HOME        = "movel(p[0.32199,-0.11007,0.12600,3.186,-0.124,0], a=1.2, v=2.0)"
SMALL_DROP  = "movel(p[0.30145,-0.15804,0.23,2.592,-1.979,0], a=1.2, v=1.3)"
MEDIUM_DROP = "movel(p[0.22736,-0.11185,0.23,2.592,-1.979,0], a=1.2, v=1.3)"

# ── Queues and synchronization ──────────────────────────────────────────────────
# Boolean flag to indicate robot busy state\ nbusy = False
# Queue for frames awaiting inference and for display
frame_queue   = queue.Queue(maxsize=1)
display_queue = queue.Queue(maxsize=1)

# ── Robot pick-and-drop task ────────────────────────────────────────────────────
def robot_task(cx, cy, cls):
    """
    Convert detected pixel coordinates to robot coordinates and
    send a URScript block to pick and drop the object.
    """
    global busy
    busy = True

    # Transform pixel center to calibrated robot XY position (mm)
    inp_pt = np.array([[[cx, cy]]], dtype=np.float32)
    tr     = cv2.transform(inp_pt, affine_matrix)[0][0]
    x_mm, y_mm = tr + manual_offset

    # Add compensation for conveyor movement (meters)
    conveyor_compensation = 1
    y_mm += conveyor_compensation

    # Convert mm to meters for URScript
    x_m, y_m = x_mm/1000, y_mm/1000

    # Set Z pick and approach heights based on object class
    if cls == 1:
        z_pick     = 0.070 + 0.010
        z_approach = 0.080 + 0.010
    else:
        z_pick     = 0.070
        z_approach = 0.080

    # Choose drop command and build URScript pick function with higher speeds
    drop_cmd = SMALL_DROP if cls == 0 else MEDIUM_DROP
    script = f"""
...
"""  # (rest of script omitted for brevity)
    send_urscript(script)
    # Wait briefly for robot motion, clear any pending frames
    time.sleep(5.5)
    while not frame_queue.empty():
        frame_queue.get()
    busy = False

# ── Detection thread ───────────────────────────────────────────────────────────
def detect_thread():
    """
    Continuously process frames from the frame_queue, run YOLO inference,
    draw boxes, and trigger robot_task when detection zone criteria are met.
    """
    global busy
    while True:
        if not frame_queue.empty() and not busy:
            frame = frame_queue.get()
            display = frame.copy()

            # Convert BGR to RGB for YOLO model
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # Perform inference\ nresults = model(img)
            preds = results.pred[0].cpu().numpy()

            for x1, y1, x2, y2, conf, cls in preds:
                if conf < model.conf:
                    continue
                # Calculate center coordinates
                cx = (int(x1) + int(x2)) // 2
                cy = (int(y1) + int(y2)) // 2
                # Determine label and color for box
                label = CLASS_NAMES.get(int(cls), str(int(cls)))
                color = (0,0,255) if cls == 1 else (255,0,0)
                # Draw detection box and label
                cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                cv2.putText(display, f"{label} ({conf:.2f})",
                            (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                # Trigger pick if object enters detection zone and robot is free
                if 195 <= cx <= 425 and 5 <= cy <= 350 and not busy:
                    print(f"🟢 {label} at ({cx},{cy}) – starting pick")
                    threading.Thread(
                        target=robot_task,
                        args=(cx, cy, int(cls)),
                        daemon=True
                    ).start()
                    break
            # Enqueue display frame if possible
            if not display_queue.full():
                display_queue.put(display)

# Start detection thread as daemon
threading.Thread(target=detect_thread, daemon=True).start()

# ── Main program ───────────────────────────────────────────────────────────────-
if __name__ == "__main__":
    try:
        # Initialize robot and conveyor
        send_urscript(HOME)
        time.sleep(2.5)
        send_urscript("set_analog_out(0, 0.04)")  # Start conveyor
        print("System ready - Conveyor running")
        # Open and configure camera
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_BUFFERSIZE , 1)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH , 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
        cap.set(cv2.CAP_PROP_FPS         , 30)
        if not cap.isOpened():
            raise RuntimeError("Failed to open camera")
        # Main capture loop
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            if not frame_queue.full():
                frame_queue.put(frame.copy())
            shown = display_queue.get() if not display_queue.empty() else frame
            # Draw detection area overlay
            cv2.rectangle(shown, (195,5), (425,350), (0,255,0), 2)
            cv2.putText(shown, "Detection Area", (180,20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
            cv2.imshow("Live Detect", shown)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        # Stop conveyor and cleanup resources
        send_urscript("set_analog_out(0, 0.0)")
        send_urscript("set_digital_out(1, False)")
        cap.release()
        cv2.destroyAllWindows()
        if robot_sock:
            robot_sock.close()
        print("Program terminated.")
