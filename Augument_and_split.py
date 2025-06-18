import os
import cv2
import albumentations as A

#  Antal augmenteringar per bild
NUM_AUGS = 5

#  Källmapp med originalbilder och YOLO-annoteringar
image_dir = "/Users/albinsvensson/Desktop/EXJOBB/captured_images/Medium"
output_dir = "/Users/albinsvensson/Desktop/EXJOBB/captured_images/AugMedium"

# Mappning mellan klass-ID och namn
class_map = {
    0: "small",
    1: "medium",
    2: "large"
}

# Avancerad augmenteringspipeline
transform = A.Compose([
    A.HorizontalFlip(p=0.5),
    A.VerticalFlip(p=0.3),
    A.RandomBrightnessContrast(p=0.4),
    A.HueSaturationValue(hue_shift_limit=15, sat_shift_limit=20, val_shift_limit=10, p=0.4),
    A.GaussianBlur(blur_limit=(3, 5), p=0.3),
    A.GaussNoise(var_limit=(10.0, 40.0), p=0.3),
    A.RandomShadow(p=0.2),
    A.CLAHE(p=0.3),
    A.Rotate(limit=25, p=0.4),
    A.MotionBlur(blur_limit=(3, 5), p=0.3),
    A.Perspective(p=0.3),
], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_visibility=0.3))

# Gå igenom alla bilder
images = [f for f in os.listdir(image_dir) if f.endswith(('.jpg', '.png'))]

for img_name in images:
    base_name = os.path.splitext(img_name)[0]
    img_path = os.path.join(image_dir, img_name)
    txt_path = os.path.join(image_dir, base_name + ".txt")

    image = cv2.imread(img_path)
    if image is None or not os.path.exists(txt_path):
        continue

    # Läs YOLO-annoteringar
    bboxes = []
    class_labels = []
    with open(txt_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            class_id = int(parts[0])
            box = list(map(float, parts[1:5]))
            bboxes.append(box)
            class_labels.append(class_id)

    # Generera augmenteringar
    for i in range(NUM_AUGS):
        try:
            augmented = transform(image=image, bboxes=bboxes, class_labels=class_labels)
            aug_img = augmented['image']
            aug_bboxes = augmented['bboxes']
            aug_labels = augmented['class_labels']
        except Exception as e:
            print(f"Fel i {img_name}: {e}")
            continue
        
        # En undermapp för varje klass
        for label in set(aug_labels):
            class_name = class_map.get(label, f"class_{label}")
            class_folder = os.path.join(output_dir, class_name)
            os.makedirs(class_folder, exist_ok=True)

            aug_img_name = f"{base_name}_aug_{i}.jpg"
            aug_txt_name = f"{base_name}_aug_{i}.txt"

            # Spara bilden
            cv2.imwrite(os.path.join(class_folder, aug_img_name), aug_img)

            # Spara etiketter (endast för denna klass)
            with open(os.path.join(class_folder, aug_txt_name), "w") as f:
                for bbox, class_id in zip(aug_bboxes, aug_labels):
                    if class_id == label:
                        f.write(f"{class_id} {' '.join(map(str, bbox))}\n")

print("Alla augmentationer är klara och sparade i klassmappar.")
