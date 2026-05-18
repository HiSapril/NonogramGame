import sys
sys.path.append("Backend")
from solver.board import NonogramBoard

presets = {
    "medium": {
        "rows": [
            [4], [1, 2], [1, 1, 1], [1, 2], [4],
            [1], [1, 1], [3], [1, 1], [1],
        ],
        "cols": [
            [4], [1, 2], [1, 1, 1], [1, 2], [4],
            [1], [1, 1], [3], [1, 1], [1],
        ],
    },
    "hard": {
        "rows": [[0], [3, 3], [5, 5], [13], [13], [13], [11], [9], [7], [5], [3], [1], [0], [0], [0]],
        "cols": [[0], [3], [5], [7], [8], [9], [9], [9], [9], [9], [8], [7], [5], [3], [0]]
    },
    "extreme": {
        "rows": [[0], [6, 6], [2, 2, 2, 2], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [2, 2, 2, 2], [6, 6], [0], [0], [0], [12], [1, 1], [1, 1], [1, 1], [2, 2], [6], [0], [0], [0]],
        "cols": [[0], [5], [2, 2], [1, 1], [1, 1, 3], [1, 1, 1, 1], [1, 1, 1, 1], [2, 2, 1, 2], [5, 1, 1], [1, 1], [1, 1], [5, 1, 1], [2, 2, 1, 2], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 3], [1, 1], [2, 2], [5], [0]]
    }
}

for name, clues in presets.items():
    print(f"\n--- Testing {name} ---")
    board = NonogramBoard(clues["rows"], clues["cols"])
    try:
        solved = board.backtrack_solve()
        print(f"Solved: {solved}")
        if solved:
            print("Board:")
            print(board)
        else:
            print("Failed to solve.")
            # Let's see if there is sum mismatch
            sum_rows = sum(sum(r) for r in clues["rows"])
            sum_cols = sum(sum(c) for c in clues["cols"])
            print(f"Sum of rows clues: {sum_rows}, Sum of cols clues: {sum_cols}")
    except Exception as e:
        print(f"Error: {e}")
