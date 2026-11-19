from flask import Flask, request, jsonify
from flask_cors import CORS
from solver import solve_puzzle

app = Flask(__name__)
CORS(app)  # Mengizinkan akses dari frontend (index.html)


@app.route("/solve", methods=["POST"])
def solve():
    data = request.get_json()

    if not data or "algorithm" not in data or "board" not in data:
        return jsonify({"error": "Request harus berisi 'algorithm' dan 'board'"}), 400

    algorithm = data["algorithm"]
    board = data["board"]

    try:
        result = solve_puzzle(algorithm, board)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan server: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)