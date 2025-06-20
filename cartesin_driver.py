from serial import Serial
import threading
import time
from flask import Flask, jsonify,request
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

# Flask app
app = Flask(__name__)

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
                    elif msg == "wait":
                        if ok_event.is_set():  # only set wait_event if ok was received before
                            wait_event.set()                            
                            logger.info("[EVENT] WAIT is SET")
                            logger.info("[EVENT] OK is CLEAR")
                            ok_event.clear()
            except Exception as e:
                logger.error(f"Read error: {e}")
                break
        time.sleep(0.01)

# Your Flask route modification:
@app.route("/gcode")
def send_gcode():
    print("Request args:", request.args)  # debug
    msg = request.args.get("msg", "")
    wait_flag = request.args.get("wait", "false").lower() == "true"
    try:
        timeout = int(request.args.get("timeout", 10))
    except ValueError:
        timeout = 10  # fallback default

    logger.info(f"[Flask] Received: {msg} (wait={wait_flag})")
    print(">>>",wait_flag,request.args)
    try:
        gcode = msg + "\r\n"
        if wait_flag:
            wait_event.clear()
            ok_event.clear()

        ser.write(gcode.encode())

        if wait_flag:
            # Clear previous event state
            
            # Wait max 10 seconds (adjust as needed)
            if wait_event.wait(timeout):
                return jsonify(status="ok", sent=msg, info="wait received")
            else:
                return jsonify(status="timeout", sent=msg, info="wait response not received in time"), 504
        else:
            return jsonify(status="ok", sent=msg)

    except Exception as e:
        return jsonify(status="error", message=str(e)), 500
    
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
    global ser, running, thread

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

    logger.info(f"[Connect] Connected to {port} @ {baudrate}")

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
        _connect("COM19",115200)
        # Start Flask (non-blocking if needed)
        app.run(host="0.0.0.0", port=5000)

        
    
    except KeyboardInterrupt:
        print("\nStopping...")
        running = False
        thread.join()
        ser.close()
        print("Serial closed. Exiting.")
