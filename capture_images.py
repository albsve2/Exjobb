import cv2
import os
import datetime

def capture_image_from_camera(save_dir="captured_images", camera_index=0):
    # Skapa mappen om den inte redan finns
    os.makedirs(save_dir, exist_ok=True)

    # Anslut till kameran
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print("Kunde inte ansluta till kameran.")
        return

    print("Tryck på 'c' för att ta en bild. Tryck på 'q' för att avsluta.")

    while True:
        # Läs bild från kameran
        ret, frame = cap.read()

        if not ret:
            print("Kunde inte läsa från kameran.")
            break

        # Visa bilden i ett fönster
        cv2.imshow("Kamera", frame)

        # Vänta på tangenttryckning
        key = cv2.waitKey(1) & 0xFF

        # Ta bild vid tryck på 'c'
        if key == ord('c'):
            # Filnamn med tidstämpel
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"image_{timestamp}.jpg"
            filepath = os.path.join(save_dir, filename)
            cv2.imwrite(filepath, frame)
            print(f"Bild sparad: {filepath}")

        # Avsluta programmet vid tryck på 'q'
        elif key == ord('q'):
            print("Avslutar...")
            break

    # Stäng kameran och alla fönster
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    capture_image_from_camera()
