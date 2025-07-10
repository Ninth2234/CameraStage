import json

machine_limits = {"x": [15, 155], "y": [0, 125]}

with open("configs/telecentric_calibration.json", "r") as f:
    calib = json.load(f)

image_size_mm = calib["image_size_mm"]

canvas_limits_mm = {
    "x": [
        machine_limits["x"][0] - image_size_mm[0] / 2,
        machine_limits["x"][1] + image_size_mm[0] / 2,
    ],
    "y": [
        machine_limits["y"][0] - image_size_mm[1] / 2,
        machine_limits["y"][1] + image_size_mm[1] / 2,
    ],
}

canvas_limits = {
    "u": [round(x * calib["pixel_per_mm_x"]) for x in canvas_limits_mm["x"]],
    "v": [round(y * calib["pixel_per_mm_y"]) for y in canvas_limits_mm["y"]],
}
canvas_size = [
    canvas_limits["u"][1] - canvas_limits["u"][0],
    canvas_limits["v"][1] - canvas_limits["v"][0],
]

canvas_size_mm = [
    canvas_size[0]/calib["pixel_per_mm_x"],
    canvas_size[1]/calib["pixel_per_mm_y"],
]

bed_zero_offset = [0, 0]

# Bundle everything
canvas_config = {
    "canvas_limits_mm": canvas_limits_mm,
    "canvas_limits": canvas_limits,
    "canvas_size": canvas_size,
    "canvas_size_mm": canvas_size_mm,
    "bed_zero_offset": bed_zero_offset,
    "machine_limits":machine_limits,
    "camera_size": calib["image_size"],
    "camera_size_mm": calib["image_size_mm"]
}

# Write to JSON
with open("configs/canvas_config.json", "w") as f:
    json.dump(canvas_config, f, indent=4)

print("✅ Saved to configs/canvas_config.json")
