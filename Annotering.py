import cv2
import os
#ÄNDRA KLASS ID
# Setup paths and folders
image_folder = "/Users/albinsvensson/Desktop/EXJOBB/mini"
output_folder = "/Users/albinsvensson/Desktop/EXJOBB/mini"
os.makedirs(output_folder, exist_ok=True)

# List images (sorted alphabetically)
images = sorted([f for f in os.listdir(image_folder) if f.lower().endswith(('.jpg', '.png'))])
print(f"Found {len(images)} images.")

# Initialize globals for annotation
bbox = []         # Will hold two points: top-left and bottom-right
bboxes = []       # List of all bounding boxes in the current image
drawing = False   # Flag when mouse button is pressed
annotation_ready = False  # True when a complete bbox is drawn
current_image_name = ""
class_id = 0      # Default class ID
current_index = 0 # Index for image list

def draw_bbox(event, x, y, flags, param):
    global bbox, drawing, img, annotation_ready
    # When left button is pressed, record the first point and clear any existing bbox
    if event == cv2.EVENT_LBUTTONDOWN:
        bbox = [(x, y)]
        drawing = True
        annotation_ready = False

    # While moving the mouse (and holding the button) show the preview rectangle
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        temp_img = img.copy()
        cv2.rectangle(temp_img, bbox[0], (x, y), (0, 255, 0), 2)
        cv2.imshow("Image", temp_img)

    # When button is released, record the second point and draw the final rectangle
    elif event == cv2.EVENT_LBUTTONUP:
        bbox.append((x, y))
        drawing = False
        annotation_ready = True
        bboxes.append((bbox[0], bbox[1], class_id))  # Save with class ID
        cv2.rectangle(img, bbox[0], bbox[1], (0, 255, 0), 2)
        cv2.imshow("Image", img)

def load_image(index):
    global img, orig_img, current_image_name, bboxes
    current_image_name = images[index]
    orig_img = cv2.imread(os.path.join(image_folder, current_image_name))

    if orig_img is None:
        print("Failed to load", current_image_name)
        return False

    img = orig_img.copy()
    bboxes = []  # Reset bounding boxes for each image
    return True

while current_index < len(images):
    if not load_image(current_index):
        current_index += 1
        continue

    cv2.namedWindow("Image", cv2.WINDOW_NORMAL)
    cv2.imshow("Image", img)
    cv2.setMouseCallback("Image", draw_bbox)

    print(f"Annotating image {current_index + 1} of {len(images)}: {current_image_name}")
    print("Draw bounding box, then press:")
    print("  S - Save annotation")
    print("  R - Reset drawing")
    print("  N - Skip annotation for this image")
    print("  B - Go back to previous image")
    print("  Q - Quit")
    print("  1/2/3 - Change class ID (small/medium/large)")

    while True:
        key = cv2.waitKey(0) & 0xFF
        
        # Save annotation if 's' is pressed
        if key == ord('s'):
            if len(bboxes) > 0:
                base, ext = os.path.splitext(current_image_name)
                label_file = os.path.join(output_folder, base + ".txt")
                with open(label_file, "w") as f:
                    for (pt1, pt2, cid) in bboxes:
                        x_center = (pt1[0] + pt2[0]) / 2 / img.shape[1]
                        y_center = (pt1[1] + pt2[1]) / 2 / img.shape[0]
                        width = abs(pt2[0] - pt1[0]) / img.shape[1]
                        height = abs(pt2[1] - pt1[1]) / img.shape[0]
                        f.write(f"{cid} {x_center} {y_center} {width} {height}\n")
                print(f"Annotation saved for {current_image_name} ({current_index + 1}/{len(images)})")
                current_index += 1
                break
            else:
                print("No bounding boxes drawn. Please draw at least one bounding box.")

        # Reset drawing if 'r' is pressed
        elif key == ord('r'):
            img = orig_img.copy()
            bboxes = []  # Clear all saved boxes
            cv2.imshow("Image", img)
            print("Drawing reset. Draw the bounding boxes again.")

        # Skip this image
        elif key == ord('n'):
            print(f"Skipping annotation for {current_image_name} ({current_index + 1}/{len(images)})")
            current_index += 1
            break

        # Go back to the previous image
        elif key == ord('b'):
            if current_index > 0:
                current_index -= 1
                print("Going back to previous image.")
                break
            else:
                print("Already at the first image. Can't go back.")

        # Quit program
        elif key == ord('q'):
            print("Exiting annotation program.")
            cv2.destroyAllWindows()
            exit()

        # Change class ID
        elif key in [ord('1'), ord('2'), ord('3')]:
            class_id = int(chr(key)) - 1
            print(f"Class ID set to {class_id} ({['small', 'medium', 'large'][class_id]})")

cv2.destroyAllWindows()
