from math import floor
from flask import Flask, render_template, send_file,jsonify,Response,request,make_response
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import requests
import eventlet
import threading
import time
from datetime import datetime
import os
import json
import cv2
from stitcher import stitch_all_images
import numpy as np

# eventlet.monkey_patch()  # needed for async networking with eventlet
SAVE_DIR = "captures"
os.makedirs(SAVE_DIR, exist_ok=True)

app = Flask(__name__)


socketio = SocketIO(app, cors_allowed_origins="*")

# UI route
@app.route("/")
def index():
    return render_template("index.html")


def _capture(url="http://192.168.31.254:5006/image"):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response

def _getPos(url="http://192.168.31.254:5005/pos"):
    resp = requests.get(url, timeout=10)
    print(resp)
    # resp.raise_for_status()
    data = resp.json()
    print(data)
    if data.get("status") != "ok":
        return False, []
    
    try:
        return True, [data.get('x'), data.get('y'), data.get('z')]
    except Exception:
        return False, []
    
@socketio.on('capture_request')
def capture_request():
    print("[SocketIO] CAPTURING...")

    # Get position
    success, pos = _getPos()
    if not success or pos is None:
        print("[SocketIO] Failed to get position")
        # emit('capture_saved', {
        #     "status": "error",
        #     "message": "Failed to get position"
        # })
        return

    try:
        # Capture image (raw PNG bytes)
        response = _capture()
        if response.status_code != 200:
            raise Exception(f"Bad status code: {response.status_code}")
        if not response.headers.get("Content-Type", "").startswith("image/png"):
            raise Exception("Invalid content type, expected image/png")

        # Use timestamp to uniquely name files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        img_filename = os.path.join(SAVE_DIR, f"{timestamp}.png")
        meta_filename = os.path.join(SAVE_DIR, f"{timestamp}.json")

        # Save image
        with open(img_filename, "wb") as f:
            f.write(response.content)

        # Save metadata (position, timestamp)
        metadata = {
            "timestamp": timestamp,
            "position": {
                "x": pos[0],
                "y": pos[1],
                "z": pos[2]
            }
        }
        with open(meta_filename, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"[SocketIO] Image saved as {img_filename}")
        # emit("capture_saved", {"status": "ok", "filename": img_filename})
        socketio.emit("captureFinish")
        stitch()

    except Exception as e:
        print("[SocketIO] Capture failed:", str(e))
        # emit('capture_saved', {
        #     "status": "error",
        #     "message": str(e)
        # })

@app.route("/stitch", methods=["GET","POST"])
def stitch():
    try:
        # Get optional parameters
        scale = float(request.args.get("scale", 1.0))   # default: no scaling
        fmt = request.args.get("format", "png").lower() # default: PNG
        request_new = request.args.get("new", False)
        valid_formats = ["jpg", "png"]

        if fmt not in valid_formats:
            return (
                jsonify({
                    "status": "error",
                    "message": f"Invalid format '{fmt}'. Valid formats are: {valid_formats}"
                }),
                400
            )         
        
        if request_new:
            stitch_all_images()  # path to the full-size stitched image
            socketio.emit("newStitchAvailable")
            return jsonify({
                    "status": "ok",
                }),200
            
            

        # Read and resize the image
        img = cv2.imread("stitched_output.png")

        small_img = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        # Encode to PNG
        success, buffer = cv2.imencode(f'.{fmt}', small_img)
        if not success:
            raise Exception("Image encoding failed")

        response = make_response(buffer.tobytes())
        response.headers["Content-Type"] = f"image/{fmt}"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
# def background_thread():
#     """Send image and position periodically to clients."""
#     while True:
#         try:
#             img_data = _capture()  # binary jpeg or png bytes
#             pos_ok, pos = _getPos()
#             if pos_ok:
#                 # Send position as JSON
#                 socketio.emit('position', {'x': pos[0], 'y': pos[1], 'z': pos[2]})
#             else:
#                 socketio.emit('position', {'error': 'Failed to get position'})

#             # Send image encoded in base64 (so JS clients can display)
#             import base64
#             b64_img = base64.b64encode(img_data).decode('utf-8')
#             socketio.emit('image', {'data': b64_img})

#         except Exception as e:
#             print("Background thread error:", e)

#         socketio.sleep(0.5)  # sleep for half second, adjust as needed


# @socketio.on('connect')
# def test_connect():
#     print('Client connected')
#     emit('message', {'data': 'Connected'})

@app.route("/clear", methods=["POST"])
def clear_captures():
    folder = "captures"
    stitched_path = "stitched_output.png"
    try:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
        
        # Overwrite stitched_output.png with black image
        width, height = 800, 600  # adjust to your desired size
        black_img = np.zeros((height, width, 3), dtype=np.uint8)  # note: shape is (height, width, channels)
        cv2.imwrite(stitched_path, black_img)
        socketio.emit("newStitchAvailable")

        return jsonify({"status": "success", "message": "All files deleted and stitched_output.png reset."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route("/scan")
def scan():
    x0, y0 = 50, 55
    # x1, y1 = 70,70
    x1, y1 = 120, 120
    increment_x = 20
    increment_y = 15

    num_x = floor((x1 - x0) / increment_x) + 1
    num_y = floor((y1 - y0) / increment_y) + 1

    increment_x = (x1-x0)/(num_x-1)
    increment_y = (y1-y0)/(num_y-1)


    scan_points = []
    for i in range(num_y):
        for j in range(num_x):
            x = x0 + j * increment_x
            y = y0 + i * increment_y
            scan_points.append((x, y))

    for (x, y) in scan_points:
        
        gcode = f"G1 X{x} Y{y}"
        res = requests.post("http://localhost:5005/gcode", params={"wait":"true"},json={"msg":f"{gcode}"})
        res = requests.post("http://localhost:5005/gcode", params={"wait":"true"},json={"msg":"M114"})
        res = requests.post("http://localhost:5005/gcode", params={"wait":"true"},json={"msg":"M114"})
        # if res.status_code != 200:
        #     print(f"⚠️ G-code failed at ({x}, {y}): {res.status_code} {res.text}")
        # time.sleep(1)
        
        capture_request()
        

    socketio.emit("scanFinish")
    print(">>>>","scanFInsih")
    return jsonify({
        "status": "ok",
        "points": scan_points,
        "count": len(scan_points)
    })




@app.route("/config")
def get_config():
    with open("configs/canvas_config.json") as f:
        config = json.load(f)
    return jsonify(config)
    

if __name__ == "__main__":
    # Start background thread that sends data to clients
    # socketio.start_background_task(target=background_thread)
    socketio.run(app, host="0.0.0.0", port=5007, debug=True)
