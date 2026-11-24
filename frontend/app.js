/**
 * FRONTEND STATE & UI CONTROLLER - SLIDING PUZZLE AI SOLVER (3x3, 4x4, 5x5)
 * Siap terhubung dengan REST API backend (BFS, GBFS, A*).
 */

const DEFAULT_INITIAL_BOARDS = {
  3: [1, 2, 3, 5, 0, 6, 4, 7, 8],
  4: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0, 12, 13, 14, 11, 15],
  5: [
    1, 2, 3, 4, 5,
    6, 7, 8, 9, 10,
    11, 12, 13, 14, 15,
    16, 17, 18, 0, 20,
    21, 22, 23, 24, 19,
  ],
};

let gridSize = 3; // 3 = 8-Puzzle, 4 = 15-Puzzle, 5 = 24-Puzzle
let initialState = [...DEFAULT_INITIAL_BOARDS[3]];
let currentState = [...initialState];
let manualSteps = 0;

// State untuk animasi solusi dari backend
let solutionSteps = [];
let currentStepIndex = 0;
let playInterval = null;
let playbackSpeed = 1.0;

// DOM Elements
const gridEl = document.getElementById("puzzle-grid");
const boardTitleEl = document.getElementById("board-title");
const benchmarkTitleEl = document.getElementById("benchmark-title");
const goalHintEl = document.getElementById("goal-hint-text");
const statusBadge = document.getElementById("status-badge");
const manualStepsEl = document.getElementById("manual-steps");
const stepCounterEl = document.getElementById("step-counter");
const speedSlider = document.getElementById("speed-slider");
const speedValueEl = document.getElementById("speed-value");
const sizeButtons = document.querySelectorAll(".size-btn");

function getGoalState(size = gridSize) {
  const total = size * size;
  return Array.from({ length: total }, (_, idx) => (idx === total - 1 ? 0 : idx + 1));
}

function getTileColorClass(value) {
  // Pertahankan pola warna 3x3 asli (1,6 indigo; 2,4,7 blue; 3,5,8 slate) & siklus konsisten untuk 9..24
  const indigoTiles = new Set([1, 6, 9, 11, 14, 16, 19, 21, 24]);
  const blueTiles = new Set([2, 4, 7, 10, 12, 15, 17, 20, 22]);
  if (indigoTiles.has(value)) return "tile-indigo";
  if (blueTiles.has(value)) return "tile-blue";
  return "tile-slate";
}

/**
 * Render papan NxN ke DOM
 */
function renderBoard(state) {
  gridEl.className = `puzzle-grid grid-${gridSize}`;
  gridEl.innerHTML = "";

  state.forEach((value, index) => {
    const tile = document.createElement("div");
    tile.className =
      value === 0 ? "tile tile-empty" : `tile ${getTileColorClass(value)}`;
    tile.textContent = value === 0 ? "" : value;
    tile.addEventListener("click", () => handleManualMove(index));
    gridEl.appendChild(tile);
  });

  if (isGoalState(state)) {
    setStatus("Solved!", "badge-solved");
  }
}

function isGoalState(state) {
  const goal = getGoalState(gridSize);
  return state.length === goal.length && state.every((val, idx) => val === goal[idx]);
}

function setStatus(text, badgeClass) {
  statusBadge.textContent = text;
  statusBadge.className = `badge ${badgeClass}`;
}

/**
 * Geser ubin secara manual jika bersebelahan dengan ubin kosong (0)
 */
function handleManualMove(tileIndex) {
  if (playInterval) return;

  const emptyIndex = currentState.indexOf(0);
  const validNeighbors = getNeighbors(emptyIndex, gridSize);

  if (validNeighbors.includes(tileIndex)) {
    [currentState[emptyIndex], currentState[tileIndex]] = [
      currentState[tileIndex],
      currentState[emptyIndex],
    ];
    manualSteps++;
    manualStepsEl.textContent = manualSteps;
    setStatus("Manual Mode", "badge-ready");
    renderBoard(currentState);
  }
}

function getNeighbors(index, size = gridSize) {
  const row = Math.floor(index / size);
  const col = index % size;
  const neighbors = [];

  if (row > 0) neighbors.push(index - size);        // Atas
  if (row < size - 1) neighbors.push(index + size); // Bawah
  if (col > 0) neighbors.push(index - 1);           // Kiri
  if (col < size - 1) neighbors.push(index + 1);    // Kanan
  return neighbors;
}

/**
 * Generator papan acak yang dijamin 100% solvable untuk 3x3, 4x4, dan 5x5
 */
function generateSolvableBoard() {
  if (gridSize === 3) {
    let arr;
    do {
      arr = [...getGoalState(3)];
      for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
      }
    } while (!isSolvable(arr, 3) || isGoalState(arr));
    return arr;
  }

  // Untuk 4x4 & 5x5: acak dengan langkah mundur legal dari Goal State
  // Dijamin 100% solvable & menjaga kedalaman langkah tetap realistis untuk demo AI
  const shuffleMoves = gridSize === 4 ? 18 : 20;
  const arr = [...getGoalState(gridSize)];
  let emptyIdx = arr.indexOf(0);
  let prevEmptyIdx = -1;

  for (let step = 0; step < shuffleMoves; step++) {
    const candidates = getNeighbors(emptyIdx, gridSize).filter(
      (idx) => idx !== prevEmptyIdx
    );
    const chosenIdx = candidates[Math.floor(Math.random() * candidates.length)];
    [arr[emptyIdx], arr[chosenIdx]] = [arr[chosenIdx], arr[emptyIdx]];
    prevEmptyIdx = emptyIdx;
    emptyIdx = chosenIdx;
  }

  return arr;
}

function isSolvable(board, size = gridSize) {
  let inversions = 0;
  const filtered = board.filter((num) => num !== 0);
  for (let i = 0; i < filtered.length; i++) {
    for (let j = i + 1; j < filtered.length; j++) {
      if (filtered[i] > filtered[j]) inversions++;
    }
  }

  if (size % 2 === 1) {
    return inversions % 2 === 0;
  }

  const emptyIdx = board.indexOf(0);
  const emptyRowFromTop = Math.floor(emptyIdx / size);
  const emptyRowFromBottom = size - emptyRowFromTop;
  return (inversions + emptyRowFromBottom) % 2 === 1;
}

/**
 * Ganti ukuran papan (3x3, 4x4, 5x5) dan reset konteks dashboard
 */
function switchGridSize(newSize) {
  if (newSize === gridSize) return;
  pauseAnimation();

  gridSize = newSize;
  sizeButtons.forEach((btn) => {
    btn.classList.toggle("active", Number(btn.dataset.size) === gridSize);
  });

  boardTitleEl.textContent = `Papan Permainan (${gridSize}x${gridSize} Sliding Puzzle)`;
  benchmarkTitleEl.textContent = `Perbandingan Kinerja (Grid ${gridSize}x${gridSize})`;

  if (gridSize === 3) {
    goalHintEl.textContent = "[1 2 3 | 4 5 6 | 7 8 _]";
  } else {
    const maxTile = gridSize * gridSize - 1;
    goalHintEl.textContent = `1–${maxTile} (_ pojok kanan bawah)`;
  }

  clearBenchmarkTable();
  initialState = [...DEFAULT_INITIAL_BOARDS[gridSize]];
  currentState = [...initialState];
  manualSteps = 0;
  solutionSteps = [];
  currentStepIndex = 0;
  manualStepsEl.textContent = "0";
  updateStepCounter();
  setStatus("Ready", "badge-ready");
  renderBoard(currentState);
}

function clearBenchmarkTable() {
  ["BFS", "GBFS", "ASTAR"].forEach((algo) => {
    const row = document.getElementById(`row-${algo}`);
    row.querySelector(".col-nodes").textContent = "-";
    row.querySelector(".col-time").textContent = "-";
    row.querySelector(".col-cost").textContent = "-";
  });
}

/**
 * =========================================================================
 * BACKEND INTEGRATION BRIDGE (Hubungkan fungsi solver BFS/GBFS/A* di sini)
 * =========================================================================
 */
const SolverBridge = {
  async solve(algorithm, startBoard) {
    try {
      const response = await fetch("http://127.0.0.1:5000/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          algorithm: algorithm,
          board: startBoard,
          size: gridSize,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Gagal memproses solusi di server.");
      }
      return data;
    } catch (err) {
      alert(`Error: ${err.message}\n\nPastikan server Python (app.py) sudah dijalankan!`);
      setStatus("Error", "badge-error");
      throw err;
    }
  },

  applySolution(algorithm, result) {
    const row = document.getElementById(`row-${algorithm}`);
    if (row && result.metrics) {
      row.querySelector(".col-nodes").textContent =
        result.metrics.expandedNodes.toLocaleString("id-ID");
      row.querySelector(".col-time").textContent = result.metrics.executionTimeMs;
      row.querySelector(".col-cost").textContent = result.metrics.pathCost;
    }

    solutionSteps = result.steps || [];
    currentStepIndex = 0;
    updateStepCounter();
    if (solutionSteps.length > 0) {
      playAnimation();
    }
  },
};

/**
 * KONTROL PLAYBACK ANIMASI
 */
function updateStepCounter() {
  const total = Math.max(0, solutionSteps.length - 1);
  stepCounterEl.textContent = `${currentStepIndex} / ${total}`;
}

function playAnimation() {
  if (solutionSteps.length === 0) return;
  pauseAnimation();
  setStatus("Animating...", "badge-solving");

  const delay = 600 / playbackSpeed;
  playInterval = setInterval(() => {
    if (currentStepIndex < solutionSteps.length - 1) {
      currentStepIndex++;
      currentState = [...solutionSteps[currentStepIndex]];
      renderBoard(currentState);
      updateStepCounter();
    } else {
      pauseAnimation();
      setStatus("Selesai", "badge-solved");
    }
  }, delay);
}

function pauseAnimation() {
  if (playInterval) {
    clearInterval(playInterval);
    playInterval = null;
  }
}

// EVENT LISTENERS
sizeButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    switchGridSize(Number(btn.dataset.size));
  });
});

document.getElementById("btn-shuffle").addEventListener("click", () => {
  pauseAnimation();
  initialState = generateSolvableBoard();
  currentState = [...initialState];
  manualSteps = 0;
  solutionSteps = [];
  currentStepIndex = 0;
  manualStepsEl.textContent = "0";
  updateStepCounter();
  setStatus("Ready", "badge-ready");
  renderBoard(currentState);
});

document.getElementById("btn-reset").addEventListener("click", () => {
  pauseAnimation();
  currentState = [...initialState];
  manualSteps = 0;
  currentStepIndex = 0;
  manualStepsEl.textContent = "0";
  updateStepCounter();
  setStatus("Ready", "badge-ready");
  renderBoard(currentState);
});

document.getElementById("btn-solve").addEventListener("click", async () => {
  pauseAnimation();
  const selectedAlgo = document.querySelector('input[name="algorithm"]:checked').value;
  setStatus(`Running ${selectedAlgo}...`, "badge-solving");

  const result = await SolverBridge.solve(selectedAlgo, [...currentState]);
  SolverBridge.applySolution(selectedAlgo, result);
});

document.getElementById("btn-play").addEventListener("click", playAnimation);
document.getElementById("btn-pause").addEventListener("click", pauseAnimation);

document.getElementById("btn-prev").addEventListener("click", () => {
  pauseAnimation();
  if (currentStepIndex > 0) {
    currentStepIndex--;
    currentState = [...solutionSteps[currentStepIndex]];
    renderBoard(currentState);
    updateStepCounter();
  }
});

document.getElementById("btn-next").addEventListener("click", () => {
  pauseAnimation();
  if (currentStepIndex < solutionSteps.length - 1) {
    currentStepIndex++;
    currentState = [...solutionSteps[currentStepIndex]];
    renderBoard(currentState);
    updateStepCounter();
  }
});

speedSlider.addEventListener("input", (e) => {
  playbackSpeed = parseFloat(e.target.value);
  speedValueEl.textContent = `${playbackSpeed.toFixed(1)}x`;
  if (playInterval) playAnimation();
});

document.getElementById("btn-clear-table").addEventListener("click", clearBenchmarkTable);

// Inisialisasi awal saat halaman dibuka
renderBoard(currentState);