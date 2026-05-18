"""
combinations.py
---------------
Nonogram solver utility: tạo tất cả các cấu hình dòng hợp lệ thỏa mãn
một tập gợi ý cho trước trong một độ dài cố định.

Một "cấu hình" là danh sách gồm các số 0 (ô trắng) và 1 (ô đen),
trong đó các số 1 liên tiếp tạo thành các khối có độ dài khớp chính xác
với các gợi ý, và mỗi cặp khối liền kề phải được ngăn cách bởi ít nhất
một số 0.
"""

from functools import lru_cache
from typing import List, Tuple


def generate_combinations(clues: List[int], length: int) -> List[List[int]]:
    """
    Tạo tất cả các cấu hình hợp lệ cho một hàng/cột trong Nonogram.

    Tham số
    -------
    clues : List[int]
        Độ dài các khối ô đen liên tiếp theo đúng thứ tự.
        Ví dụ: [3, 1] nghĩa là một khối gồm 3 ô đen,
        sau đó là một khối gồm 1 ô đen.
    length : int
        Tổng số ô trong hàng hoặc cột.

    Giá trị trả về
    --------------
    List[List[int]]
        Tất cả các cấu hình hợp lệ dưới dạng danh sách các số 0 và 1.
        Trả về danh sách rỗng nếu các gợi ý không thể vừa trong độ dài đã cho.

    Ví dụ
    -----
    >>> generate_combinations([2, 1], 5)
    [[1, 1, 0, 1, 0], [1, 1, 0, 0, 1], [0, 1, 1, 0, 1]]

    >>> generate_combinations([], 4)
    [[0, 0, 0, 0]]

    >>> generate_combinations([5], 3)
    []
    """
    # Normalize clues: [0] or empty clues mean no black blocks
    clues = [c for c in clues if c > 0]

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
        Đệ quy xây dựng tất cả các hậu tố hợp lệ.

        Tham số
        -------
        remaining_clues : Tuple[int, ...]
            Các gợi ý chưa được đặt.
        remaining_length : int
            Số lượng ô còn khả dụng.

        Giá trị trả về
        --------------
        List[Tuple[int, ...]]
            Mỗi phần tử là một tuple gồm các số 0/1 biểu diễn
            một hậu tố hợp lệ.
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
