import json
import numpy as np

image_size = [3088, 2064]  # [width, height] in pixels

coords1 = np.array([116.0, 99.3])     # in mm
pts1 = np.array([375, 1492])          # in pixels

coords2 = np.array([109.1, 98.1])     # in mm
pts2 = np.array([1106, 1367])         # in pixels

# Compute mm per pixel
delta_coords = coords1 - coords2      # [dx_mm, dy_mm]
delta_pixels = pts1 - pts2            # [dx_px, dy_px]

mm_per_pixel = delta_coords / delta_pixels
# mm_per_pixel_x, mm_per_pixel_y = mm_per_pixel.tolist()
mm_per_pixel_x, mm_per_pixel_y = [-0.0095,0.0095] 


# Inverse
pixel_per_mm_x = 1.0 / mm_per_pixel_x
pixel_per_mm_y = 1.0 / mm_per_pixel_y

# Compute image size in mm
image_size_mm = [
    image_size[0] * abs(mm_per_pixel_x),
    image_size[1] * abs(mm_per_pixel_y)
]

# Optionally: set origin_pixel and origin_world
origin_pixel = pts1.tolist()
origin_world = coords1.tolist()

# --- Camera matrix (for completeness, used in OpenCV calibration) ---
# For telecentric lens, assume fx ≈ fy, and principal point is image center
fx = pixel_per_mm_x
fy = pixel_per_mm_y
cx = image_size[0] / 2.0
cy = image_size[1] / 2.0

camera_matrix = [
    [fx, 0, cx],
    [0, fy, cy],
    [0,  0,  1]
]

# Create calibration dictionary
calibration = {
    "mm_per_pixel_x": abs(mm_per_pixel_x),
    "mm_per_pixel_y": abs(mm_per_pixel_y),
    "pixel_per_mm_x": abs(pixel_per_mm_x),
    "pixel_per_mm_y": abs(pixel_per_mm_y),
    "origin_pixel": origin_pixel,
    "origin_world": origin_world,
    "image_size": image_size,
    "image_size_mm": image_size_mm,
    "camera_matrix": camera_matrix,
    "notes": "Telecentric calibration on June 21, 2025"
}

# Save to file
with open("telecentric_calibration.json", "w") as f:
    json.dump(calibration, f, indent=4)

print("Calibration saved to telecentric_calibration.json")
