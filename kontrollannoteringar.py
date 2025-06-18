import cv2
import os

# Ange mappvägar
dataset_folder = "/Users/albinsvensson/Desktop/EXJOBB/captured_images/AugMedium/medium"
image_folder = os.path.join(dataset_folder, "/Users/albinsvensson/Desktop/EXJOBB/captured_images/AugMedium/medium")
label_folder = os.path.join(dataset_folder, "/Users/albinsvensson/Desktop/EXJOBB/captured_images/AugMedium/medium")

# Läs klasser
classes = ["Small", "Medium"]

# Visa varje bild med bounding boxes
for image_name in os.listdir(image_folder):
    if image_name.endswith(".jpg"):
        image_path = os.path.join(image_folder, image_name)
        label_path = os.path.join(label_folder, image_name.replace(".jpg", ".txt"))

        image = cv2.imread(image_path)
        h, w, _ = image.shape

        with open(label_path, "r") as f:
            for line in f.readlines():
                class_id, x_center, y_center, width, height = map(float, line.split())
                x1 = int((x_center - width / 2) * w)
                y1 = int((y_center - height / 2) * h)
                x2 = int((x_center + width / 2) * w)
                y2 = int((y_center + height / 2) * h)

                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(image, classes[int(class_id)], (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow("Annotated Image", image)
        cv2.waitKey(0)

cv2.destroyAllWindows()
