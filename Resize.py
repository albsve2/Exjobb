import os
import cv2

# --- INPUT SETTINGS ---
input_folder = "/Users/albinsvensson/Desktop/EXJOBB/captured_images/Medium2"
output_folder = "/Users/albinsvensson/Desktop/EXJOBB/captured_images/Medium2"
target_size = (640, 640)  # width, height

# --- CREATE OUTPUT FOLDER IF IT DOESN'T EXIST ---
os.makedirs(output_folder, exist_ok=True)

# --- LOOP THROUGH ALL FILES ---
for filename in os.listdir(input_folder):
    if filename.lower().endswith((".jpg", ".jpeg", ".png")):
        img_path = os.path.join(input_folder, filename)
        img = cv2.imread(img_path)

        if img is not None:
            resized = cv2.resize(img, target_size)
            output_path = os.path.join(output_folder, filename)
            cv2.imwrite(output_path, resized)
            print(f"Saved: {output_path}")
        else:
            print(f"Failed to read: {img_path}")
