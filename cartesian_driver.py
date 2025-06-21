from serial import Serial
import threading
import queue
import time
from flask import Flask, jsonify,request
from flask_cors import CORS

import logging

import serial
import serial.tools
import serial.tools.list_ports

logger = logging.getLogger("GCodeLogger")
logger.setLevel(logging.DEBUG)

# File handler
file_handler = logging.FileHandler("logs/cartesian.log")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(message)s'))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Initialize serial port
ser = None
running = False
thread = None


ok_event = threading.Event()
wait_event = threading.Event()
msg_queue = queue.Queue()

# Flask app
app = Flask(__name__)
CORS(app)

# Modify your read_task:
def read_task():
    while running:
        if ser.in_waiting:
            try:
                msg = ser.readline().decode(errors='ignore').strip()
                if msg:
                    logger.info(f"[Recv] {msg}")
                    if msg.lower().startswith("ok"):
                        ok_event.set()
                        logger.info("[EVENT] OK is SET")
                    
                    if ok_event.is_set():  # only set wait_event if ok was received before
                        msg_queue.put(msg)
                        if msg == "wait":
                            wait_event.set()                            
                            logger.info("[EVENT] WAIT is SET")
                            logger.info("[EVENT] OK is CLEAR")
                            ok_event.clear()
            except Exception as e:
                logger.error(f"Read error: {e}")
                break
        time.sleep(0.01)

def _send_gcode(msg, wait=False, timeout=10):
    try:
        gcode = msg.strip() + "\r\n"

        if wait:
            wait_event.clear()
            ok_event.clear()

        ser.write(gcode.encode())
        logger.info(f"[GCODE] Sent: {msg.strip()} (wait={wait})")

        if wait:
            if wait_event.wait(timeout):
                response = []
                while not msg_queue.empty():
                    response.append(msg_queue.get())
                response.pop()
                response.pop(0)
                return {"status": "ok", "sent": msg, "response": response}, 200
            else:
                return {"status": "timeout", "sent": msg}, 504
        else:
            return {"status": "ok", "sent": msg}, 200

    except Exception as e:
        logger.error(f"[GCODE ERROR] {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route("/gcode", methods=['GET', 'POST'])
def send_gcode():
    msg = request.args.get("msg", "")

    if not msg and request.method == "POST":
        if request.form.get("msg"):
            msg = request.form.get("msg")
        elif request.is_json:
            data = request.get_json()
            msg = data.get("msg", "") if data else ""

    wait_flag = request.args.get("wait", "false").lower() == "true"
    try:
        timeout = int(request.args.get("timeout", 1))
    except ValueError:
        timeout = 1

    logger.info(f"[Flask] Received G-code: {msg} (wait={wait_flag})")

    response_data, status_code = _send_gcode(msg, wait=wait_flag, timeout=timeout)
    return jsonify(response_data), status_code
    
@app.route("/pos",methods=["GET"])
def get_pos():
    return _send_gcode("M114", wait=True, timeout=5)
    

    
@app.route("/logs")
def get_logs():
    try:
        n = int(request.args.get("n", 20))  # Default to 10 lines
        with open("gcode.log", "r") as f:
            lines = f.readlines()
            last_10 = lines[-n:]
        return jsonify(logs=[line.strip() for line in last_10])
    except Exception as e:
        logger.error(f"Log read error: {e}")
        return jsonify(status="error", message="Failed to read logs"), 500
    
@app.route("/ports", methods=["GET"])
def list_ports():
    ports = serial.tools.list_ports.comports()
    port_list = [port.device for port in ports]
    return jsonify(ports=port_list)



def _connect(port, baudrate=115200):
    global ser, running, thread, last_port, last_baudrate

    # Stop previous thread & close port if open
    running = False
    if thread and thread.is_alive():
        thread.join()
    if ser and ser.is_open:
        ser.close()

    # Open new serial port and start reader thread
    ser = Serial(port, baudrate, timeout=1)
    running = True
    thread = threading.Thread(target=read_task, daemon=True)
    thread.start()

    last_port = port
    last_baudrate = baudrate

    logger.info(f"[Connect] Connected to {port} @ {baudrate}")

def _disconnect():
    global running, ser, thread
    running = False
    if thread and thread.is_alive():
        thread.join()
    if ser and ser.is_open:
        ser.close()
        logger.info("[Disconnect] Serial port closed.")

@app.route("/reconnect")
def reconnect(delay=0.2):
    global last_port, last_baudrate
    logger.info("[Reconnect] Attempting reconnect...")
    _disconnect()
    time.sleep(delay)
    try:
        _connect(last_port, last_baudrate)
        return True, f"Reconnected to {last_port}"
    except Exception as e:
        logger.error(f"[Reconnect Failed] {e}")
        return False, str(e)

@app.route("/connect", methods=["POST"])
def connect_serial():
    data = request.json
    port = data.get("port")
    baudrate = data.get("baudrate", 115200)

    if not port:
        return jsonify(status="error", message="Missing port name"), 400

    try:
        _connect(port, baudrate)
        return jsonify(status="connected", port=port, baudrate=baudrate)
    except Exception as e:
        logger.error(f"[Connect Error] {e}")
        return jsonify(status="error", message=str(e)), 500


# Main entry
if __name__ == "__main__":
    try:
        _connect("/dev/snapmaker",115200)
        # Start Flask (non-blocking if needed)
        app.run(host="0.0.0.0", port=5005)

        
    
    except KeyboardInterrupt:
        print("\nStopping...")
        running = False
        thread.join()
        ser.close()
        print("Serial closed. Exiting.")
