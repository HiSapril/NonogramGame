"""
app.py
------
Flask backend for the Nonogram solver.

Exposes a single REST endpoint:

    POST /solve
        Body : { "rows_clues": [[...], ...], "cols_clues": [[...], ...] }
        Returns the solved grid, the full move history (LOGIC / GUESS /
        BACKTRACK steps), and execution statistics.

Run locally:
    python app.py
"""

import time
import logging

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from solver.board import NonogramBoard

# ── App setup ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)   # allow all origins; tighten in production as needed

# Cấu hình Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///puzzles.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Puzzle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rows_clues = db.Column(db.String(500), nullable=False)
    cols_clues = db.Column(db.String(500), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rowsClues": self.rows_clues,
            "colsClues": self.cols_clues
        }

with app.app_context():
    db.create_all()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ── Helper ────────────────────────────────────────────────────────────────────

def _validate_clues(clues: object, name: str) -> list:
    """
    Assert that *clues* is a list of lists of positive integers.

    Raises
    ------
    ValueError
        With a human-readable message describing the problem.
    """
    if not isinstance(clues, list) or len(clues) == 0:
        raise ValueError(f"'{name}' must be a non-empty list.")
    for i, row in enumerate(clues):
        if not isinstance(row, list):
            raise ValueError(f"'{name}[{i}]' must be a list, got {type(row).__name__}.")
        for j, val in enumerate(row):
            if not isinstance(val, int) or val < 0:
                raise ValueError(
                    f"'{name}[{i}][{j}]' must be a non-negative integer, got {val!r}."
                )
    return clues


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.route("/solve", methods=["POST"])
def solve():
    """
    Solve a Nonogram puzzle.

    Request body (JSON)
    -------------------
    {
        "rows_clues": [[int, ...], ...],   // one sublist per row
        "cols_clues": [[int, ...], ...]    // one sublist per column
    }

    Response (JSON)
    ---------------
    Success (200):
    {
        "status": "success",
        "solution": [[int, ...], ...],     // final 2-D grid (0 / 1)
        "steps": [                         // full move history
            {"x": int, "y": int, "val": int, "type": "logic"|"GUESS"|"BACKTRACK"},
            ...
        ],
        "stats": {
            "time_ms":     float,          // wall-clock time in milliseconds
            "total_steps": int             // number of history entries
        }
    }

    Error (400 / 500):
    {
        "status": "error",
        "message": str
    }
    """
    # ── Parse body ────────────────────────────────────────────────────────────
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"status": "error", "message": "Request body must be valid JSON."}), 400

    # ── Validate input ────────────────────────────────────────────────────────
    try:
        rows_clues = _validate_clues(body.get("rows_clues"), "rows_clues")
        cols_clues = _validate_clues(body.get("cols_clues"), "cols_clues")
    except (ValueError, TypeError) as exc:
        logger.warning("Bad request: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 400

    logger.info(
        "Solving %dx%d puzzle — rows_clues=%s cols_clues=%s",
        len(rows_clues), len(cols_clues), rows_clues, cols_clues,
    )

    # ── Solve ─────────────────────────────────────────────────────────────────
    try:
        board = NonogramBoard(rows_clues, cols_clues)

        t_start = time.time()
        solved  = board.backtrack_solve()
        t_end   = time.time()

        elapsed_ms = round((t_end - t_start) * 1000, 3)

    except Exception as exc:          # unexpected solver error
        logger.exception("Solver crashed: %s", exc)
        return jsonify({"status": "error", "message": f"Solver error: {exc}"}), 500

    # ── Build response ────────────────────────────────────────────────────────
    if not solved:
        logger.info("Puzzle has no solution.")
        return jsonify({
            "status":  "error",
            "message": "This puzzle has no valid solution.",
        }), 400

    logger.info("Solved in %.3f ms, %d history steps.", elapsed_ms, len(board.history))

    return jsonify({
        "status":   "success",
        "solution": board.grid,
        "steps":    board.history,
        "stats": {
            "time_ms":     elapsed_ms,
            "total_steps": len(board.history),
        },
    }), 200


@app.route("/health", methods=["GET"])
def health():
    """Simple liveness check — returns 200 OK."""
    return jsonify({"status": "ok"}), 200

# ── Custom Puzzle APIs ───────────────────────────────────────────────────────

@app.route('/api/save_puzzle', methods=['POST'])
def save_puzzle():
    data = request.json
    try:
        new_puzzle = Puzzle(
            name=data.get('name', 'Untitled Puzzle'),
            rows_clues=data['rows_clues'],
            cols_clues=data['cols_clues']
        )
        db.session.add(new_puzzle)
        db.session.commit()
        return jsonify({"message": "Lưu thành công!", "id": new_puzzle.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/get_puzzles', methods=['GET'])
def get_puzzles():
    puzzles = Puzzle.query.all()
    return jsonify([p.to_dict() for p in puzzles])

@app.route('/api/delete_puzzle/<int:puzzle_id>', methods=['DELETE'])
def delete_puzzle(puzzle_id):
    try:
        puzzle = Puzzle.query.get(puzzle_id)
        if not puzzle:
            return jsonify({"error": "Không tìm thấy câu đố"}), 404
        db.session.delete(puzzle)
        db.session.commit()
        return jsonify({"message": "Xóa thành công"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/rename_puzzle/<int:puzzle_id>', methods=['PUT'])
def rename_puzzle(puzzle_id):
    data = request.json
    try:
        puzzle = Puzzle.query.get(puzzle_id)
        if not puzzle:
            return jsonify({"error": "Không tìm thấy câu đố"}), 404
        puzzle.name = data.get('name', puzzle.name)
        db.session.commit()
        return jsonify({"message": "Đổi tên thành công"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
