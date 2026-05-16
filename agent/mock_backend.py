# save as mock_backend.py in your agent folder
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route("/alert", methods=["POST"])
def alert():
    data = request.json
    print(f"[BACKEND RECEIVED] {data}")
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(port=5000)