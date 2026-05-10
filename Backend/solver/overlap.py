"""
overlap.py
----------
Nonogram solver utility: given all valid configurations of a row/column,
determines the "overlap" — which cells are definitely black (1), definitely
white (0), or still unknown (-1).

Intended to be called after generate_combinations() from combinations.py.
"""

from typing import List, Optional


class ImpossibleStateError(Exception):
    """Raised when the combination list is empty (board state is unsolvable)."""


def get_overlap(combinations: List[List[int]], length: int) -> Optional[List[int]]:
    """
    Determine the certain and uncertain cells across all valid combinations.

    For each cell position, compare its value across every combination:
      - If every combination has 1  → the cell is definitely black  ( 1)
      - If every combination has 0  → the cell is definitely white  ( 0)
      - If combinations disagree    → the cell is unknown           (-1)

    Parameters
    ----------
    combinations : List[List[int]]
        All valid configurations for a row/column, as produced by
        ``generate_combinations()``.  Each inner list is a sequence of
        0s (white) and 1s (black) of length ``length``.
    length : int
        The expected length of each configuration.

    Returns
    -------
    List[int]
        A list of length ``length`` whose values are 1, 0, or -1.

    Raises
    ------
    ImpossibleStateError
        If ``combinations`` is empty, meaning no valid configuration exists
        for the current board state (i.e. the puzzle is in an impossible state).

    Examples
    --------
    >>> get_overlap([[1, 1, 0, 1], [1, 1, 0, 0]], length=4)
    [1, 1, 0, -1]

    >>> get_overlap([[1, 1, 0, 1, 0], [1, 1, 0, 0, 1], [0, 1, 1, 0, 1]], length=5)
    [-1, 1, -1, -1, -1]

    >>> get_overlap([[0, 0, 0, 0]], length=4)
    [0, 0, 0, 0]
    """
    if not combinations:
        raise ImpossibleStateError(
            "No valid combinations exist — the current board state is impossible."
        )

    result: List[int] = []

    # zip(*combinations) transposes the list-of-rows into a list-of-columns,
    # so `column` is a tuple of the i-th cell value from every combination.
    # This is an O(n * k) pass with no extra intermediate structures.
    for column in zip(*combinations):
        first = column[0]
        # all() short-circuits on the first mismatch → efficient for large sets
        if all(cell == first for cell in column):
            result.append(first)   # definitely 1 or definitely 0
        else:
            result.append(-1)      # varies → unknown

    return result


# ── Quick self-test when run directly ────────────────────────────────────────
if __name__ == "__main__":
    import traceback

    test_cases = [
        # (combinations, length, expected_output)
        ([[1, 1, 0, 1], [1, 1, 0, 0]],                          4, [1, 1, 0, -1]),
        ([[1, 1, 0, 1, 0], [1, 1, 0, 0, 1], [0, 1, 1, 0, 1]],  5, [-1, 1, -1, -1, -1]),
        ([[0, 0, 0, 0]],                                          4, [0, 0, 0, 0]),
        ([[1, 1, 1]],                                             3, [1, 1, 1]),
        ([[1, 0, 1], [0, 1, 1], [1, 1, 0]],                      3, [-1, -1, -1]),
    ]

    all_passed = True

    for combos, length, expected in test_cases:
        result = get_overlap(combos, length)
        ok = result == expected
        status = "[PASS]" if ok else "[FAIL]"
        if not ok:
            all_passed = False
        print(f"{status} | combinations={combos}")
        if not ok:
            print(f"       Expected : {expected}")
            print(f"       Got      : {result}")

    # Edge case: empty combinations must raise ImpossibleStateError
    try:
        get_overlap([], 5)
        print("[FAIL] | empty combinations — expected ImpossibleStateError, but no error raised")
        all_passed = False
    except ImpossibleStateError as e:
        print(f"[PASS] | empty combinations raised ImpossibleStateError: {e}")
    except Exception as e:
        print(f"[FAIL] | empty combinations raised unexpected error: {e}")
        traceback.print_exc()
        all_passed = False

    print("\nAll tests passed!" if all_passed else "\nSome tests FAILED.")
