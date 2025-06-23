from flask import Flask, render_template, send_file,jsonify,Response,request
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
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "ok":
        return False, []
    
    try:
        return True, [data.get('x'), data.get('y'), data.get('z')]
    except Exception:
        return False, []
    
@socketio.on('capture_request')
def handle_capture_request():
    print("[SocketIO] CAPTURING...")

    # Get position
    success, pos = _getPos()
    if not success or pos is None:
        print("[SocketIO] Failed to get position")
        emit('capture_saved', {
            "status": "error",
            "message": "Failed to get position"
        })
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
        emit("capture_saved", {"status": "ok", "filename": img_filename})

    except Exception as e:
        print("[SocketIO] Capture failed:", str(e))
        emit('capture_saved', {
            "status": "error",
            "message": str(e)
        })

@app.route("/stitch", methods=["GET"])
def stitch_route():
    try:
        # Get optional parameters
        scale = float(request.args.get("scale", 1.0))   # default: no scaling
        fmt = request.args.get("format", "png").lower() # default: PNG
        valid_formats = ["jpg", "png"]

        if fmt not in valid_formats:
            return (
                jsonify({
                    "status": "error",
                    "message": f"Invalid format '{fmt}'. Valid formats are: {valid_formats}"
                }),
                400
            ) 
        t0 = time.perf_counter()
        path = stitch_all_images()  # path to the full-size stitched image
        t1 = time.perf_counter()

        # Read and resize the image
        img = cv2.imread(path)
        if img is None:
            raise Exception(f"Failed to load image at path: {path}")

        small_img = cv2.resize(img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

        # Encode to PNG
        success, buffer = cv2.imencode(f'.{fmt}', small_img)
        if not success:
            raise Exception("Image encoding failed")

        return Response(buffer.tobytes(), mimetype=f'image/{fmt}'),200

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

    try:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)

        return jsonify({"status": "success", "message": "All files in captures/ deleted."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/config")
def get_config():
    with open("configs/canvas_config.json") as f:
        config = json.load(f)
    return jsonify(config)
    

if __name__ == "__main__":
    # Start background thread that sends data to clients
    # socketio.start_background_task(target=background_thread)
    socketio.run(app, host="0.0.0.0", port=5007, debug=True)
