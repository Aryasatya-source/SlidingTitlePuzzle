from collections import deque
import heapq
import itertools
import time
from typing import Dict, List, Optional, Tuple

Board = List[int]
StateTuple = Tuple[int, ...] #isinya int, jumlahnya gabisa ditentuin

GOAL_STATE: Board = [1, 2, 3, 4, 5, 6, 7, 8, 0]
GOAL_TUPLE: StateTuple = tuple(GOAL_STATE)


class UnsolvableBoardError(ValueError):
    """Dilemparkan jika konfigurasi papan 8-puzzle tidak dapat diselesaikan."""


def validate_board(board: List[int]) -> StateTuple:
    """Memastikan bentuk papan valid (9 elemen unik 0..8)."""
    if not isinstance(board, list) or len(board) != 9:
        raise ValueError("Board harus berupa list berisi 9 angka.")
    if sorted(board) != list(range(9)):
        raise ValueError("Board harus berisi angka unik 0 sampai 8.")
    return tuple(board)


def count_inversions(board: List[int]) -> int:
    """Menghitung jumlah inversi (mengabaikan ubin kosong 0)."""
    tiles = [num for num in board if num != 0]
    inversions = 0
    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            if tiles[i] > tiles[j]:
                inversions += 1
    return inversions


def is_solvable(board: List[int]) -> bool:
    """
    Untuk grid 3x3 dengan goal [1, 2, 3, 4, 5, 6, 7, 8, 0],
    papan solvable jika dan hanya jika jumlah inversi genap.
    """
    return count_inversions(board) % 2 == 0


def get_neighbors(state: StateTuple) -> List[StateTuple]:
    """
    Menghasilkan state tetangga yang valid dengan menggeser ubin kosong (0)
    ke Atas, Bawah, Kiri, atau Kanan.
    """
    empty_idx = state.index(0)
    row, col = divmod(empty_idx, 3)
    neighbors: List[StateTuple] = []

    # (delta_row, delta_col) -> Atas, Bawah, Kiri, Kanan
    moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for d_row, d_col in moves:
        n_row, n_col = row + d_row, col + d_col
        if 0 <= n_row < 3 and 0 <= n_col < 3:
            neighbor_idx = n_row * 3 + n_col
            state_list = list(state)
            state_list[empty_idx], state_list[neighbor_idx] = (
                state_list[neighbor_idx],
                state_list[empty_idx],
            )
            neighbors.append(tuple(state_list))

    return neighbors


def _reconstruct_path(
    parent_map: Dict[StateTuple, StateTuple | None], goal: StateTuple
) -> List[Board]:
    """Merekonstruksi jalur langkah dari initial state ke goal state."""
    path_tuples: List[StateTuple] = []
    curr: StateTuple | None = goal
    while curr is not None:
        path_tuples.append(curr)
        curr = parent_map[curr]
    path_tuples.reverse()
    return [list(s) for s in path_tuples]


def solve_bfs(initial_board: Board) -> Dict[str, object]:
    """
    Menyelesaikan 8-Puzzle menggunakan Breadth-First Search (BFS).
    Mengembalikan dictionary sesuai kontrak REST API:
    {
        "steps": [...],
        "metrics": {
            "expandedNodes": int,
            "executionTimeMs": float,
            "pathCost": int
        }
    }
    """
    start_tuple = validate_board(initial_board)

    if not is_solvable(list(start_tuple)):
        raise UnsolvableBoardError(
            "Konfigurasi papan tidak dapat diselesaikan (unsolvable)."
        )

    start_time = time.perf_counter()

    if start_tuple == GOAL_TUPLE:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "steps": [list(start_tuple)],
            "metrics": {
                "expandedNodes": 0,
                "executionTimeMs": elapsed_ms,
                "pathCost": 0,
            },
        }

    queue: deque[StateTuple] = deque([start_tuple])
    visited: set[StateTuple] = {start_tuple}
    parent: Dict[StateTuple, StateTuple | None] = {start_tuple: None}
    expanded_nodes = 0

    while queue:
        current = queue.popleft()
        expanded_nodes += 1

        if current == GOAL_TUPLE:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            steps = _reconstruct_path(parent, current)
            return {
                "steps": steps,
                "metrics": {
                    "expandedNodes": expanded_nodes,
                    "executionTimeMs": elapsed_ms,
                    "pathCost": len(steps) - 1,
                },
            }

        for next_state in get_neighbors(current):
            if next_state not in visited:
                visited.add(next_state)
                parent[next_state] = current
                queue.append(next_state)

    raise UnsolvableBoardError(
        "Konfigurasi papan tidak dapat diselesaikan (unsolvable)."
    )
def manhattan_distance(state: StateTuple) -> int:
    """Total jarak Manhattan ubin 1..8 ke posisi goal (heuristik h(n))."""
    distance = 0
    for idx, tile in enumerate(state):
        if tile != 0:
            curr_row, curr_col = divmod(idx, 3)
            goal_row, goal_col = divmod(tile - 1, 3)
            distance += abs(curr_row - goal_row) + abs(curr_col - goal_col)
    return distance

def solve_gbfs(initial_board: Board) -> Dict[str, object]:
    """
    Menyelesaikan 8-Puzzle menggunakan Greedy Best-First Search (GBFS).
    Fungsi evaluasi f(n) = h(n), dengan h(n) = Manhattan Distance.
    Priority queue: heapq dengan tuple (h_score, tie_breaker, state).
    """
    start_tuple = validate_board(initial_board)

    if not is_solvable(list(start_tuple)):
        raise UnsolvableBoardError(
            "Konfigurasi papan tidak dapat diselesaikan (unsolvable)."
        )

    start_time = time.perf_counter()

    if start_tuple == GOAL_TUPLE:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "steps": [list(start_tuple)],
            "metrics": {
                "expandedNodes": 0,
                "executionTimeMs": elapsed_ms,
                "pathCost": 0,
            },
        }

    # Counter sebagai tie-breaker agar heapq tidak membandingkan state
    counter = itertools.count()
    heap: List[Tuple[int, int, StateTuple]] = [
        (manhattan_distance(start_tuple), next(counter), start_tuple)
    ]
    visited: set[StateTuple] = {start_tuple}
    parent: Dict[StateTuple, Optional[StateTuple]] = {start_tuple: None}
    expanded_nodes = 0

    while heap:
        _, _, current = heapq.heappop(heap)
        expanded_nodes += 1  # dihitung setiap node di-pop (sama seperti BFS)

        if current == GOAL_TUPLE:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            steps = _reconstruct_path(parent, current)
            return {
                "steps": steps,
                "metrics": {
                    "expandedNodes": expanded_nodes,
                    "executionTimeMs": elapsed_ms,
                    "pathCost": len(steps) - 1,
                },
            }

        for next_state in get_neighbors(current):
            if next_state not in visited:
                visited.add(next_state)
                parent[next_state] = current
                heapq.heappush(
                    heap,
                    (manhattan_distance(next_state), next(counter), next_state),
                )

    raise UnsolvableBoardError(
        "Konfigurasi papan tidak dapat diselesaikan (unsolvable)."
    )

def solve_astar(initial_board: Board) -> Dict[str, object]:
    raise ValueError("Algoritma A* Search belum diimplementasikan.")

def solve_puzzle(algorithm: str, board: Board) -> Dict[str, object]:
    """Menghubungkan request dari app.py ke fungsi solver yang dipilih."""
    algo = algorithm.upper()
    if algo == "BFS":
        return solve_bfs(board)
    elif algo == "GBFS":
        return solve_gbfs(board)
    elif algo == "ASTAR":
        return solve_astar(board)
    raise ValueError(f"Algoritma '{algorithm}' tidak dikenal.")

#testing
if __name__ == "__main__":
    sample_board = [1, 2, 3, 5, 0, 6, 4, 7, 8]
    result = solve_bfs(sample_board)
    print("Path Cost:", result["metrics"]["pathCost"])
    print("Expanded Nodes:", result["metrics"]["expandedNodes"])
    print("Execution Time (ms):", result["metrics"]["executionTimeMs"])
    print("Total Steps (termasuk initial):", len(result["steps"]))
    for idx, step in enumerate(result["steps"]):
        print(f"Step {idx}: {step}")