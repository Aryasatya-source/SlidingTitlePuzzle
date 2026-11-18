/**
 * FRONTEND STATE & UI CONTROLLER - 8-PUZZLE AI SOLVER
 * Siap diintegrasikan dengan modul backend (BFS, GBFS, A*).
 */

const GOAL_STATE = [1, 2, 3, 4, 5, 6, 7, 8, 0]; // 0 = ubin kosong

let initialState = [1, 2, 3, 5, 0, 6, 4, 7, 8];
let currentState = [...initialState];
let manualSteps = 0;

// State untuk animasi solusi dari backend
let solutionSteps = []; // Array of board states: [[...], [...], ...]
let currentStepIndex = 0;
let playInterval = null;
let playbackSpeed = 1.0;

// DOM Elements
const gridEl = document.getElementById("puzzle-grid");
const statusBadge = document.getElementById("status-badge");
const manualStepsEl = document.getElementById("manual-steps");
const stepCounterEl = document.getElementById("step-counter");
const speedSlider = document.getElementById("speed-slider");
const speedValueEl = document.getElementById("speed-value");

/**
 * Render papan 3x3 ke DOM
 */
function renderBoard(state) {
  gridEl.innerHTML = "";
  state.forEach((value, index) => {
    const tile = document.createElement("div");
    tile.className = value === 0 ? "tile tile-empty" : `tile tile-${value}`;
    tile.textContent = value === 0 ? "" : value;
    tile.addEventListener("click", () => handleManualMove(index));
    gridEl.appendChild(tile);
  });

  if (isGoalState(state)) {
    setStatus("Solved!", "badge-solved");
  }
}

function isGoalState(state) {
  return state.every((val, idx) => val === GOAL_STATE[idx]);
}

function setStatus(text, badgeClass) {
  statusBadge.textContent = text;
  statusBadge.className = `badge ${badgeClass}`;
}

/**
 * Geser ubin secara manual jika bersebelahan dengan ubin kosong (0)
 */
function handleManualMove(tileIndex) {
  if (playInterval) return; // Kunci saat animasi AI berjalan

  const emptyIndex = currentState.indexOf(0);
  const validNeighbors = getNeighbors(emptyIndex);

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

function getNeighbors(index) {
  const row = Math.floor(index / 3);
  const col = index % 3;
  const neighbors = [];

  if (row > 0) neighbors.push(index - 3); // Atas
  if (row < 2) neighbors.push(index + 3); // Bawah
  if (col > 0) neighbors.push(index - 1); // Kiri
  if (col < 2) neighbors.push(index + 1); // Kanan
  return neighbors;
}

/**
 * Generator papan acak yang dijamin solvable (jumlah inversi genap)
 */
function generateSolvableBoard() {
  let arr;
  do {
    arr = [...GOAL_STATE];
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
  } while (!isSolvable(arr) || isGoalState(arr));
  return arr;
}

function isSolvable(board) {
  let inversions = 0;
  const filtered = board.filter((num) => num !== 0);
  for (let i = 0; i < filtered.length; i++) {
    for (let j = i + 1; j < filtered.length; j++) {
      if (filtered[i] > filtered[j]) inversions++;
    }
  }
  return inversions % 2 === 0;
}

/**
 * =========================================================================
 * BACKEND INTEGRATION BRIDGE (Hubungkan fungsi solver BFS/GBFS/A* di sini)
 * =========================================================================
 */
const SolverBridge = {
  /**
   * Dipanggil saat tombol "Selesaikan" ditekan.
   * Nanti ganti isi fungsi ini dengan pemanggilan algoritma backend (JS atau API Python).
   */
  async solve(algorithm, startBoard) {
    console.log(`[Frontend -> Backend] Request solve: ${algorithm}`, startBoard);

    // --- MOCK RESPONSE SEMENTARA (Hapus setelah backend siap) ---
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          steps: [
            [...startBoard],
            [1, 2, 3, 5, 7, 6, 4, 0, 8],
            [1, 2, 3, 5, 7, 6, 4, 8, 0],
          ],
          metrics: {
            expandedNodes: algorithm === "BFS" ? 24103 : algorithm === "GBFS" ? 112 : 840,
            executionTimeMs: algorithm === "BFS" ? 350 : algorithm === "GBFS" ? 2 : 18,
            pathCost: algorithm === "GBFS" ? 48 : 22,
          },
        });
      }, 300);
    });
  },

  /**
   * Menerima hasil dari backend untuk diperbarui ke tabel dan dijalankan animasinya
   */
  applySolution(algorithm, result) {
    // 1. Update Tabel Perbandingan
    const row = document.getElementById(`row-${algorithm}`);
    if (row && result.metrics) {
      row.querySelector(".col-nodes").textContent =
        result.metrics.expandedNodes.toLocaleString("id-ID");
      row.querySelector(".col-time").textContent = result.metrics.executionTimeMs;
      row.querySelector(".col-cost").textContent = result.metrics.pathCost;
    }

    // 2. Siapkan Animasi Langkah
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

document.getElementById("btn-clear-table").addEventListener("click", () => {
  ["BFS", "GBFS", "ASTAR"].forEach((algo) => {
    const row = document.getElementById(`row-${algo}`);
    row.querySelector(".col-nodes").textContent = "-";
    row.querySelector(".col-time").textContent = "-";
    row.querySelector(".col-cost").textContent = "-";
  });
});

// Inisialisasi awal saat halaman dibuka
renderBoard(currentState);