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
    # Chuẩn hóa gợi ý: [0] hoặc gợi ý rỗng nghĩa là không có khối ô đen nào
    clues = [c for c in clues if c > 0]

    # Chuyển sang tuple để có thể băm (hashable) cho lru_cache
    clues_tuple = tuple(clues)

    # Không gian tối thiểu cần thiết:
    #   tổng của tất cả kích thước khối + ít nhất (n-1) khoảng trắng ngăn cách giữa n khối
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
        # ── Trường hợp cơ sở: không còn gợi ý nào ──────────────────────────────────
        if not remaining_clues:
            # Tất cả các ô còn lại phải là màu trắng
            return [(0,) * remaining_length]

        # ── Tỉa nhánh: không đủ không gian cho các gợi ý còn lại ─────────────────
        min_needed = sum(remaining_clues) + len(remaining_clues) - 1
        if min_needed > remaining_length:
            return []

        block = remaining_clues[0]
        rest  = remaining_clues[1:]
        results: List[Tuple[int, ...]] = []

        # Số lượng vị trí mà khối hiện tại có thể BẮT ĐẦU.
        # Khối (cộng thêm ô trắng bắt buộc theo sau, nếu còn gợi ý tiếp theo)
        # phải vừa với không gian còn lại.
        trailing = 1 if rest else 0          # dải phân cách bắt buộc sau khối
        max_start = remaining_length - block - trailing - (sum(rest) + len(rest) - 1 if rest else 0)

        for start in range(max_start + 1):
            # `start` ô trắng trước khối
            prefix: Tuple[int, ...] = (0,) * start + (1,) * block

            if rest:
                # Ô trắng phân cách bắt buộc duy nhất, sau đó đệ quy
                prefix += (0,)
                suffix_length = remaining_length - len(prefix)
                for suffix in _solve(rest, suffix_length):
                    results.append(prefix + suffix)
            else:
                # Khối cuối cùng: lấp đầy các ô còn lại bằng ô trắng
                whites_after = remaining_length - len(prefix)
                results.append(prefix + (0,) * whites_after)

        return results

    raw_results = _solve(clues_tuple, length)
    # Chuyển đổi tuple → list để cung cấp API thân thiện hơn
    return [list(config) for config in raw_results]


# ── Kiểm thử nhanh khi chạy trực tiếp ────────────────────────────────────────
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
