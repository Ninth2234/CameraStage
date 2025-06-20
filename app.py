from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
app = Flask(__name__)


CORS(app, resources={r"/*": {"origins": "192.168.31.254"}})

# UI route
@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5007, debug=True)
