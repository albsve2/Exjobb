import cv2
import numpy as np
import os

# Directories (adjust paths if needed)
input_dir = '/Users/albinsvensson/Desktop/EXJOBB/Pythonkod/Testbilder/bilder'
output_dir = '/Users/albinsvensson/Desktop/EXJOBB/Testbilder/result'
os.makedirs(output_dir, exist_ok=True)

# Get list of image files
image_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.jpg','.jpeg','.png'))]

for img_file in image_files:
    image_path = os.path.join(input_dir, img_file)
    image = cv2.imread(image_path)
    if image is None:
        print("Error loading image:", image_path)
        continue

    output_img = image.copy()
    img_h, img_w = image.shape[:2]

    # ---------- Preprocessing ----------
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Use a stronger median blur to remove small noise
    blurred = cv2.medianBlur(gray, 7)
    
    # Use Otsu's thresholding; invert if needed so that battery regions become white
    ret, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Apply morphological opening with a larger kernel to remove small dots/noise
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
    
    # ---------- Connected Components Analysis ----------
    # This will label all connected regions in the binary image
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(opening, connectivity=8)
    
    found = 0
    for i in range(1, num_labels):  # Skip background (label 0)
        area = stats[i, cv2.CC_STAT_AREA]
        if area < 500:  # Increase this threshold to ignore small dots (tweak as needed)
            continue
        
        # Get bounding box of the connected component
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        
        # Calculate aspect ratio; make sure we get the elongated value regardless of orientation
        aspect_ratio = float(w) / h if h > 0 else 0
        if aspect_ratio < 1:
            aspect_ratio = 1 / aspect_ratio
        
        # Debug output (you can print these values for tuning)
        print(f"{img_file}: Component {i} - Area: {area}, Box: ({x},{y},{w},{h}), Aspect Ratio: {aspect_ratio:.2f}")
        
        # Filter: assume battery is an elongated region (adjust ratio threshold as needed)
        if aspect_ratio < 1.5:
            continue
        
        # Draw bounding box and label it
        found += 1
        cv2.rectangle(output_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(output_img, "Battery", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    print(f"{img_file}: Detected battery-like regions: {found}")

    # Save the annotated image
    out_img_path = os.path.join(output_dir, img_file)
    cv2.imwrite(out_img_path, output_img)

cv2.destroyAllWindows()
