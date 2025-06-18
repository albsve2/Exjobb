import os
import shutil
import random

# Ange mappvägar
image_folder = "path_to_images"
label_folder = "path_to_labels"
dataset_folder = "dataset"

# Skapa mappstruktur
for split in ["train", "val", "test"]:
    os.makedirs(os.path.join(dataset_folder, "images", split), exist_ok=True)
    os.makedirs(os.path.join(dataset_folder, "labels", split), exist_ok=True)

# Lista bilder och dela in i train/val/test
images = [f for f in os.listdir(image_folder) if f.endswith('.jpg')]
random.shuffle(images)

train_split = int(0.7 * len(images))
val_split = int(0.9 * len(images))

train_images = images[:train_split]
val_images = images[train_split:val_split]
test_images = images[val_split:]

# Flytta filer till rätt mappar
for image in train_images:
    shutil.move(os.path.join(image_folder, image), os.path.join(dataset_folder, "images/train", image))
    shutil.move(os.path.join(label_folder, image.replace(".jpg", ".txt")), os.path.join(dataset_folder, "labels/train", image.replace(".jpg", ".txt")))

for image in val_images:
    shutil.move(os.path.join(image_folder, image), os.path.join(dataset_folder, "images/val", image))
    shutil.move(os.path.join(label_folder, image.replace(".jpg", ".txt")), os.path.join(dataset_folder, "labels/val", image.replace(".jpg", ".txt")))

for image in test_images:
    shutil.move(os.path.join(image_folder, image), os.path.join(dataset_folder, "images/test", image))
    shutil.move(os.path.join(label_folder, image.replace(".jpg", ".txt")), os.path.join(dataset_folder, "labels/test", image.replace(".jpg", ".txt")))

print("Datasetet är organiserat!")
