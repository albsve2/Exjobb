import cv2
import numpy as np

# Lista för pixel- och robotpunkter
pixel_points = []
robot_points = []

# Kamera
cap = cv2.VideoCapture(1)
if not cap.isOpened():
    raise RuntimeError("Kunde inte öppna kamera")

# Funktion för robust float-inmatning
def prompt_mm(prompt_text):
    while True:
        try:
            return float(input(prompt_text))
        except ValueError:
            print("❗ Ogiltigt tal, försök igen.")

# Nytt tillåtet område
ALLOWED_ZONE = ((180, 5), (400, 350))

# Muscallback
def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and len(pixel_points) < 3:
        if not (ALLOWED_ZONE[0][0] <= x <= ALLOWED_ZONE[1][0] and ALLOWED_ZONE[0][1] <= y <= ALLOWED_ZONE[1][1]):
            print(f"❌ Punkt utanför tillåtet område: ({x},{y}) ignoreras.")
            return

        print(f"Klick registrerad: pixel=({x}, {y})")
        pixel_points.append([x, y])

        # Mata in motsvarande robotkoordinater
        rx = prompt_mm(f"Ange robot X för pixelpunkt {x}, {y} (i mm): ")
        ry = prompt_mm(f"Ange robot Y för pixelpunkt {x}, {y} (i mm): ")
        robot_points.append([rx, ry])

# Visa kamerabild och samla klick
cv2.namedWindow("Klicka 3 punkter i bilden")
cv2.setMouseCallback("Klicka 3 punkter i bilden", on_mouse)

while len(pixel_points) < 3:
    ret, frame = cap.read()
    if not ret:
        continue
    vis = frame.copy()

    # Rita tillåtet område
    cv2.rectangle(vis, ALLOWED_ZONE[0], ALLOWED_ZONE[1], (0, 255, 0), 2)
    cv2.putText(vis, "Tillatet detektionsomrade", (ALLOWED_ZONE[0][0]+5, ALLOWED_ZONE[0][1]+20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    for i, pt in enumerate(pixel_points):
        cv2.circle(vis, tuple(pt), 6, (0, 0, 255), -1)
        cv2.putText(vis, f"{i+1}", (pt[0]+10, pt[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

    cv2.imshow("Klicka 3 punkter i bilden", vis)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

# Om 3 punkter registrerats, räkna ut affinitetsmatris
if len(pixel_points) == 3:
    pixel_np = np.array(pixel_points, dtype=np.float32)
    robot_np = np.array(robot_points, dtype=np.float32)

    affine_matrix = cv2.getAffineTransform(pixel_np, robot_np)
    print("\n✅ Klar! Affinitetsmatris (bild → robot mm):")
    print(affine_matrix)

    np.savetxt("affine_matrix.txt", affine_matrix)
    print("\n📝 Sparat till 'affine_matrix.txt'")
else:
    print("❌ Färre än 3 punkter angivna – ingen matris skapad.")
