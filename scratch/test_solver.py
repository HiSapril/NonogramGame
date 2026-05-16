import sys
sys.path.append("Backend")
from solver.board import NonogramBoard

rows_clues = [[2], [2], [2], [2], [2]]
cols_clues = [[2], [2], [2], [2], [2]]

board = NonogramBoard(rows_clues, cols_clues)
solved = board.backtrack_solve()

print("Solved:", solved)
print(board)
