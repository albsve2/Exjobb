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
