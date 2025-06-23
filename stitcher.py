import os
import json
import cv2
import numpy as np


def load_captures_data(folder="captures"):
    data = []

    for filename in os.listdir(folder):
        base, ext = os.path.splitext(filename)

        if ext.lower() != ".json":
            continue

        json_path = os.path.join(folder, filename)
        img_path = os.path.join(folder, base + ".png")
        if not os.path.exists(img_path):
            img_path = os.path.join(folder, base + ".jpg")
        if not os.path.exists(img_path):
            print(f"[Warning] No image found for {filename}")
            continue

        # Load coordinate
        try:
            with open(json_path, "r") as f:
                info = json.load(f)
            coords = info.get("position", None)
            if coords is None:
                print(f"[Warning] No 'position' key in {filename}")
                continue
        except Exception as e:
            print(f"[Error] Failed to read {json_path}: {e}")
            continue

        # Load image
        image = cv2.imread(img_path)
        if image is None:
            print(f"[Error] Failed to load image {img_path}")
            continue
        

        data.append({
            "name": base,
            "coords": coords,
            "image": image
        })

    return data

def stitch_all_images(calib_path="configs/telecentric_calibration.json", captures_folder="captures", output_path="stitched_output.png"):
    with open(calib_path, "r") as f:
        calib = json.load(f)

    with open("configs/canvas_config.json","r") as f:
        canvas_config = json.load(f)

    mm_per_pixel_x = calib["mm_per_pixel_x"]
    mm_per_pixel_y = calib["mm_per_pixel_y"]
    image_size_mm = calib["image_size_mm"]

    machine_limits = {"x": [50, 120], "y": [50, 120]}
    bed_limits = machine_limits

    canvas_limits_mm = canvas_config["canvas_limits_mm"]

    canvas_width_px = canvas_config["canvas_size"][0]
    canvas_height_px = canvas_config["canvas_size"][1]
    canvas = np.zeros((canvas_height_px, canvas_width_px, 3), dtype=np.uint8)

    captures = load_captures_data(captures_folder)
    for cap in captures:
        img = cap["image"]
        x_mm = cap["coords"]["x"] - image_size_mm[0] / 2
        y_mm = cap["coords"]["y"] - image_size_mm[1] / 2

        x_offset_mm = x_mm - canvas_limits_mm["x"][0]
        y_offset_mm = y_mm - canvas_limits_mm["y"][0]

        h, w = img.shape[:2]

        x_px = int(x_offset_mm / mm_per_pixel_x)
        y_px = canvas_height_px - int(y_offset_mm / mm_per_pixel_y) - h

        y_end = min(canvas.shape[0], y_px + h)
        x_end = min(canvas.shape[1], x_px + w)
        y_img_end = y_end - y_px
        x_img_end = x_end - x_px

        canvas[y_px:y_end, x_px:x_end] = img[0:y_img_end, 0:x_img_end]

    cv2.imwrite(output_path, canvas)
    return output_path

if __name__ == "__main__":
    stitch_all_images()