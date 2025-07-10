import cv2
import numpy as np
import sys, getopt
import pathlib

# ==== Step 1: Define your max display size ====
max_width = 1200
max_height = 900

# ==== Helper function: Convert display to original coordinates ====
def display_to_original_coords(x, y, scale):
    return int(round(x / scale)), int(round(y / scale))

# ==== Blemish fix (NO CHANGE) ====
def fix_blemish(image, source_pos, target_pos, brush_size):
    image_original = image.copy()
    # Get ROI
    clone_source_roi = image_original[source_pos[1]-brush_size:source_pos[1]+brush_size, source_pos[0]-brush_size:source_pos[0]+brush_size]
    # Get mask
    clone_source_mask = np.ones(clone_source_roi.shape, clone_source_roi.dtype) * 255
    clone_source_mask = cv2.GaussianBlur(clone_source_mask, (5,5), 0, 0)
    # Apply clone
    fix = cv2.seamlessClone(clone_source_roi, image_original, clone_source_mask, target_pos, cv2.NORMAL_CLONE)
    return fix

# ==== Globals for mouse callback ====
brush_size = 20
max_brush_size = 50
target_selected = False
target_pos = None
scale = 1.0  # Will update after image load

# ==== Mouse callback (KEY PART) ====
def on_mouse(event, x, y, flags, userdata):
    global image, display_image, brush_size, image_history, target_selected, target_pos, scale

    # Map click to original image
    orig_x, orig_y = display_to_original_coords(x, y, scale)
    mouse_pos = (orig_x, orig_y)

    # For display: draw on display_image (scaled version)
    image_view = display_image.copy()

    if target_selected:
        # Second click: user picks source region
        if event == cv2.EVENT_LBUTTONDOWN:
            image = fix_blemish(image, mouse_pos, target_pos, brush_size)
            image_history.append(image.copy())
            # Update the display image
            display_image = cv2.resize(image, (display_w, display_h), interpolation=cv2.INTER_AREA) if scale < 1.0 else image.copy()
            target_selected = False

        if flags == cv2.EVENT_MOUSEMOVE:
            # Show circles and lines on display image
            # Convert positions to display scale for drawing
            disp_target = (int(target_pos[0] * scale), int(target_pos[1] * scale))
            disp_mouse = (int(mouse_pos[0] * scale), int(mouse_pos[1] * scale))
            cv2.circle(image_view, center=disp_target, radius=int(brush_size*scale), color=(0,0,255), thickness=1)
            cv2.circle(image_view, center=disp_mouse, radius=int(brush_size*scale), color=(255,0,0), thickness=1)
            t = np.array(disp_target)
            m = np.array(disp_mouse)
            if np.linalg.norm(t-m) > brush_size * scale * 2:
                v = t - m
                line_vector = v / np.linalg.norm(v)
                t = t - line_vector * brush_size * scale
                t = tuple(t.astype(np.int64))
                m = m + line_vector * brush_size * scale
                m = tuple(m.astype(np.int64))
                cv2.line(image_view, t, m, (255,0,0), 1)
    else:
        # First click: user picks target region (blemish)
        if event == cv2.EVENT_LBUTTONDOWN:
            target_pos = mouse_pos
            target_selected = True
            disp_mouse = (int(mouse_pos[0] * scale), int(mouse_pos[1] * scale))
            cv2.circle(image_view, center=disp_mouse, radius=int(brush_size*scale), color=(0,0,255), thickness=1)

        if flags == cv2.EVENT_MOUSEMOVE:
            disp_mouse = (int(mouse_pos[0] * scale), int(mouse_pos[1] * scale))
            cv2.circle(image_view, center=disp_mouse, radius=int(brush_size*scale), color=(0,0,255), thickness=1)

    cv2.imshow(window_name, image_view)

def update_brush_size(*args):
    global brush_size
    brush_size = args[0]

def get_cli_io(argv):
    input_path = None
    output_path = None
    try:
        opts, args = getopt.getopt(argv[1:],"hi:o:")
    except getopt.GetoptError as err:
        print("Usage: blemish.py -i <input_path> -o <output_path>")
        print(err)
        sys.exit()
    for opt, arg in opts:
        if opt == '-h':
            print("Usage: blemish.py -i <input_path> -o <output_path>")
            sys.exit()
        elif opt == "-i":
            input_path = pathlib.Path(arg)
        elif opt == "-o":
            output_path = pathlib.Path(arg)
    if input_path is None:
        input_path = pathlib.Path("blemish.png")
        output_path = pathlib.Path("blemish_fix.png")
    elif output_path is None:
        output_path = input_path.with_stem(input_path.stem + "_fix")
    return input_path.as_posix(), output_path.as_posix()

# ==== MAIN ====
if __name__ == "__main__":
    input_path, save_file_path = get_cli_io(sys.argv)
    image = cv2.imread(input_path, cv2.IMREAD_COLOR)
    if image is not None:
        print(f"\nSuccessfully read image '{input_path}'")
    else:
        print(f"\nFailed to read image '{input_path}'")
        quit()
    print("\nInstructions: Click on the blemish you want to remove. Then click on the target area to clone from.")
    print("Press ESC to exit the program. \nPress 'z' to undo. \nPress 's' to save the image. \nPress '[' or ']' to change the brush size, or move the brush size slider.")

    # Create image history
    image_history = [image.copy()]

    # ==== Step 2: Scale for display if needed ====
    orig_height, orig_width = image.shape[:2]
    scale_x = min(1.0, max_width / orig_width)
    scale_y = min(1.0, max_height / orig_height)
    scale = min(scale_x, scale_y)
    if scale < 1.0:
        display_w = int(orig_width * scale)
        display_h = int(orig_height * scale)
        display_image = cv2.resize(image, (display_w, display_h), interpolation=cv2.INTER_AREA)
        print(f"Image scaled for display at {scale:.3f}x")
    else:
        display_w = orig_width
        display_h = orig_height
        display_image = image.copy()

    # ==== Window and controls ====
    window_name = "Blemish Tool"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.imshow(window_name, display_image)
    cv2.createTrackbar("Brush Size", window_name, brush_size, max_brush_size, update_brush_size)
    cv2.setMouseCallback(window_name, on_mouse)

    key_press = None
    while key_press != 27: # ESC
        if key_press == ord("z") and len(image_history) > 1:
            image_history.pop()
            image = image_history[-1].copy()
            display_image = cv2.resize(image, (display_w, display_h), interpolation=cv2.INTER_AREA) if scale < 1.0 else image.copy()
            cv2.imshow(window_name, display_image)
        if key_press == ord("s"):
            try:
                retval = cv2.imwrite(save_file_path, image)
                if retval == True:
                    print(f"Saved image as '{save_file_path}'")
            except cv2.error:
                print(f"Could not save image to '{save_file_path}'")
        if key_press == ord("]") and brush_size < max_brush_size:
            update_brush_size(brush_size + 1)
            cv2.setTrackbarPos("Brush Size", window_name, brush_size)
        if key_press == ord("[") and brush_size > 0:
            update_brush_size(brush_size - 1)
            cv2.setTrackbarPos("Brush Size", window_name, brush_size)
        key_press = cv2.waitKey(20) & 0xFF

    cv2.destroyAllWindows()
