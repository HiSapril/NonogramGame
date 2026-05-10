"""
combinations.py
---------------
Nonogram solver utility: generates all valid line configurations that satisfy
a given set of clues within a fixed length.

A "configuration" is a list of 0s (white) and 1s (black) where consecutive 1s
form blocks whose lengths exactly match the clues, and every pair of adjacent
blocks is separated by at least one 0.
"""

from functools import lru_cache
from typing import List, Tuple


def generate_combinations(clues: List[int], length: int) -> List[List[int]]:
    """
    Generate all valid configurations for a nonogram row/column.

    Parameters
    ----------
    clues : List[int]
        Ordered block lengths of consecutive black cells.
        Example: [3, 1] means a block of 3 blacks then a block of 1 black.
    length : int
        Total number of cells in the row or column.

    Returns
    -------
    List[List[int]]
        All valid configurations as lists of 0s and 1s.
        Returns an empty list if the clues cannot fit in the given length.

    Examples
    --------
    >>> generate_combinations([2, 1], 5)
    [[1, 1, 0, 1, 0], [1, 1, 0, 0, 1], [0, 1, 1, 0, 1]]

    >>> generate_combinations([], 4)
    [[0, 0, 0, 0]]

    >>> generate_combinations([5], 3)
    []
    """
    # Convert to tuple so it is hashable for lru_cache
    clues_tuple = tuple(clues)

    # Minimum space required:
    #   sum of all block sizes + at least (n-1) separator whites between n blocks
    min_length = sum(clues_tuple) + max(len(clues_tuple) - 1, 0)
    if min_length > length:
        return []

    @lru_cache(maxsize=None)
    def _solve(remaining_clues: Tuple[int, ...], remaining_length: int) -> List[Tuple[int, ...]]:
        """
        Recursively build all valid suffixes.

        Parameters
        ----------
        remaining_clues : Tuple[int, ...]
            Clues that have not yet been placed.
        remaining_length : int
            Number of cells still available.

        Returns
        -------
        List[Tuple[int, ...]]
            Each element is a tuple of 0s/1s representing a valid suffix.
        """
        # ── Base case: no clues left ──────────────────────────────────────────
        if not remaining_clues:
            # All remaining cells must be white
            return [(0,) * remaining_length]

        # ── Pruning: not enough space for the remaining clues ─────────────────
        min_needed = sum(remaining_clues) + len(remaining_clues) - 1
        if min_needed > remaining_length:
            return []

        block = remaining_clues[0]
        rest  = remaining_clues[1:]
        results: List[Tuple[int, ...]] = []

        # Number of positions at which the current block can START.
        # The block (plus its mandatory trailing white, if more clues follow)
        # must fit within the remaining space.
        trailing = 1 if rest else 0          # mandatory separator after block
        max_start = remaining_length - block - trailing - (sum(rest) + len(rest) - 1 if rest else 0)

        for start in range(max_start + 1):
            # `start` white cells before the block
            prefix: Tuple[int, ...] = (0,) * start + (1,) * block

            if rest:
                # Mandatory single white separator, then recurse
                prefix += (0,)
                suffix_length = remaining_length - len(prefix)
                for suffix in _solve(rest, suffix_length):
                    results.append(prefix + suffix)
            else:
                # Last block: pad remaining cells with whites
                whites_after = remaining_length - len(prefix)
                results.append(prefix + (0,) * whites_after)

        return results

    raw_results = _solve(clues_tuple, length)
    # Convert tuples → lists for a friendlier public API
    return [list(config) for config in raw_results]


# ── Quick self-test when run directly ────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        (([2, 1], 5),  [[1, 1, 0, 1, 0], [1, 1, 0, 0, 1], [0, 1, 1, 0, 1]]),
        (([3],    5),  [[1, 1, 1, 0, 0], [0, 1, 1, 1, 0], [0, 0, 1, 1, 1]]),
        (([],     4),  [[0, 0, 0, 0]]),
        (([5],    3),  []),
        (([1, 1], 3),  [[1, 0, 1]]),
    ]

    all_passed = True
    for (clues, length), expected in test_cases:
        result = generate_combinations(clues, length)
        status = "[PASS]" if result == expected else "[FAIL]"
        if result != expected:
            all_passed = False
        print(f"{status} | clues={clues}, length={length}")
        if result != expected:
            print(f"       Expected : {expected}")
            print(f"       Got      : {result}")

    print("\nAll tests passed!" if all_passed else "\nSome tests FAILED.")
