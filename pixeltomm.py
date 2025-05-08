import cv2
import math

# Global lista för klickade punkter
points = []

def click_event(event, x, y, flags, param):
    global points

    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(f"Punkt markerad: ({x}, {y})")

        if len(points) == 2:
            # Beräkna avstånd i pixlar
            dx = points[1][0] - points[0][0]
            dy = points[1][1] - points[0][1]
            pixel_distance = math.sqrt(dx**2 + dy**2)

            # Ange verklig längd i mm mellan punkterna
            real_distance_mm = float(input("Skriv in det verkliga avståndet mellan punkterna (i mm): "))
            mm_per_pixel = real_distance_mm / pixel_distance

            print(f"\nPixelavstånd: {pixel_distance:.2f} pixlar")
            print(f"mm/pixel: {mm_per_pixel:.4f} mm/pixel")

            # Avsluta
            cv2.destroyAllWindows()

# Starta kameran
cap = cv2.VideoCapture(1)
if not cap.isOpened():
    print("Kunde inte öppna kameran.")
    exit()

ret, frame = cap.read()
if not ret:
    print("Kunde inte läsa bild.")
    cap.release()
    exit()

cv2.imshow("Klicka på två punkter", frame)
cv2.setMouseCallback("Klicka på två punkter", click_event)
cv2.waitKey(0)

cap.release()
