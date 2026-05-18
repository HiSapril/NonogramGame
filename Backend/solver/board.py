"""
board.py
--------
Trình quản lý trạng thái trò chơi Nonogram.

Điều phối lưới chơi, việc theo dõi lịch sử thao tác, và vòng lặp suy luận 
lan truyền ràng buộc (constraint-propagation deduction loop) sử dụng 
generate_combinations() và get_overlap() từ các module cùng cấp.
"""

import copy
from typing import List, Dict, Any, Optional, Tuple

try:
    # Nhập gói (cách dùng thông thường: từ solver.board nhập NonogramBoard)
    from .combinations import generate_combinations
    from .overlap import get_overlap, ImpossibleStateError
except ImportError:
    # Chạy trực tiếp: python board.py
    from combinations import generate_combinations          # type: ignore
    from overlap import get_overlap, ImpossibleStateError   # type: ignore


# ── Bí danh kiểu dữ liệu (Type aliases) ─────────────────────────────────────────────────
Clues     = List[int]
Grid      = List[List[int]]
HistEntry = Dict[str, Any]   # {"x": int, "y": int, "val": int, "type": str}


class NonogramBoard:
    """
    Quản lý toàn bộ trạng thái của một câu đố Nonogram.

    Giá trị của lưới
    ----------------
    -1 : chưa biết (chưa được xác định)
     0 : ô trắng (trống)
     1 : ô đen (được tô)

    Tham số
    -------
    rows_clues : List[List[int]]
        Một danh sách gợi ý cho mỗi hàng (ví dụ: [[3], [1, 1], [2]]).
    cols_clues : List[List[int]]
        Một danh sách gợi ý cho mỗi cột.

    Thuộc tính
    ----------
    grid    : danh sách 2 chiều list[int] có kích thước (số_hàng × số_cột),
              được khởi tạo với giá trị -1.
    history : Danh sách các bản ghi thay đổi {"x", "y", "val", "type"}.
    """

    def __init__(self, rows_clues: List[Clues], cols_clues: List[Clues]) -> None:
        self.rows_clues: List[Clues] = rows_clues
        self.cols_clues: List[Clues] = cols_clues

        self.num_rows: int = len(rows_clues)
        self.num_cols: int = len(cols_clues)

        # Lưới được khởi tạo là -1 (tất cả chưa xác định)
        self.grid: Grid = [
            [-1] * self.num_cols for _ in range(self.num_rows)
        ]

        # Lịch sử kiểm tra đầy đủ của mọi thay đổi ô
        self.history: List[HistEntry] = []

    # ── Các phương thức truy cập (Accessors) ─────────────────────────────────────────────────────

    def get_row(self, index: int) -> List[int]:
        """Trả về một *bản sao* trạng thái hiện tại của hàng ``index``."""
        return list(self.grid[index])

    def get_col(self, index: int) -> List[int]:
        """Trả về một *bản sao* trạng thái hiện tại của cột ``index``."""
        return [self.grid[r][index] for r in range(self.num_rows)]

    # ── Các phương thức thay đổi (Mutation) ──────────────────────────────────────────────────────

    def update_cell(self, r: int, c: int, val: int, type: str = "logic", reason: str = "") -> bool:
        """
        Cập nhật ô (r, c) thành ``val`` và ghi lại thay đổi vào lịch sử.

        Việc cập nhật sẽ bị bỏ qua (và trả về ``False``) nếu ô đó đã
        chứa giá trị ``val``, giúp lịch sử gọn nhẹ và vòng lặp suy luận
        hoạt động hiệu quả hơn.

        Tham số
        -------
        r, c : int
            Chỉ số hàng và cột (đánh số từ 0).
        val  : int
            Giá trị mới của ô: 0 (trắng) hoặc 1 (đen).
        type : str
            Nguồn gốc của thay đổi, ví dụ ``"logic"`` (suy luận) hoặc
            ``"user"`` (nhập thủ công). Được lưu nguyên văn vào lịch sử.
        reason : str
            Giải thích lý do tại sao thay đổi này được suy luận ra.

        Giá trị trả về
        --------------
        bool
            ``True`` nếu ô thực sự được thay đổi, ngược lại là ``False``.
        """
        if self.grid[r][c] == val:
            return False   # không có thay đổi — bỏ qua

        self.grid[r][c] = val
        self.history.append({"x": c, "y": r, "val": val, "type": type, "reason": reason})
        return True

    # ── Kiểm tra trạng thái (Status checks) ─────────────────────────────────────────────────

    def is_solved(self) -> bool:
        """Trả về ``True`` khi mọi ô đã được xác định (không còn ô -1)."""
        return all(
            self.grid[r][c] != -1
            for r in range(self.num_rows)
            for c in range(self.num_cols)
        )

    def is_invalid(self) -> bool:
        """
        Trả về ``True`` nếu trạng thái hiện tại của bảng được chứng minh là
        không thể giải được.

        Một trạng thái được xem là không hợp lệ khi có ít nhất một hàng hoặc
        một cột không còn tổ hợp hợp lệ nào phù hợp với các ô đã được điền.
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

    # ── Lan truyền ràng buộc (Constraint propagation) ────────────────────────────────────────────────

    def apply_logic(self) -> bool:
        """
        Chạy vòng lặp suy luận lan truyền ràng buộc
        (constraint-propagation deduction loop).

        Mỗi vòng lặp:
        1. Với mỗi hàng — tạo tất cả các tổ hợp tương thích với trạng thái
           hiện tại của lưới, tính phần giao nhau (overlap), và cố định
           các ô chắc chắn.
        2. Lặp lại tương tự cho mỗi cột.
        3. Nếu *bất kỳ* ô nào được cập nhật trong vòng lặp này, quay lại
           bước 1 (một cập nhật ở cột có thể mở ra các suy luận mới cho hàng
           và ngược lại).
        4. Dừng khi một lượt quét hoàn chỉnh không tạo ra thông tin mới,
           hoặc khi bảng được giải xong / trở nên không hợp lệ.

        Giá trị trả về
        --------------
        bool
            ``True``  — bảng đã được giải hoàn toàn chỉ bằng suy luận logic.
            ``False`` — vòng lặp bị bế tắc (cần quay lui / phỏng đoán)
                        hoặc bảng rơi vào trạng thái không hợp lệ.
        """
        while True:
            changed = False

            # ── Quét hàng (Row pass) ──────────────────────────────────────────────────────
            for r in range(self.num_rows):
                combos = self._filtered_combinations("row", r)

                if combos is None:
                    continue   # hàng không còn ô nào chưa biết; không cần làm gì cả

                if len(combos) == 0:
                    return False   # mâu thuẫn — không có tổ hợp hợp lệ nào cho hàng này

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

            # ── Quét cột (Column pass) ───────────────────────────────────────────────────
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

            # ── Kiểm tra kết thúc (Termination checks) ────────────────────────────────────────────
            if self.is_solved():
                return True

            if not changed:
                # Không tiến triển thêm — riêng suy luận logic không thể tiếp tục tiến xa hơn
                return False

    # ── Heuristic MRV ──────────────────────────────────────────────────────────

    def get_mrv_line(self) -> Optional[Tuple[str, int]]:
        """
        Tìm dòng chưa được giải quyết với tiêu chí **Giá trị còn lại tối thiểu**
        (Minimum Remaining Values - MRV).

        Quét qua mọi hàng và cột vẫn còn ít nhất một ô chưa biết (-1)
        và đếm số lượng tổ hợp hợp lệ phù hợp với trạng thái hiện tại
        của lưới. Trả về dòng có ít lựa chọn nhất
        (nhưng lớn hơn 1 — một dòng chỉ có đúng 1 tổ hợp sẽ được xử lý bởi
        ``apply_logic`` ở lần gọi tiếp theo).

        Heuristic MRV giúp giảm hệ số phân nhánh của thuật toán quay lui
        (backtracking): phỏng đoán trên dòng bị ràng buộc nhiều nhất sẽ có
        khả năng tạo ra mâu thuẫn sớm hơn và loại bỏ các nhánh lớn của cây tìm kiếm.

        Giá trị trả về
        --------------
        Tuple[str, int] hoặc None
            ``(line_type, index)`` trong đó *line_type* là ``"row"`` hoặc ``"col"``
            và *index* là vị trí đánh số từ 0.
            Trả về ``None`` nếu mọi dòng đã được xác định hoàn toàn.
        """
        best_type:  Optional[str] = None
        best_index: int           = -1
        best_count: int           = float("inf")  # type: ignore[assignment]

        for r in range(self.num_rows):
            combos = self._filtered_combinations("row", r)
            if combos is None:
                continue                  # dòng đã được xác định hoàn toàn
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

    # ── Bộ giải quay lui (Backtracking solver) ───────────────────────────────────────────────────

    def backtrack_solve(self) -> bool:
        """
        Giải câu đố bằng thuật toán quay lui đệ quy (recursive backtracking)
        kết hợp heuristic MRV.

        Thuật toán
        -----------
        1. **Đơn giản hóa** — chạy ``apply_logic()`` để lan truyền toàn bộ
           các suy luận xác định được từ trạng thái hiện tại.
        2. **Kết thúc** — nếu bảng đã được giải, trả về ``True``; nếu bảng
           rơi vào trạng thái mâu thuẫn, trả về ``False``.
        3. **Chọn** — chọn dòng chưa được giải có ít tổ hợp hợp lệ nhất
           (MRV), nhằm giảm hệ số phân nhánh.
        4. **Phân nhánh** — với mỗi tổ hợp hợp lệ của dòng đó:

           a. **Lưu** trạng thái hiện tại của lưới và độ dài lịch sử.
           b. **Áp dụng** tổ hợp, đánh dấu mỗi thay đổi bằng ``'GUESS'``.
           c. **Đệ quy** — gọi ``backtrack_solve()`` trên bảng đã cập nhật.
           d. **Thành công** — nếu lời gọi đệ quy trả về ``True``, truyền
              ``True`` ngược lên ngăn xếp lời gọi.
           e. **Khôi phục** — nếu lời gọi đệ quy trả về ``False``, hoàn tác
              lưới về trạng thái đã lưu và thêm các mục lịch sử
              ``'BACKTRACK'`` để frontend có thể hiển thị hoạt ảnh bước hoàn tác.
        5. Nếu mọi nhánh đều thất bại, trả về ``False``.

        Giá trị trả về
        --------------
        bool
            ``True`` nếu câu đố được giải, ``False`` nếu không thể giải được.
        """
        # ── Bước 1: Đơn giản hóa ──────────────────────────────────────────────────
        self.apply_logic()

        # ── Bước 2: Các trường hợp cơ sở ────────────────────────────────────────────────
        if self.is_invalid():
            return False
        if self.is_solved():
            return True

        # ── Bước 3: Chọn dòng bị ràng buộc nhiều nhất (MRV) ─────────────────────
        mrv = self.get_mrv_line()
        if mrv is None:
            # Mọi dòng đã được xác định nhưng bảng chưa được đánh dấu đã giải — trường hợp đặc biệt
            return self.is_solved()

        line_type, index = mrv

        # ── Bước 4: Lấy tất cả các tổ hợp hợp lệ cho dòng đã chọn ────────────
        combos = self._filtered_combinations(line_type, index)
        if not combos:
            return False   # không có lựa chọn nào — mâu thuẫn

        # ── Bước 5: Phân nhánh qua từng tổ hợp ứng viên ────────────────────
        for combo in combos:
            # (a) Lưu trạng thái ──────────────────────────────────────────────────
            saved_grid    = copy.deepcopy(self.grid)
            saved_hist_len = len(self.history)

            # (b) Áp dụng tổ hợp, đánh dấu các mục là GUESS ─────────────────
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

            # (c) Đệ quy ─────────────────────────────────────────────────────
            if self.backtrack_solve():
                return True   # (d) truyền thành công ngược lên

            # (e) Khôi phục — ảnh chụp nhanh lưới + các mục lịch sử BACKTRACK ──────────
            self.grid = saved_grid

            # Ghi lại mỗi ô đã hoàn tác dưới dạng BACKTRACK cho frontend
            guess_entries = self.history[saved_hist_len:]
            del self.history[saved_hist_len:]   # cắt tỉa bớt các mục phỏng đoán speculative

            for entry in guess_entries:
                # Chỉ phát ra mục BACKTRACK cho những ô thực sự đã bị
                # thay đổi trong quá trình phỏng đoán (val có thể khác với val đã phục hồi)
                r_bt = entry["y"]
                c_bt = entry["x"]
                restored_val = self.grid[r_bt][c_bt]
                cell_desc = "đen" if restored_val == 1 else ("trống" if restored_val == 0 else "trống/chưa rõ")
                reason = f"Quay lui (Backtrack): Phát hiện mâu thuẫn -> Hoàn trả ô hàng {r_bt+1}, cột {c_bt+1} về trạng thái {cell_desc}."
                self.history.append({
                    "x":    c_bt,
                    "y":    r_bt,
                    "val":  restored_val,   # giá trị được khôi phục
                    "type": "BACKTRACK",
                    "reason": reason
                })

        return False   # mọi nhánh đều thất bại

    # ── Các hàm trợ giúp riêng tư (Private helpers) ───────────────────────────────────────────────────────

    def _filtered_combinations(
        self, line_type: str, index: int
    ) -> Optional[List[List[int]]]:
        """
        Tạo tất cả các tổ hợp cho một dòng sao cho **phù hợp**
        với các ô đã được xác định trong lưới.

        Trả về ``None`` nếu mọi ô trong dòng đã được biết trước
        (đường xử lý nhanh - fast-path).
        Trả về danh sách rỗng ``[]`` nếu không có tổ hợp nào phù hợp.

        Tham số
        -------
        line_type : str
            ``"row"`` hoặc ``"col"``.
        index : int
            Chỉ số của hàng hoặc cột.
        """
        if line_type == "row":
            clues  = self.rows_clues[index]
            length = self.num_cols
            current = self.get_row(index)
        else:
            clues  = self.cols_clues[index]
            length = self.num_rows
            current = self.get_col(index)

        # Fast-path: dòng đã được xác định hoàn toàn
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
            normalized_clues = [c for c in clues if c > 0]
            if blocks == normalized_clues:
                return None
            else:
                return []

        all_combos = generate_combinations(clues, length)

        # Bộ lọc: chỉ giữ lại các tổ hợp tương thích với các ô cố định
        return [
            combo for combo in all_combos
            if all(
                current[i] == -1 or current[i] == combo[i]
                for i in range(length)
            )
        ]

    # ── Display ───────────────────────────────────────────────────────────────

    def __str__(self) -> str:
        """In bảng lưới ra màn hình một cách đẹp đẽ. Sử dụng '#' cho ô đen, '.' cho ô trắng, '?' cho ô chưa xác định."""
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


# ── Tự kiểm thử (Self-test) ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ── Test 1: Câu đố 5x5 'khung + chữ thập' — có thể giải duy nhất bằng logic ──────────
    #
    #   Gợi ý hàng : [5], [1,1,1], [1,1,1], [1,1,1], [5]
    #   Gợi ý cột  : [5], [1,1,1], [1,1,1], [1,1,1], [5]
    #
    #   Giải pháp mong đợi:
    #   # # # # #
    #   # . # . #
    #   # . # . #
    #   # . # . #
    #   # # # # #
    rows_clues = [[5], [1, 1, 1], [1, 1, 1], [1, 1, 1], [5]]
    cols_clues = [[5], [1, 1], [5], [1, 1], [5]]

    board = NonogramBoard(rows_clues, cols_clues)

    assert not board.is_solved(),  "Bảng mới không được coi là đã giải xong"
    assert not board.is_invalid(), "Bảng mới không được coi là không hợp lệ"

    solved = board.apply_logic()
    print("=== Test 1: 5x5 'frame+cross' puzzle ===")
    print(board)
    print(f"Solved by logic: {solved}")
    print(f"History entries: {len(board.history)}")
    print(f"repr: {board!r}")
    assert solved,        "Câu đố phải giải được chỉ bằng logic"
    assert board.is_solved()
    print("[PASS] Test 1\n")

    # ── Test 2: update_cell bỏ qua ghi đè trùng lặp ─────────────────────────────
    board2 = NonogramBoard([[1]], [[1]])
    changed1 = board2.update_cell(0, 0, 1, "user")
    changed2 = board2.update_cell(0, 0, 1, "user")   # cùng giá trị — nên bỏ qua
    assert changed1 is True
    assert changed2 is False
    assert len(board2.history) == 1, "Lịch sử phải có chính xác 1 mục ghi chép"
    print("[PASS] Test 2: update_cell skips duplicates\n")

    # ── Test 3: is_invalid trên một bảng mâu thuẫn ───────────────────────────
    # Buộc xảy ra mâu thuẫn: gợi ý=[3] nhưng độ dài=3, sau đó điền trước ô thứ 1 là 0
    board3 = NonogramBoard([[3]], [[1], [1], [1]])
    board3.grid[0][1] = 0   # ô giữa màu trắng — điều không thể đối với gợi ý [3]
    assert board3.is_invalid(), "Bảng có hàng bất khả thi phải bị coi là không hợp lệ"
    print("[PASS] Test 3: is_invalid detects contradiction\n")

    # ── Test 4: get_row / get_col trả về các bản sao riêng biệt ───────────────────────────────
    board4 = NonogramBoard([[1, 1]], [[1], [1], [1]])
    row = board4.get_row(0)
    row[0] = 999           # thay đổi bản sao không được ảnh hưởng đến bảng lưới
    assert board4.grid[0][0] == -1
    col = board4.get_col(0)
    col[0] = 999
    assert board4.grid[0][0] == -1
    print("[PASS] Test 4: get_row/get_col return independent copies\n")

    # ── Test 5: Câu đố yêu cầu thuật toán quay lui (backtracking) ────────────────────────────
    #
    #   Một câu đố 5x5 không thể giải hoàn toàn chỉ bằng lan truyền ràng buộc
    #   thông thường — yêu cầu ít nhất một phỏng đoán + khả năng quay lui.
    #
    #   Gợi ý hàng: [1,1], [2], [1,1], [2], [1,1]
    #   Gợi ý cột : [1,1], [2], [1,1], [2], [1,1]
    rows_clues5 = [[1, 1], [2], [1, 1], [2], [1, 1]]
    cols_clues5 = [[1, 1], [2], [1, 1], [2], [1, 1]]

    board5 = NonogramBoard(rows_clues5, cols_clues5)
    result5 = board5.backtrack_solve()
    print("=== Test 5: backtracking puzzle ===")
    print(board5)
    guess_count     = sum(1 for h in board5.history if h["type"] == "GUESS")
    backtrack_count = sum(1 for h in board5.history if h["type"] == "BACKTRACK")
    print(f"Solved: {result5}  |  GUESS entries: {guess_count}  |  BACKTRACK entries: {backtrack_count}")
    assert result5, "Thuật toán quay lui phải giải được câu đố"
    assert board5.is_solved()
    print("[PASS] Test 5\n")

    # ── Test 6: Câu đố không thể giải — backtrack phải trả về False ───────────────
    # Hàng có gợi ý [3] trên dòng có 2 ô là điều không thể ngay từ đầu.
    rows_clues6 = [[3], [1]]
    cols_clues6 = [[1], [1]]
    board6 = NonogramBoard(rows_clues6, cols_clues6)
    result6 = board6.backtrack_solve()
    assert not result6, "Câu đố bất khả thi phải trả về False"
    print("[PASS] Test 6: unsolvable puzzle returns False\n")

    print("All tests passed!")
