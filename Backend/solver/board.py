"""
board.py
--------
Nonogram game-state manager.

Coordinates the grid, history tracking, and the constraint-propagation
deduction loop that uses generate_combinations() and get_overlap() from
the sibling modules.
"""

import copy
from typing import List, Dict, Any, Optional, Tuple

try:
    # Package import (normal usage: `from solver.board import NonogramBoard`)
    from .combinations import generate_combinations
    from .overlap import get_overlap, ImpossibleStateError
except ImportError:
    # Direct run: `python board.py`
    from combinations import generate_combinations          # type: ignore
    from overlap import get_overlap, ImpossibleStateError   # type: ignore


# ── Type aliases ──────────────────────────────────────────────────────────────
Clues     = List[int]
Grid      = List[List[int]]
HistEntry = Dict[str, Any]   # {"x": int, "y": int, "val": int, "type": str}


class NonogramBoard:
    """
    Manages the full state of a Nonogram puzzle.

    Grid values
    -----------
    -1 : unknown (not yet determined)
     0 : white (empty)
     1 : black (filled)

    Parameters
    ----------
    rows_clues : List[List[int]]
        One clue list per row  (e.g. [[3], [1, 1], [2]]).
    cols_clues : List[List[int]]
        One clue list per column.

    Attributes
    ----------
    grid    : 2-D list[int] of shape (num_rows × num_cols), initialised to -1.
    history : List of change records {"x", "y", "val", "type"}.
    """

    def __init__(self, rows_clues: List[Clues], cols_clues: List[Clues]) -> None:
        self.rows_clues: List[Clues] = rows_clues
        self.cols_clues: List[Clues] = cols_clues

        self.num_rows: int = len(rows_clues)
        self.num_cols: int = len(cols_clues)

        # Grid initialised to -1 (all unknown)
        self.grid: Grid = [
            [-1] * self.num_cols for _ in range(self.num_rows)
        ]

        # Full audit trail of every cell change
        self.history: List[HistEntry] = []

    # ── Accessors ─────────────────────────────────────────────────────────────

    def get_row(self, index: int) -> List[int]:
        """Return a *copy* of the current state of row ``index``."""
        return list(self.grid[index])

    def get_col(self, index: int) -> List[int]:
        """Return a *copy* of the current state of column ``index``."""
        return [self.grid[r][index] for r in range(self.num_rows)]

    # ── Mutation ──────────────────────────────────────────────────────────────

    def update_cell(self, r: int, c: int, val: int, type: str = "logic", reason: str = "") -> bool:
        """
        Update cell (r, c) to ``val`` and record the change in history.

        The update is skipped (and ``False`` is returned) if the cell already
        holds ``val``, keeping history lean and the deduction loop efficient.

        Parameters
        ----------
        r, c : int
            Row and column indices (0-based).
        val  : int
            New cell value: 0 (white) or 1 (black).
        type : str
            Source of the change, e.g. ``"logic"`` (deduction) or
            ``"user"`` (manual input).  Stored verbatim in history.
        reason : str
            Explanation of why this change was deduced.

        Returns
        -------
        bool
            ``True`` if the cell was actually changed, ``False`` otherwise.
        """
        if self.grid[r][c] == val:
            return False   # no change — skip

        self.grid[r][c] = val
        self.history.append({"x": c, "y": r, "val": val, "type": type, "reason": reason})
        return True

    # ── Status checks ─────────────────────────────────────────────────────────

    def is_solved(self) -> bool:
        """Return ``True`` when every cell has been determined (no -1 left)."""
        return all(
            self.grid[r][c] != -1
            for r in range(self.num_rows)
            for c in range(self.num_cols)
        )

    def is_invalid(self) -> bool:
        """
        Return ``True`` if the current board state is provably unsolvable.

        A state is invalid when at least one row or column has *no* valid
        combination that is consistent with the already-filled cells.
        """
        for r in range(self.num_rows):
            combos = self._filtered_combinations("row", r)
            if combos is not None and len(combos) == 0:
                return True

        for c in range(self.num_cols):
            combos = self._filtered_combinations("col", c)
            if combos is not None and len(combos) == 0:
                return True

        return False

    # ── Constraint propagation ────────────────────────────────────────────────

    def apply_logic(self) -> bool:
        """
        Run the constraint-propagation deduction loop.

        Each iteration:
        1. For every row — generate all combinations compatible with the
           current grid state, compute the overlap, and lock in any certain
           cells.
        2. Repeat for every column.
        3. If *any* cell was updated this iteration, go back to step 1
           (a column update may unlock new row deductions and vice versa).
        4. Stop when a full pass produces no new information, or when the
           board is solved / becomes invalid.

        Returns
        -------
        bool
            ``True``  — the board was solved completely by logic alone.
            ``False`` — the loop stalled (backtracking / guessing needed)
                        or the board entered an invalid state.
        """
        while True:
            changed = False

            # ── Row pass ──────────────────────────────────────────────────────
            for r in range(self.num_rows):
                combos = self._filtered_combinations("row", r)

                if combos is None:
                    continue   # row has no unknowns; nothing to do

                if len(combos) == 0:
                    return False   # conflict — no valid combo for this row

                try:
                    overlap = get_overlap(combos, self.num_cols)
                except ImpossibleStateError:
                    return False

                for c, val in enumerate(overlap):
                    if val != -1:
                        clues = self.rows_clues[r]
                        combos_to_show = combos[:3]
                        combos_str = str(combos_to_show)
                        if len(combos) > 3:
                            combos_str = combos_str[:-1] + ", ...]"
                        
                        cell_desc = "đen" if val == 1 else "trống"
                        reason = f"Hàng {r+1} (Gợi ý {clues}) có {len(combos)} cấu hình khả dĩ: {combos_str} -> Giao thoa: ô cột {c+1} chắc chắn {cell_desc}."
                        
                        if self.update_cell(r, c, val, type="logic", reason=reason):
                            changed = True

            # ── Column pass ───────────────────────────────────────────────────
            for c in range(self.num_cols):
                combos = self._filtered_combinations("col", c)

                if combos is None:
                    continue

                if len(combos) == 0:
                    return False

                try:
                    overlap = get_overlap(combos, self.num_rows)
                except ImpossibleStateError:
                    return False

                for r, val in enumerate(overlap):
                    if val != -1:
                        clues = self.cols_clues[c]
                        combos_to_show = combos[:3]
                        combos_str = str(combos_to_show)
                        if len(combos) > 3:
                            combos_str = combos_str[:-1] + ", ...]"
                        
                        cell_desc = "đen" if val == 1 else "trống"
                        reason = f"Cột {c+1} (Gợi ý {clues}) có {len(combos)} cấu hình khả dĩ: {combos_str} -> Giao thoa: ô hàng {r+1} chắc chắn {cell_desc}."
                        
                        if self.update_cell(r, c, val, type="logic", reason=reason):
                            changed = True

            # ── Termination checks ────────────────────────────────────────────
            if self.is_solved():
                return True

            if not changed:
                # No progress made — logic alone cannot proceed further
                return False

    # ── MRV heuristic ──────────────────────────────────────────────────────────

    def get_mrv_line(self) -> Optional[Tuple[str, int]]:
        """
        Find the unresolved line with the **Minimum Remaining Values**.

        Scans every row and column that still contains at least one unknown
        cell (-1) and counts how many valid combinations are consistent with
        the current grid state.  Returns the line that has the fewest options
        (but more than 1 — a line with exactly 1 combo would be handled by
        ``apply_logic`` on the next call).

        The MRV heuristic minimises the branching factor of the backtracking
        search: guessing on the most constrained line is most likely to produce
        an early contradiction and prune large subtrees.

        Returns
        -------
        Tuple[str, int] or None
            ``(line_type, index)`` where *line_type* is ``"row"`` or ``"col"``
            and *index* is the 0-based position.
            Returns ``None`` if every line is already fully determined.
        """
        best_type:  Optional[str] = None
        best_index: int           = -1
        best_count: int           = float("inf")  # type: ignore[assignment]

        for r in range(self.num_rows):
            combos = self._filtered_combinations("row", r)
            if combos is None:
                continue                  # line is fully determined
            count = len(combos)
            if 1 < count < best_count:
                best_count = count
                best_type  = "row"
                best_index = r

        for c in range(self.num_cols):
            combos = self._filtered_combinations("col", c)
            if combos is None:
                continue
            count = len(combos)
            if 1 < count < best_count:
                best_count = count
                best_type  = "col"
                best_index = c

        if best_type is None:
            return None
        return (best_type, best_index)

    # ── Backtracking solver ───────────────────────────────────────────────────

    def backtrack_solve(self) -> bool:
        """
        Solve the puzzle using recursive backtracking with the MRV heuristic.

        Algorithm
        ---------
        1. **Simplify** — run ``apply_logic()`` to propagate all deterministic
           deductions from the current state.
        2. **Terminate** — if the board is solved, return ``True``; if it is
           in a contradictory state, return ``False``.
        3. **Choose** — pick the unresolved line with the fewest valid
           combinations (MRV), minimising the branching factor.
        4. **Branch** — for each valid combination of that line:

           a. **Save** the current grid and history length.
           b. **Apply** the combination, tagging each change as ``'GUESS'``.
           c. **Recurse** — call ``backtrack_solve()`` on the updated board.
           d. **Succeed** — if the recursive call returns ``True``, propagate
              ``True`` up the call stack.
           e. **Restore** — if the recursive call returns ``False``, roll the
              grid back to the saved snapshot and append ``'BACKTRACK'``
              history entries so the frontend can animate the undo step.
        5. If every branch fails, return ``False``.

        Returns
        -------
        bool
            ``True`` if the puzzle was solved, ``False`` if it is unsolvable.
        """
        # ── Step 1: simplify ──────────────────────────────────────────────────
        self.apply_logic()

        # ── Step 2: base cases ────────────────────────────────────────────────
        if self.is_invalid():
            return False
        if self.is_solved():
            return True

        # ── Step 3: pick the most-constrained line (MRV) ─────────────────────
        mrv = self.get_mrv_line()
        if mrv is None:
            # Every line is determined but board not flagged solved — edge case
            return self.is_solved()

        line_type, index = mrv

        # ── Step 4: get all valid combinations for the chosen line ────────────
        combos = self._filtered_combinations(line_type, index)
        if not combos:
            return False   # no options — contradiction

        # ── Step 5: branch over each candidate combination ────────────────────
        for combo in combos:
            # (a) Save state ──────────────────────────────────────────────────
            saved_grid    = copy.deepcopy(self.grid)
            saved_hist_len = len(self.history)

            # (b) Apply combination, tagging entries as GUESS ─────────────────
            if line_type == "row":
                clues = self.rows_clues[index]
                for c, val in enumerate(combo):
                    cell_desc = "đen" if val == 1 else "trống"
                    reason = f"Giả định: Theo cấu hình thử nghiệm {combo} của Hàng {index+1} (Gợi ý {clues}) -> Đặt ô cột {c+1} thành {cell_desc}."
                    self.update_cell(index, c, val, type="GUESS", reason=reason)
            else:
                clues = self.cols_clues[index]
                for r, val in enumerate(combo):
                    cell_desc = "đen" if val == 1 else "trống"
                    reason = f"Giả định: Theo cấu hình thử nghiệm {combo} của Cột {index+1} (Gợi ý {clues}) -> Đặt ô hàng {r+1} thành {cell_desc}."
                    self.update_cell(r, index, val, type="GUESS", reason=reason)

            # (c) Recurse ─────────────────────────────────────────────────────
            if self.backtrack_solve():
                return True   # (d) propagate success

            # (e) Restore — grid snapshot + BACKTRACK history entries ──────────
            self.grid = saved_grid

            # Record each reverted cell as BACKTRACK for the frontend
            guess_entries = self.history[saved_hist_len:]
            del self.history[saved_hist_len:]   # trim speculative entries

            for entry in guess_entries:
                # Emit a BACKTRACK entry only for cells that were actually
                # changed during the guess (val may differ from the restored val)
                r_bt = entry["y"]
                c_bt = entry["x"]
                restored_val = self.grid[r_bt][c_bt]
                cell_desc = "đen" if restored_val == 1 else ("trống" if restored_val == 0 else "trống/chưa rõ")
                reason = f"Quay lui (Backtrack): Phát hiện mâu thuẫn -> Hoàn trả ô hàng {r_bt+1}, cột {c_bt+1} về trạng thái {cell_desc}."
                self.history.append({
                    "x":    c_bt,
                    "y":    r_bt,
                    "val":  restored_val,   # restored value
                    "type": "BACKTRACK",
                    "reason": reason
                })

        return False   # every branch failed

    # ── Private helpers ───────────────────────────────────────────────────────

    def _filtered_combinations(
        self, line_type: str, index: int
    ) -> Optional[List[List[int]]]:
        """
        Generate all combinations for a line that are **consistent** with the
        cells already determined in the grid.

        Returns ``None`` if every cell in the line is already known (fast-path).
        Returns an empty list ``[]`` if no combination is consistent.

        Parameters
        ----------
        line_type : str
            ``"row"`` or ``"col"``.
        index : int
            Index of the row or column.
        """
        if line_type == "row":
            clues  = self.rows_clues[index]
            length = self.num_cols
            current = self.get_row(index)
        else:
            clues  = self.cols_clues[index]
            length = self.num_rows
            current = self.get_col(index)

        # Fast-path: line is already fully determined
        if -1 not in current:
            blocks = []
            count = 0
            for val in current:
                if val == 1:
                    count += 1
                elif val == 0 and count > 0:
                    blocks.append(count)
                    count = 0
            if count > 0:
                blocks.append(count)
            if blocks == clues:
                return None
            else:
                return []

        all_combos = generate_combinations(clues, length)

        # Filter: keep only combinations compatible with fixed cells
        return [
            combo for combo in all_combos
            if all(
                current[i] == -1 or current[i] == combo[i]
                for i in range(length)
            )
        ]

    # ── Display ───────────────────────────────────────────────────────────────

    def __str__(self) -> str:
        """Pretty-print the grid. Uses '#' for black, '.' for white, '?' for unknown."""
        symbol = {1: "#", 0: ".", -1: "?"}
        rows = [
            " ".join(symbol[self.grid[r][c]] for c in range(self.num_cols))
            for r in range(self.num_rows)
        ]
        return "\n".join(rows)

    def __repr__(self) -> str:
        return (
            f"NonogramBoard("
            f"{self.num_rows}x{self.num_cols}, "
            f"solved={self.is_solved()}, "
            f"history_len={len(self.history)})"
        )


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ── Test 1: 5x5 'frame+cross' puzzle — uniquely solvable by logic ──────────
    #
    #   Row clues : [5], [1,1,1], [1,1,1], [1,1,1], [5]
    #   Col clues : [5], [1,1,1], [1,1,1], [1,1,1], [5]
    #
    #   Expected solution:
    #   # # # # #
    #   # . # . #
    #   # . # . #
    #   # . # . #
    #   # # # # #
    rows_clues = [[5], [1, 1, 1], [1, 1, 1], [1, 1, 1], [5]]
    cols_clues = [[5], [1, 1], [5], [1, 1], [5]]

    board = NonogramBoard(rows_clues, cols_clues)

    assert not board.is_solved(),  "New board should not be solved"
    assert not board.is_invalid(), "New board should not be invalid"

    solved = board.apply_logic()
    print("=== Test 1: 5x5 'frame+cross' puzzle ===")
    print(board)
    print(f"Solved by logic: {solved}")
    print(f"History entries: {len(board.history)}")
    print(f"repr: {board!r}")
    assert solved,        "Puzzle should be solvable by logic alone"
    assert board.is_solved()
    print("[PASS] Test 1\n")

    # ── Test 2: update_cell skips duplicate writes ─────────────────────────────
    board2 = NonogramBoard([[1]], [[1]])
    changed1 = board2.update_cell(0, 0, 1, "user")
    changed2 = board2.update_cell(0, 0, 1, "user")   # same value — should skip
    assert changed1 is True
    assert changed2 is False
    assert len(board2.history) == 1, "History should have exactly 1 entry"
    print("[PASS] Test 2: update_cell skips duplicates\n")

    # ── Test 3: is_invalid on a contradictory board ───────────────────────────
    # Force a contradiction: clue=[3] but length=3, then pre-fill cell 1 as 0
    board3 = NonogramBoard([[3]], [[1], [1], [1]])
    board3.grid[0][1] = 0   # middle cell white — impossible for clue [3]
    assert board3.is_invalid(), "Board with impossible row should be invalid"
    print("[PASS] Test 3: is_invalid detects contradiction\n")

    # ── Test 4: get_row / get_col return copies ───────────────────────────────
    board4 = NonogramBoard([[1, 1]], [[1], [1], [1]])
    row = board4.get_row(0)
    row[0] = 999           # mutating the copy must not affect the grid
    assert board4.grid[0][0] == -1
    col = board4.get_col(0)
    col[0] = 999
    assert board4.grid[0][0] == -1
    print("[PASS] Test 4: get_row/get_col return independent copies\n")

    # ── Test 5: puzzle that requires backtracking ────────────────────────────
    #
    #   A 5x5 puzzle that cannot be fully solved by constraint propagation
    #   alone — requires at least one guess + possible backtrack.
    #
    #   Row clues: [1,1], [2], [1,1], [2], [1,1]
    #   Col clues: [1,1], [2], [1,1], [2], [1,1]
    rows_clues5 = [[1, 1], [2], [1, 1], [2], [1, 1]]
    cols_clues5 = [[1, 1], [2], [1, 1], [2], [1, 1]]

    board5 = NonogramBoard(rows_clues5, cols_clues5)
    result5 = board5.backtrack_solve()
    print("=== Test 5: backtracking puzzle ===")
    print(board5)
    guess_count     = sum(1 for h in board5.history if h["type"] == "GUESS")
    backtrack_count = sum(1 for h in board5.history if h["type"] == "BACKTRACK")
    print(f"Solved: {result5}  |  GUESS entries: {guess_count}  |  BACKTRACK entries: {backtrack_count}")
    assert result5, "Backtracking should solve the puzzle"
    assert board5.is_solved()
    print("[PASS] Test 5\n")

    # ── Test 6: unsolvable puzzle — backtrack must return False ───────────────
    # Row clue [3] in a 2-cell row is impossible from the start.
    rows_clues6 = [[3], [1]]
    cols_clues6 = [[1], [1]]
    board6 = NonogramBoard(rows_clues6, cols_clues6)
    result6 = board6.backtrack_solve()
    assert not result6, "Unsolvable puzzle should return False"
    print("[PASS] Test 6: unsolvable puzzle returns False\n")

    print("All tests passed!")
