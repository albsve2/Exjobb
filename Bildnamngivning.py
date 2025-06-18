import os

# Mapp där bilderna ligger
image_folder = "/Users/albinsvensson/Desktop/EXJOBB/captured_images/AugMedium/medium"  # Ändra till rätt mapp
battery_category = "medium"  # Ändra kategori till 'small', 'medium' eller 'large'

# Hämta alla bildfiler i mappen
image_files = sorted([f for f in os.listdir(image_folder) if f.lower().endswith(('.jpg', '.png'))])

# Döp om bilderna
for index, filename in enumerate(image_files, start=1):
    new_name = f"battery_{battery_category}_{index:03d}.jpg"
    old_path = os.path.join(image_folder, filename)
    new_path = os.path.join(image_folder, new_name)
    os.rename(old_path, new_path)
    print(f"Renamed {filename} → {new_name}")

print("Alla bilder har fått nya namn!")
