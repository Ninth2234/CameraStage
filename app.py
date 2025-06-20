from flask import Flask, request, render_template, jsonify

app = Flask(__name__)

# UI route
@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(port=5000, debug=True)
