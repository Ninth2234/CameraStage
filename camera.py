import threading
import time
import cv2
import numpy as np
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from pypylon import pylon

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize PyPylon
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
camera.Open()
print(camera.ExposureTime.GetMax(),camera.ExposureTime.GetMin())
camera.ExposureTime.SetValue(100_000)
print(camera.ExposureTime.Value)
# Shared frame variable
latest_frame = None
frame_lock = threading.Lock()
frame_number = 0  # global frame number

# MAX_EXPOSURE = camera.ExposureTime.GetMax()
MAX_EXPOSURE = 1_000_000
MIN_EXPOSURE = camera.ExposureTime.GetMin()

@app.route('/exposure', methods=['GET', 'POST'])
def exposure():
    try:
        max_exp = MAX_EXPOSURE
        min_exp = MIN_EXPOSURE
        current_exp = camera.ExposureTime.Value

        # Get value from JSON or query string
        data = request.get_json(silent=True)

        value = None
        if data and 'value' in data:
            value = data['value']
        elif 'value' in request.args:
            value = request.args.get('value')

        if value is None:
            if request.method == 'POST':
                return jsonify({
                    "status": "error",
                    "message": "Missing 'value' for exposure setting"
                }), 400
            
            return jsonify({
                "status": "ok",
                "current": current_exp,
                "min": min_exp,
                "max": max_exp
            }),200

        try:
            value_int = float(value)
        except ValueError:
            return jsonify({
                "status": "error",
                "message": f"Invalid value: {value}"
            }), 400

        if not (min_exp <= value_int <= max_exp):
            return jsonify({
                "status": "error",
                "message": f"Value {value_int} out of range ({min_exp}–{max_exp})",
                "min": min_exp,
                "max": max_exp
            }), 400

        # Set the exposure if value is valid
        camera.ExposureTime.SetValue(value_int)
        current_exp = camera.ExposureTime.Value

        # In all other cases (GET with no value), just return current status
        return jsonify({
            "status": "ok",
            "current": current_exp,
            "min": min_exp,
            "max": max_exp
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/status",methods=["GET"])
def status():
    ...
    


def camera_thread():
    global latest_frame, frame_number

    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    while True:
        t0 = time.perf_counter()
        
        image = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        
        image = image.Array
        image = cv2.resize(image, (0, 0), fx=0.1, fy=0.1, interpolation=cv2.INTER_LINEAR)
        
        
        t1 = time.perf_counter()
        
        
        # Resize and encode to JPEG        
        ret, jpeg = cv2.imencode('.jpg', image)
        if not ret:
            continue
        t2 = time.perf_counter()
        with frame_lock:
            latest_frame = jpeg.tobytes()
            frame_number += 1
        t3 = time.perf_counter()

        # print(f"Grab: {1000*(t1 - t0):.3f} ms\t Encode: {1000*(t2 - t1):.3f} ms\t Send: {1000*(t3 - t2):.3f} ms")


@app.route('/image')
def get_latest_image():
    with frame_lock:
        if latest_frame is None:
            return "No image available", 503
        return Response(latest_frame, mimetype='image/jpeg')

@app.route('/video')
def stream():
    def generate():
        last_send = 0
        min_interval = 1/30
        frame_count = 0
        fps_start_time = time.perf_counter()

        last_send = frame_number

        while True:

            now = time.perf_counter()
            elapsed = now - last_send
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
    
            with frame_lock:
                if frame_number == last_send:
                    frame = None  # no new frame yet
                    
                else:
                    frame = latest_frame
                    last_send = frame_number  # update last sent frame number
        
            if frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + f"{len(frame)}".encode() + b'\r\n'
                       b'\r\n' + frame + b'\r\n')
                frame_count += 1

                # Measure FPS every second
                if (now - fps_start_time) >= 1.0:
                    fps = frame_count / (now - fps_start_time)
                    print(f"[STREAM] FPS: {fps:.2f}")
                    frame_count = 0
                    fps_start_time = now
            else:
                time.sleep(0.01)  # small sleep to avoid busy wait

            last_send = time.perf_counter()

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    t = threading.Thread(target=camera_thread, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5006)
