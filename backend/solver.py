from collections import deque
from functools import lru_cache
from math import isqrt
import heapq
import itertools
import random
import time
from typing import Dict, List, Optional, Tuple


# ==============================================================================
# BAGIAN 1: KONFIGURASI, EXCEPTION, VALIDASI PAPAN & HELPER FUNCTIONS
# ==============================================================================

Board = List[int]
StateTuple = Tuple[int, ...]  # isinya int, jumlahnya sebanyak N*N

# Ukuran papan yang didukung: 3x3 (8-puzzle), 4x4 (15-puzzle), 5x5 (24-puzzle)
SUPPORTED_SIZES = (3, 4, 5)

# Batas pencarian per algoritma agar server tidak kehabisan memori / hang.
# max_nodes   : batas jumlah state yang tersimpan di memori (visited/best_g)
# timeout_sec : batas waktu eksekusi pencarian dalam detik
SEARCH_LIMITS: Dict[str, Dict[str, float]] = {
    "BFS": {"max_nodes": 20_000_000, "timeout_sec": 360.0},
    "GBFS": {"max_nodes": 500_000, "timeout_sec": 30.0},
    "ASTAR": {"max_nodes": 400_000, "timeout_sec": 30.0},
}

# Jumlah langkah acak mundur dari goal untuk papan 4x4 dan 5x5.
# Papan 4x4/5x5 yang diacak total hampir selalu terlalu sulit untuk
# diselesaikan oleh solver Python, sehingga kedalaman scramble dibatasi.
DEFAULT_SCRAMBLE_MOVES = {4: 18, 5: 20}
MAX_SCRAMBLE_MOVES = 200


class UnsolvableBoardError(ValueError):
    """Dilemparkan jika konfigurasi papan tidak dapat diselesaikan."""


class SearchLimitError(Exception):
    """Dilemparkan jika pencarian melebihi batas node (memori) atau waktu."""

    def __init__(self, message: str, expanded_nodes: int = 0, elapsed_ms: float = 0.0):
        super().__init__(message)
        self.expanded_nodes = expanded_nodes
        self.elapsed_ms = elapsed_ms


def get_board_size(board_length: int) -> int:
    """Mengubah panjang papan (9/16/25) menjadi ukuran sisi N (3/4/5)."""
    size = isqrt(board_length)
    if size * size != board_length or size not in SUPPORTED_SIZES:
        raise ValueError(
            "Ukuran board tidak didukung. Gunakan 9 (3x3), 16 (4x4), atau 25 (5x5) elemen."
        )
    return size


def get_goal_state(size: int) -> Board:
    """Goal state NxN: [1, 2, ..., N*N-1, 0] (ubin kosong di pojok kanan bawah)."""
    if size not in SUPPORTED_SIZES:
        raise ValueError(f"Ukuran {size}x{size} tidak didukung.")
    total = size * size
    return [idx + 1 if idx < total - 1 else 0 for idx in range(total)]


@lru_cache(maxsize=None)
def get_goal_tuple(size: int) -> StateTuple:
    """Goal state NxN dalam bentuk tuple (di-cache per ukuran)."""
    return tuple(get_goal_state(size))


def validate_board(board: List[int], size: Optional[int] = None) -> Tuple[StateTuple, int]:
    """
    Memastikan bentuk papan valid: list berisi N*N angka unik 0..N*N-1.
    Mengembalikan (state_tuple, ukuran_N).
    """
    if not isinstance(board, list):
        raise ValueError("Board harus berupa list angka.")

    if size is not None:
        if isinstance(size, bool) or not isinstance(size, int):
            raise ValueError("Ukuran papan (size) harus berupa bilangan bulat.")
        if size not in SUPPORTED_SIZES:
            raise ValueError("Ukuran papan harus 3, 4, atau 5.")
        if len(board) != size * size:
            raise ValueError(
                f"Board {size}x{size} harus berisi {size * size} angka, "
                f"tetapi menerima {len(board)} angka."
            )
    else:
        size = get_board_size(len(board))

    for value in board:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Seluruh elemen board harus berupa bilangan bulat.")

    if sorted(board) != list(range(size * size)):
        raise ValueError(f"Board harus berisi angka unik 0 sampai {size * size - 1}.")

    return tuple(board), size


def count_inversions(board: List[int]) -> int:
    """Menghitung jumlah inversi (mengabaikan ubin kosong 0)."""
    tiles = [num for num in board if num != 0]
    inversions = 0
    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            if tiles[i] > tiles[j]:
                inversions += 1
    return inversions


def is_solvable(board: List[int], size: Optional[int] = None) -> bool:
    """
    Cek solvability untuk goal [1, 2, ..., N*N-1, 0].

    - Grid ukuran ganjil (3x3, 5x5): solvable jika dan hanya jika jumlah
      inversi genap.
    - Grid ukuran genap (4x4): hitung baris ubin kosong dari BAWAH (1-based).
      Solvable jika (inversi + baris_kosong_dari_bawah) bernilai ganjil, yaitu:
        * kosong di baris genap dari bawah  -> inversi harus ganjil
        * kosong di baris ganjil dari bawah -> inversi harus genap
    """
    if size is None:
        size = get_board_size(len(board))

    inversions = count_inversions(board)

    if size % 2 == 1:
        return inversions % 2 == 0

    empty_idx = list(board).index(0)
    empty_row_from_top = empty_idx // size
    empty_row_from_bottom = size - empty_row_from_top
    return (inversions + empty_row_from_bottom) % 2 == 1


@lru_cache(maxsize=None)
def _goal_tables(size: int) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    """Tabel baris & kolom goal untuk setiap ubin (indeks = nilai ubin)."""
    total = size * size
    goal_row = [0] * total
    goal_col = [0] * total
    for tile in range(1, total):
        row, col = divmod(tile - 1, size)
        goal_row[tile] = row
        goal_col[tile] = col
    return tuple(goal_row), tuple(goal_col)


@lru_cache(maxsize=None)
def _neighbor_table(size: int) -> Tuple[Tuple[int, ...], ...]:
    """Tabel indeks tetangga (Atas, Bawah, Kiri, Kanan) untuk setiap sel."""
    table = []
    for idx in range(size * size):
        row, col = divmod(idx, size)
        neighbors = []
        if row > 0:
            neighbors.append(idx - size)
        if row < size - 1:
            neighbors.append(idx + size)
        if col > 0:
            neighbors.append(idx - 1)
        if col < size - 1:
            neighbors.append(idx + 1)
        table.append(tuple(neighbors))
    return tuple(table)


def manhattan_distance(state: StateTuple, size: Optional[int] = None) -> int:
    """Total jarak Manhattan seluruh ubin (kecuali kosong) ke posisi goal."""
    if size is None:
        size = get_board_size(len(state))
    goal_row, goal_col = _goal_tables(size)
    distance = 0
    for idx, tile in enumerate(state):
        if tile != 0:
            curr_row, curr_col = divmod(idx, size)
            distance += abs(curr_row - goal_row[tile]) + abs(curr_col - goal_col[tile])
    return distance


def _lis_length(sequence: List[int]) -> int:
    """Panjang Longest Increasing Subsequence (strictly increasing)."""
    if not sequence:
        return 0
    lengths = [1] * len(sequence)
    for i in range(1, len(sequence)):
        for j in range(i):
            if sequence[j] < sequence[i] and lengths[j] + 1 > lengths[i]:
                lengths[i] = lengths[j] + 1
    return max(lengths)


def linear_conflict(state: StateTuple, size: Optional[int] = None) -> int:
    """
    Tambahan penalti Linear Conflict (selalu kelipatan 2).
    Dua ubin berada dalam satu baris/kolom yang sama dengan baris/kolom goal
    masing-masing, tetapi urutannya terbalik, sehingga salah satunya harus
    keluar dari baris/kolom tersebut dan kembali (minimal +2 langkah).
    Jumlah ubin yang harus dikeluarkan per garis = panjang daftar - LIS.
    """
    if size is None:
        size = get_board_size(len(state))
    goal_row, goal_col = _goal_tables(size)
    conflicts = 0

    for row in range(size):
        goal_cols: List[int] = []
        for col in range(size):
            tile = state[row * size + col]
            if tile != 0 and goal_row[tile] == row:
                goal_cols.append(goal_col[tile])
        conflicts += len(goal_cols) - _lis_length(goal_cols)

    for col in range(size):
        goal_rows: List[int] = []
        for row in range(size):
            tile = state[row * size + col]
            if tile != 0 and goal_col[tile] == col:
                goal_rows.append(goal_row[tile])
        conflicts += len(goal_rows) - _lis_length(goal_rows)

    return 2 * conflicts


def heuristic(state: StateTuple, size: Optional[int] = None) -> int:
    """Heuristik h(n) = Manhattan Distance + Linear Conflict (admissible)."""
    if size is None:
        size = get_board_size(len(state))
    return manhattan_distance(state, size) + linear_conflict(state, size)


def get_neighbors(state: StateTuple, size: Optional[int] = None) -> List[StateTuple]:
    """
    Menghasilkan state tetangga yang valid dengan menggeser ubin kosong (0)
    ke Atas, Bawah, Kiri, atau Kanan pada papan NxN.
    """
    if size is None:
        size = get_board_size(len(state))
    empty_idx = state.index(0)
    neighbors: List[StateTuple] = []

    for neighbor_idx in _neighbor_table(size)[empty_idx]:
        state_list = list(state)
        state_list[empty_idx], state_list[neighbor_idx] = (
            state_list[neighbor_idx],
            state_list[empty_idx],
        )
        neighbors.append(tuple(state_list))

    return neighbors


def _reconstruct_path(
    parent_map: Dict[StateTuple, Optional[StateTuple]], goal: StateTuple
) -> List[Board]:
    """Merekonstruksi jalur langkah dari initial state ke goal state."""
    path_tuples: List[StateTuple] = []
    curr: Optional[StateTuple] = goal
    while curr is not None:
        path_tuples.append(curr)
        curr = parent_map[curr]
    path_tuples.reverse()
    return [list(s) for s in path_tuples]


# ==============================================================================
# BAGIAN 2: GENERATOR PAPAN ACAK YANG DIJAMIN SOLVABLE
# ==============================================================================


def generate_random_board(size: int = 3) -> Board:
    """
    Papan hasil permutasi acak penuh yang dijamin solvable.
    Jika hasil acak tidak solvable, dua ubin non-kosong ditukar (satu
    transposisi mengubah paritas inversi) sehingga menjadi solvable.
    """
    if size not in SUPPORTED_SIZES:
        raise ValueError(f"Ukuran {size}x{size} tidak didukung.")

    goal = get_goal_state(size)
    while True:
        board = list(goal)
        random.shuffle(board)

        if not is_solvable(board, size):
            non_empty = [idx for idx, value in enumerate(board) if value != 0]
            a, b = non_empty[0], non_empty[1]
            board[a], board[b] = board[b], board[a]

        if board != goal:
            return board


def generate_scrambled_board(size: int, scramble_moves: int) -> Board:
    """
    Papan hasil langkah acak legal mundur dari goal state.
    Dijamin solvable karena setiap langkah adalah gerakan yang sah, dan
    kedalaman solusi optimal tidak melebihi scramble_moves.
    """
    if size not in SUPPORTED_SIZES:
        raise ValueError(f"Ukuran {size}x{size} tidak didukung.")
    if isinstance(scramble_moves, bool) or not isinstance(scramble_moves, int):
        raise ValueError("Jumlah langkah acak harus berupa bilangan bulat.")
    if scramble_moves < 1 or scramble_moves > MAX_SCRAMBLE_MOVES:
        raise ValueError(f"Jumlah langkah acak harus antara 1 dan {MAX_SCRAMBLE_MOVES}.")

    goal = get_goal_state(size)
    neighbor_table = _neighbor_table(size)

    while True:
        board = list(goal)
        empty_idx = board.index(0)
        prev_empty_idx = -1

        for _ in range(scramble_moves):
            candidates = [idx for idx in neighbor_table[empty_idx] if idx != prev_empty_idx]
            chosen_idx = random.choice(candidates)
            board[empty_idx], board[chosen_idx] = board[chosen_idx], board[empty_idx]
            prev_empty_idx = empty_idx
            empty_idx = chosen_idx

        if board != goal:
            return board


def generate_solvable_board(size: int = 3, scramble_moves: Optional[int] = None) -> Board:
    """
    Generator utama papan solvable.
    - 3x3 tanpa scramble_moves : permutasi acak penuh (dengan koreksi paritas).
    - 4x4 / 5x5 tanpa scramble_moves : langkah acak mundur dari goal dengan
      kedalaman default agar solver masih sanggup menyelesaikannya.
    - scramble_moves diberikan : langkah acak mundur sebanyak nilai tersebut.
    """
    if size not in SUPPORTED_SIZES:
        raise ValueError(f"Ukuran {size}x{size} tidak didukung.")

    if scramble_moves is None:
        if size == 3:
            return generate_random_board(3)
        scramble_moves = DEFAULT_SCRAMBLE_MOVES[size]

    return generate_scrambled_board(size, scramble_moves)


# ==============================================================================
# BAGIAN 3: HELPER HASIL & BATAS PENCARIAN
# ==============================================================================


def _prepare(initial_board: Board, size: Optional[int]) -> Tuple[StateTuple, int, StateTuple]:
    """Validasi papan, cek solvability, dan kembalikan (start, size, goal)."""
    start_tuple, board_size = validate_board(initial_board, size)

    if not is_solvable(list(start_tuple), board_size):
        raise UnsolvableBoardError(
            "Konfigurasi papan tidak dapat diselesaikan (unsolvable)."
        )

    return start_tuple, board_size, get_goal_tuple(board_size)


def _elapsed_ms(start_time: float) -> float:
    return round((time.perf_counter() - start_time) * 1000, 2)


def _build_result(
    steps: List[Board], expanded_nodes: int, start_time: float, size: int
) -> Dict[str, object]:
    """Membentuk dictionary hasil sesuai kontrak REST API."""
    return {
        "steps": steps,
        "size": size,
        "metrics": {
            "expandedNodes": expanded_nodes,
            "executionTimeMs": _elapsed_ms(start_time),
            "pathCost": len(steps) - 1,
        },
    }


def _raise_node_limit(
    algorithm: str, expanded_nodes: int, stored_nodes: int, start_time: float
) -> None:
    limits = SEARCH_LIMITS[algorithm]
    elapsed = _elapsed_ms(start_time)
    raise SearchLimitError(
        f"Pencarian {algorithm} dihentikan: memori melebihi batas "
        f"({stored_nodes:,} state tersimpan, batas {int(limits['max_nodes']):,}) "
        f"setelah {expanded_nodes:,} node diekspansi dalam {elapsed / 1000:.1f} detik. "
        f"Coba papan yang lebih mudah (Acak Papan lagi), ukuran grid yang lebih kecil, "
        f"atau gunakan algoritma A* / Greedy Best-First Search.",
        expanded_nodes=expanded_nodes,
        elapsed_ms=elapsed,
    )


def _raise_timeout(algorithm: str, expanded_nodes: int, start_time: float) -> None:
    limits = SEARCH_LIMITS[algorithm]
    elapsed = _elapsed_ms(start_time)
    raise SearchLimitError(
        f"Pencarian {algorithm} dihentikan: waktu melebihi batas "
        f"{limits['timeout_sec']:.0f} detik setelah {expanded_nodes:,} node diekspansi. "
        f"Coba papan yang lebih mudah (Acak Papan lagi), ukuran grid yang lebih kecil, "
        f"atau gunakan algoritma A* / Greedy Best-First Search.",
        expanded_nodes=expanded_nodes,
        elapsed_ms=elapsed,
    )


# ==============================================================================
# BAGIAN 4: ALGORITMA BREADTH-FIRST SEARCH (BFS)
# ==============================================================================


def solve_bfs(initial_board: Board, size: Optional[int] = None) -> Dict[str, object]:
    """
    Menyelesaikan puzzle NxN menggunakan Breadth-First Search (BFS).
    Dilengkapi batas jumlah state tersimpan dan timeout agar server aman.
    Mengembalikan dictionary sesuai kontrak REST API:
    {
        "steps": [...],
        "size": int,
        "metrics": {
            "expandedNodes": int,
            "executionTimeMs": float,
            "pathCost": int
        }
    }
    """
    start_tuple, board_size, goal_tuple = _prepare(initial_board, size)
    limits = SEARCH_LIMITS["BFS"]
    max_nodes = int(limits["max_nodes"])
    timeout_sec = float(limits["timeout_sec"])

    start_time = time.perf_counter()

    if start_tuple == goal_tuple:
        return _build_result([list(start_tuple)], 0, start_time, board_size)

    queue: deque = deque([start_tuple])
    visited: set = {start_tuple}
    parent: Dict[StateTuple, Optional[StateTuple]] = {start_tuple: None}
    expanded_nodes = 0

    while queue:
        current = queue.popleft()
        expanded_nodes += 1

        if current == goal_tuple:
            steps = _reconstruct_path(parent, current)
            return _build_result(steps, expanded_nodes, start_time, board_size)

        if len(visited) > max_nodes:
            _raise_node_limit("BFS", expanded_nodes, len(visited), start_time)

        if (expanded_nodes & 1023) == 0 and (
            time.perf_counter() - start_time
        ) > timeout_sec:
            _raise_timeout("BFS", expanded_nodes, start_time)

        for next_state in get_neighbors(current, board_size):
            if next_state not in visited:
                visited.add(next_state)
                parent[next_state] = current
                queue.append(next_state)

    raise UnsolvableBoardError(
        "Konfigurasi papan tidak dapat diselesaikan (unsolvable)."
    )


# ==============================================================================
# BAGIAN 5: ALGORITMA GREEDY BEST-FIRST SEARCH (GBFS)
# ==============================================================================


def solve_gbfs(initial_board: Board, size: Optional[int] = None) -> Dict[str, object]:
    """
    Menyelesaikan puzzle NxN menggunakan Greedy Best-First Search (GBFS).
    Fungsi evaluasi f(n) = h(n), dengan h(n) = Manhattan Distance + Linear Conflict.
    Priority queue: heapq dengan tuple (h_score, tie_breaker, state).
    """
    start_tuple, board_size, goal_tuple = _prepare(initial_board, size)
    limits = SEARCH_LIMITS["GBFS"]
    max_nodes = int(limits["max_nodes"])
    timeout_sec = float(limits["timeout_sec"])

    start_time = time.perf_counter()

    if start_tuple == goal_tuple:
        return _build_result([list(start_tuple)], 0, start_time, board_size)

    # Counter sebagai tie-breaker agar heapq tidak membandingkan state
    counter = itertools.count()
    heap: List[Tuple[int, int, StateTuple]] = [
        (heuristic(start_tuple, board_size), next(counter), start_tuple)
    ]
    visited: set = {start_tuple}
    parent: Dict[StateTuple, Optional[StateTuple]] = {start_tuple: None}
    expanded_nodes = 0

    while heap:
        _, _, current = heapq.heappop(heap)
        expanded_nodes += 1  # dihitung setiap node di-pop (sama seperti BFS)

        if current == goal_tuple:
            steps = _reconstruct_path(parent, current)
            return _build_result(steps, expanded_nodes, start_time, board_size)

        if len(visited) > max_nodes:
            _raise_node_limit("GBFS", expanded_nodes, len(visited), start_time)

        if (expanded_nodes & 1023) == 0 and (
            time.perf_counter() - start_time
        ) > timeout_sec:
            _raise_timeout("GBFS", expanded_nodes, start_time)

        for next_state in get_neighbors(current, board_size):
            if next_state not in visited:
                visited.add(next_state)
                parent[next_state] = current
                heapq.heappush(
                    heap,
                    (heuristic(next_state, board_size), next(counter), next_state),
                )

    raise UnsolvableBoardError(
        "Konfigurasi papan tidak dapat diselesaikan (unsolvable)."
    )


# ==============================================================================
# BAGIAN 6: ALGORITMA A* (A-STAR)
# ==============================================================================


def solve_astar(initial_board: Board, size: Optional[int] = None) -> Dict[str, object]:
    """
    Menyelesaikan puzzle NxN menggunakan A* Search.
    Fungsi evaluasi f(n) = g(n) + h(n), dengan h(n) = Manhattan Distance + Linear Conflict.
    Priority queue: heapq dengan tuple (f_score, tie_breaker, g_score, state).
    Heuristik bersifat admissible sehingga solusi yang dihasilkan optimal
    (path cost sama dengan BFS). Closed list menggunakan set; sebuah state
    dikeluarkan kembali dari closed list jika ditemukan jalur yang lebih murah.
    """
    start_tuple, board_size, goal_tuple = _prepare(initial_board, size)
    limits = SEARCH_LIMITS["ASTAR"]
    max_nodes = int(limits["max_nodes"])
    timeout_sec = float(limits["timeout_sec"])

    start_time = time.perf_counter()

    if start_tuple == goal_tuple:
        return _build_result([list(start_tuple)], 0, start_time, board_size)

    # Counter sebagai tie-breaker agar heapq tidak membandingkan state
    counter = itertools.count()
    start_h = heuristic(start_tuple, board_size)
    heap: List[Tuple[int, int, int, StateTuple]] = [
        (start_h, next(counter), 0, start_tuple)  # (f, tie_breaker, g, state)
    ]
    best_g: Dict[StateTuple, int] = {start_tuple: 0}
    parent: Dict[StateTuple, Optional[StateTuple]] = {start_tuple: None}
    closed: set = set()
    expanded_nodes = 0

    while heap:
        _, _, g, current = heapq.heappop(heap)

        # Lewati entri usang (state ini sudah ditemukan lewat jalur lebih murah)
        if g > best_g[current] or current in closed:
            continue

        closed.add(current)
        expanded_nodes += 1  # dihitung setiap node di-pop untuk diekspansi

        if current == goal_tuple:
            steps = _reconstruct_path(parent, current)
            return _build_result(steps, expanded_nodes, start_time, board_size)

        if len(best_g) > max_nodes:
            _raise_node_limit("ASTAR", expanded_nodes, len(best_g), start_time)

        if (expanded_nodes & 1023) == 0 and (
            time.perf_counter() - start_time
        ) > timeout_sec:
            _raise_timeout("ASTAR", expanded_nodes, start_time)

        for next_state in get_neighbors(current, board_size):
            new_g = g + 1  # step cost selalu 1
            if next_state not in best_g or new_g < best_g[next_state]:
                best_g[next_state] = new_g
                parent[next_state] = current
                closed.discard(next_state)
                f_score = new_g + heuristic(next_state, board_size)
                heapq.heappush(
                    heap, (f_score, next(counter), new_g, next_state)
                )

    raise UnsolvableBoardError(
        "Konfigurasi papan tidak dapat diselesaikan (unsolvable)."
    )


# ==============================================================================
# BAGIAN 7: DISPATCHER UTAMA (PINTU MASUK UNTUK REST API app.py)
# ==============================================================================


def solve_puzzle(
    algorithm: str, board: Board, size: Optional[int] = None
) -> Dict[str, object]:
    """Menghubungkan request dari app.py ke fungsi solver yang dipilih."""
    if not isinstance(algorithm, str):
        raise ValueError("Algoritma harus berupa string.")

    algo = algorithm.upper()
    if algo == "BFS":
        return solve_bfs(board, size)
    elif algo == "GBFS":
        return solve_gbfs(board, size)
    elif algo == "ASTAR":
        return solve_astar(board, size)
    raise ValueError(f"Algoritma '{algorithm}' tidak dikenal.")