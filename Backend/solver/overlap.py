"""
overlap.py
----------
Nonogram solver utility: với tất cả các cấu hình hợp lệ của một hàng/cột,
xác định phần "giao nhau" (overlap) — ô nào chắc chắn là màu đen (1),
chắc chắn là màu trắng (0), hoặc vẫn chưa xác định (-1).

Được thiết kế để gọi sau ``generate_combinations()`` từ combinations.py.
"""

from typing import List, Optional


class ImpossibleStateError(Exception):
    """Raised when the combination list is empty (board state is unsolvable)."""


def get_overlap(combinations: List[List[int]], length: int) -> Optional[List[int]]:
    """
    Xác định các ô chắc chắn và không chắc chắn giữa tất cả các tổ hợp hợp lệ.

    Với mỗi vị trí ô, so sánh giá trị của nó trên mọi tổ hợp:
      - Nếu mọi tổ hợp đều có giá trị 1  → ô chắc chắn là màu đen   ( 1)
      - Nếu mọi tổ hợp đều có giá trị 0  → ô chắc chắn là màu trắng ( 0)
      - Nếu các tổ hợp khác nhau         → ô chưa xác định          (-1)

    Tham số
    -------
    combinations : List[List[int]]
        Tất cả các cấu hình hợp lệ cho một hàng/cột, được tạo bởi
        ``generate_combinations()``. Mỗi danh sách bên trong là một dãy
        gồm các số 0 (trắng) và 1 (đen) có độ dài ``length``.
    length : int
        Độ dài mong đợi của mỗi cấu hình.

    Giá trị trả về
    --------------
    List[int]
        Một danh sách có độ dài ``length`` với các giá trị 1, 0 hoặc -1.

    Ngoại lệ
    --------
    ImpossibleStateError
        Được phát sinh nếu ``combinations`` rỗng, nghĩa là không tồn tại
        cấu hình hợp lệ nào cho trạng thái hiện tại của bảng
        (tức là câu đố đang ở trạng thái không thể giải được).

    Ví dụ
    -----
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
