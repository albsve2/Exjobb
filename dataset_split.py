import os
import shutil
import random

# Källmapp med bilder och annoteringsfiler (YOLO-format)
input = "/Users/albinsvensson/Desktop/EXJOBB/captured_images/AugSmall/small"

# Utmatningsmapp för dataset-split
output = "/Users/albinsvensson/Desktop/EXJOBB/captured_images/Dataset"

# Fördelningsprocent (summan ska vara 1.0)
train_ratio = 0.7
val_ratio = 0.2
# test_ratio kommer bli 1 - train_ratio - val_ratio (dvs. 0.1)

# Skapa utmatningsmapparna: train, val, test
splits = ['train', 'val', 'test']
for split in splits:
    split_dir = os.path.join(output, split)
    os.makedirs(split_dir, exist_ok=True)

# Hämta alla bildfiler (case-insensitive filter)
image_files = [f for f in os.listdir(input) if f.lower().endswith(('.jpg', '.png'))]

for img_file in image_files:
    base_name, ext = os.path.splitext(img_file)
    # Slumpa fram en siffra för att bestämma split
    r = random.random()
    if r < train_ratio:
        split = "train"
    elif r < train_ratio + val_ratio:
        split = "val"
    else:
        split = "test"
    
    dest_folder = os.path.join(output, split)
    
    # Kopiera bildfilen
    src_img = os.path.join(input, img_file)
    dest_img = os.path.join(dest_folder, img_file)
    shutil.copy(src_img, dest_img)
    
    # Om en annoteringsfil finns kopieras den också (förväntas ha samma basnamn + .txt)
    src_txt = os.path.join(input, base_name + ".txt")
    if os.path.exists(src_txt):
        dest_txt = os.path.join(dest_folder, base_name + ".txt")
        shutil.copy(src_txt, dest_txt)

print("Uppdelning i train/val/test är klar!")