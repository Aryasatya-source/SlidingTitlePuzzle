from flask import Flask, request, jsonify
from flask_cors import CORS
from solver import SearchLimitError, generate_solvable_board, solve_puzzle


app = Flask(__name__)
CORS(app)  # Mengizinkan akses dari frontend (index.html)


@app.route("/solve", methods=["POST"])
def solve():
    data = request.get_json(silent=True)

    if not data or "algorithm" not in data or "board" not in data:
        return jsonify({"error": "Request harus berisi 'algorithm' dan 'board'"}), 400

    algorithm = data["algorithm"]
    board = data["board"]
    size = data.get("size")  # opsional: 3, 4, atau 5 (jika kosong, dideduksi dari panjang board)

    try:
        result = solve_puzzle(algorithm, board, size)
        return jsonify(result), 200
    except SearchLimitError as e:
        return (
            jsonify(
                {
                    "error": str(e),
                    "code": "SEARCH_LIMIT_EXCEEDED",
                    "expandedNodes": e.expanded_nodes,
                    "executionTimeMs": e.elapsed_ms,
                }
            ),
            422,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except MemoryError:
        return (
            jsonify(
                {
                    "error": "Server kehabisan memori saat mencari solusi. "
                    "Coba papan yang lebih mudah atau ukuran grid yang lebih kecil.",
                    "code": "SEARCH_LIMIT_EXCEEDED",
                }
            ),
            422,
        )
    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan server: {str(e)}"}), 500


@app.route("/shuffle", methods=["GET"])
def shuffle():
    """
    Menghasilkan papan acak yang dijamin solvable.
    Query: size (3/4/5, default 3), moves (opsional, jumlah langkah acak mundur dari goal).
    """
    size = request.args.get("size", default=3, type=int)
    moves = request.args.get("moves", default=None, type=int)

    try:
        board = generate_solvable_board(size, moves)
        return jsonify({"board": board, "size": size}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan server: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)