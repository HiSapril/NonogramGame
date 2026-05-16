/**
 * script.js — Nonogram Game
 *
 * Architecture
 * ────────────
 * renderBoard(rowsClues, colsClues) — builds DOM (clues + grid cells)
 * fetchAndSolve()                   — async: POST /solve → animateSteps()
 * animateSteps(steps)               — async: replays every solver step
 * sleep(ms)                         — Promise-based delay utility
 */

"use strict";

// ── API ───────────────────────────────────────────────────────────────────────
const API_BASE = "http://127.0.0.1:5000";

// ── Utility ───────────────────────────────────────────────────────────────────

/** Pause execution for `ms` milliseconds. */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// ── Puzzle presets ────────────────────────────────────────────────────────────
const PUZZLE_LIBRARY = {
  easy: {
    label: "⭐ Easy — 5×5 Frame",
    rows: [[5], [1, 1, 1], [1, 1, 1], [1, 1, 1], [5]],
    cols: [[5], [1, 1, 1], [1, 1, 1], [1, 1, 1], [5]],
  },
  medium: {
    label: "⭐⭐ Medium — 10×10 Classic",
    rows: [
      [4], [1, 2], [1, 1, 1], [1, 2], [4],
      [1], [1, 1], [3], [1, 1], [1],
    ],
    cols: [
      [2], [1, 2], [1, 1, 1], [1, 2], [4],
      [1], [1, 1], [3], [1, 1], [1],
    ],
  },
  hard: {
    label: "⭐⭐⭐ Hard — 15×15 Heart",
    rows: [[0], [3, 3], [5, 5], [13], [13], [13], [11], [9], [7], [5], [3], [1], [0], [0], [0]],
    cols: [[0], [3], [5], [7], [8], [9], [9], [9], [9], [9], [8], [7], [5], [3], [0]]
  },
  extreme: {
    label: "⭐⭐⭐⭐ Extreme — 20×20 Smiley",
    rows: [[0], [6, 6], [2, 2, 2, 2], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [2, 2, 2, 2], [6, 6], [0], [0], [0], [12], [1, 1], [1, 1], [1, 1], [2, 2], [6], [0], [0], [0]],
    cols: [[0], [5], [2, 2], [1, 1], [1, 1, 3], [1, 1, 1, 1], [1, 1, 1, 1], [2, 2, 1, 2], [5, 1, 1], [1, 1], [1, 1], [5, 1, 1], [2, 2, 1, 2], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 3], [1, 1], [2, 2], [5], [0]]
  }
};

// ── State ─────────────────────────────────────────────────────────────────────
let currentRowsClues  = PUZZLE_LIBRARY.easy.rows;
let currentColsClues  = PUZZLE_LIBRARY.easy.cols;
let animationRunning  = false;   // guard against double-start
let animationAborted  = false;   // set to true on pause/reset
let currentSteps      = [];
let currentStepIndex  = 0;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const container       = document.getElementById("nonogram-container");
const colCluesEl      = document.getElementById("col-clues");
const rowCluesEl      = document.getElementById("row-clues");
const gameGridEl      = document.getElementById("game-grid");
const statusBar       = document.getElementById("status-bar");
const statusIcon      = document.getElementById("status-icon");
const statusText      = document.getElementById("status-text");

const statTime        = document.getElementById("stat-time");
const statSteps       = document.getElementById("stat-steps");
const statBacktracks  = document.getElementById("stat-backtracks");
const statLogic       = document.getElementById("stat-logic");
const statGuess       = document.getElementById("stat-guess");

const puzzleSelect    = document.getElementById("puzzle-selector");
const customGroup     = document.getElementById("custom-input-group");
const customNameInput = document.getElementById("custom-name");
const customRowsInput = document.getElementById("custom-rows");
const customColsInput = document.getElementById("custom-cols");
const btnClear        = document.getElementById("btn-clear");
const btnReset        = document.getElementById("btn-reset");
const btnSolve        = document.getElementById("btn-solve");
const btnPlay         = document.getElementById("btn-play");
const btnPause        = document.getElementById("btn-pause");
const btnPrev         = document.getElementById("btn-prev");
const btnNext         = document.getElementById("btn-next");
const btnSave         = document.getElementById("btn-save");
const btnDelete       = document.getElementById("btn-delete");
const speedControl    = document.getElementById("speed-control");
const speedSlider     = document.getElementById("speed-slider");
const speedLabel      = document.getElementById("speed-label");

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Set status bar message + CSS state class */
function setStatus(state, icon, message) {
  statusBar.className   = `state--${state}`;
  statusIcon.textContent = icon;
  statusText.textContent = message;
}

/** Populate stats */
function showStats({ time_ms, total_steps, logic, guess, backtracks }) {
  // Animate the values update
  [statTime, statSteps, statLogic, statGuess, statBacktracks].forEach(el => {
    el.classList.remove('updated');
    void el.offsetWidth; // trigger reflow
    el.classList.add('updated');
  });

  statTime.textContent       = `${time_ms} ms`;
  statSteps.textContent      = total_steps;
  statLogic.textContent      = logic;
  statGuess.textContent      = guess;
  statBacktracks.textContent = backtracks;
}

function validateNonogramClues(rowsClues, colsClues) {
  const numRows = rowsClues.length;
  const numCols = colsClues.length;
  
  let sumRows = 0;
  for (const row of rowsClues) {
    if (row.length === 1 && row[0] === 0) continue; // empty row
    const minSpace = row.reduce((a, b) => a + b, 0) + row.length - 1;
    if (minSpace > numCols) {
      throw new Error(`Một hàng yêu cầu ít nhất ${minSpace} ô, nhưng lưới chỉ có ${numCols} cột.`);
    }
    sumRows += row.reduce((a, b) => a + b, 0);
  }

  let sumCols = 0;
  for (const col of colsClues) {
    if (col.length === 1 && col[0] === 0) continue; // empty col
    const minSpace = col.reduce((a, b) => a + b, 0) + col.length - 1;
    if (minSpace > numRows) {
      throw new Error(`Một cột yêu cầu ít nhất ${minSpace} ô, nhưng lưới chỉ có ${numRows} hàng.`);
    }
    sumCols += col.reduce((a, b) => a + b, 0);
  }

  if (sumRows !== sumCols) {
    throw new Error(`Tổng số ô đen ở các hàng (${sumRows}) không bằng tổng số ô đen ở các cột (${sumCols}).`);
  }
}

/** Parse "3,1 | 2 | 1,1" → [[3,1],[2],[1,1]] */
function parseClueString(str) {
  return str.split("|").map(part =>
    part.trim().split(",").map(n => {
      const v = parseInt(n.trim(), 10);
      if (isNaN(v) || v < 0) throw new Error(`Invalid number: "${n.trim()}"`);
      return v;
    })
  );
}

/** Read current delay from slider (dir=rtl: higher value = lower ms = faster) */
function currentDelay() {
  return +speedSlider.value;   // 1 ms (fast, slider right) … 500 ms (slow, slider left)
}

// ── renderBoard ───────────────────────────────────────────────────────────────

/**
 * Rebuild the entire DOM:
 *   - Sets CSS variables --rows / --cols on #nonogram-container
 *   - Fills #col-clues, #row-clues with clue numbers
 *   - Fills #game-grid with interactive cells using data-row / data-col
 *
 * Left-click  → toggle cell-empty ↔ cell-filled
 * Right-click → toggle cell-empty ↔ cell-crossed  (prevents context menu)
 *
 * @param {number[][]} rowsClues
 * @param {number[][]} colsClues
 */
function renderBoard(rowsClues, colsClues) {
  const rows = rowsClues.length;
  const cols = colsClues.length;

  // ── CSS variables ──────────────────────────────────────────────────────────
  container.style.setProperty("--rows", rows);
  container.style.setProperty("--cols", cols);

  // ── Column clues (top-right) ───────────────────────────────────────────────
  colCluesEl.innerHTML = "";
  colCluesEl.style.gridTemplateColumns = `repeat(${cols}, var(--cell-size))`;

  colsClues.forEach((clue, c) => {
    const div = document.createElement("div");
    div.className = "col-clue";
    div.setAttribute("role", "listitem");
    div.setAttribute("aria-label", `Column ${c + 1}: ${clue.join(", ")}`);
    clue.forEach(n => {
      const span = document.createElement("span");
      span.className   = "clue-number";
      span.textContent = n;
      div.appendChild(span);
    });
    colCluesEl.appendChild(div);
  });

  // ── Row clues (bottom-left) ────────────────────────────────────────────────
  rowCluesEl.innerHTML = "";
  rowCluesEl.style.gridTemplateRows = `repeat(${rows}, var(--cell-size))`;

  rowsClues.forEach((clue, r) => {
    const div = document.createElement("div");
    div.className = "row-clue";
    div.setAttribute("role", "listitem");
    div.setAttribute("aria-label", `Row ${r + 1}: ${clue.join(", ")}`);
    clue.forEach(n => {
      const span = document.createElement("span");
      span.className   = "clue-number";
      span.textContent = n;
      div.appendChild(span);
    });
    rowCluesEl.appendChild(div);
  });

  // ── Game grid (bottom-right) ───────────────────────────────────────────────
  gameGridEl.innerHTML = "";
  gameGridEl.style.gridTemplateColumns = `repeat(${cols}, var(--cell-size))`;
  gameGridEl.style.gridTemplateRows    = `repeat(${rows}, var(--cell-size))`;

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const cell = document.createElement("div");
      cell.className = "cell cell-empty";
      cell.setAttribute("role", "gridcell");
      cell.setAttribute("data-row", r);   // used by getCell(r,c)
      cell.setAttribute("data-col", c);
      cell.setAttribute("tabindex", "0");
      cell.setAttribute("aria-label", `Row ${r + 1}, Col ${c + 1}`);

      // Left click — toggle empty ↔ filled
      cell.addEventListener("click", () => {
        if (animationRunning) return;
        setCellState(cell, cell.classList.contains("cell-filled") ? "empty" : "filled");
      });

      // Right click — toggle empty ↔ crossed
      cell.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        if (animationRunning) return;
        setCellState(cell, cell.classList.contains("cell-crossed") ? "empty" : "crossed");
      });

      // Keyboard a11y
      cell.addEventListener("keydown", (e) => {
        if (e.key === " " || e.key === "Enter") { e.preventDefault(); cell.click(); }
        if (e.key === "x" || e.key === "X")     { e.preventDefault(); cell.dispatchEvent(new MouseEvent("contextmenu")); }
      });

      gameGridEl.appendChild(cell);
    }
  }
}

// ── Cell state management ─────────────────────────────────────────────────────

const STATE_CLASSES = [
  "cell-empty", "cell-filled", "cell-crossed",
  "cell-logic", "cell-guess",  "cell-backtrack",
];

/**
 * Set a cell's visual class and inner text.
 * val=1 → filled (■), val=0 → crossed (X) for solver states.
 *
 * @param {HTMLElement} cell
 * @param {"empty"|"filled"|"crossed"|"logic"|"guess"|"backtrack"} state
 * @param {number|null} [val]  — 1 = black, 0 = white (used to set inner content)
 */
function setCellState(cell, state, val = null) {
  // Force animation replay by cloning if already in that class
  if (cell.classList.contains(`cell-${state}`) &&
      (state === "logic" || state === "guess" || state === "backtrack")) {
    const clone = cell.cloneNode(true);
    cell.replaceWith(clone);
    cell = clone;
    reattachCellListeners(cell);
  }

  cell.classList.remove(...STATE_CLASSES);
  cell.classList.add(`cell-${state}`);

  // Handle text content: show '✕' when the cell is deduced or marked as empty
  if (val === 0 || state === "crossed") {
    cell.textContent = "✕";
  } else {
    cell.textContent = "";
  }

  cell.setAttribute("aria-label",
    `Row ${+cell.dataset.row + 1}, Col ${+cell.dataset.col + 1} — ${state}`);
}

/** Re-attach click/contextmenu/keydown after node replacement */
function reattachCellListeners(cell) {
  cell.addEventListener("click", () => {
    if (animationRunning) return;
    setCellState(cell, cell.classList.contains("cell-filled") ? "empty" : "filled");
  });
  cell.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    if (animationRunning) return;
    setCellState(cell, cell.classList.contains("cell-crossed") ? "empty" : "crossed");
  });
  cell.addEventListener("keydown", (e) => {
    if (e.key === " " || e.key === "Enter") { e.preventDefault(); cell.click(); }
    if (e.key === "x" || e.key === "X")     { e.preventDefault(); cell.dispatchEvent(new MouseEvent("contextmenu")); }
  });
}

/** Retrieve cell DOM node by (row, col) */
function getCell(r, c) {
  return gameGridEl.querySelector(`[data-row="${r}"][data-col="${c}"]`);
}

/** Reset every cell to empty */
function resetGrid() {
  gameGridEl.querySelectorAll(".cell").forEach(cell => {
    cell.classList.remove(...STATE_CLASSES);
    cell.classList.add("cell-empty");
    cell.textContent = "";
  });
}

// ── fetchAndSolve — main API integration ──────────────────────────────────────

/**
 * POST the current puzzle to the Flask /solve endpoint,
 * show stats, then start the step-by-step animation.
 *
 * Attached to #btn-solve. Disables the button to prevent concurrent runs.
 */
async function fetchAndSolve() {
  // Guard
  if (animationRunning) return;

  // Reset board & UI
  animationAborted = false;
  resetGrid();
  btnSolve.disabled   = true;
  btnPlay.hidden      = true;
  btnPause.hidden     = true;
  btnPrev.hidden      = true;
  btnNext.hidden      = true;
  speedControl.hidden = true;
  setStatus("solving", "◌", "Sending puzzle to AI solver…");

  try {
    // ── 1. Fetch ─────────────────────────────────────────────────────────────
    const res = await fetch(`${API_BASE}/solve`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rows_clues: currentRowsClues,
        cols_clues: currentColsClues,
      }),
    });

    const data = await res.json();

    if (data.status !== "success") {
      setStatus("error", "✕", `Solver: ${data.message}`);
      btnSolve.disabled = false;
      return;
    }

    // ── 2. Show stats ─────────────────────────────────────────────────────────
    const steps          = data.steps;           // [{x, y, val, type}, ...]
    const logicCount     = steps.filter(s => s.type === "logic").length;
    const guessCount     = steps.filter(s => s.type === "GUESS").length;
    const backtrackCount = steps.filter(s => s.type === "BACKTRACK").length;

    showStats({
      time_ms:     data.stats.time_ms,
      total_steps: data.stats.total_steps,
      logic:       logicCount,
      guess:       guessCount,
      backtracks:  backtrackCount
    });

    setStatus("solved", "✓",
      `Solved in ${data.stats.time_ms} ms · ${steps.length} steps — press ▶ Play Steps`);

    // Show final solution as filled/crossed immediately
    data.solution.forEach((row, r) =>
      row.forEach((val, c) => {
        const cell = getCell(r, c);
        if (cell) setCellState(cell, val === 1 ? "filled" : "crossed");
      })
    );

    // ── 3. Offer step-by-step animation ───────────────────────────────────────
    speedControl.hidden = false;
    btnPlay.hidden      = false;
    btnPause.hidden     = true;
    btnPrev.hidden      = false;
    btnNext.hidden      = false;

    currentSteps = steps;
    currentStepIndex = 0;

    // Store steps for the Play button
    btnPlay.onclick = async () => {
      if (currentStepIndex === 0 || currentStepIndex >= currentSteps.length) {
        resetGrid();
        currentStepIndex = 0;
      }
      await animateSteps();
    };

  } catch (err) {
    setStatus("error", "✕", `Network error: ${err.message}`);
  } finally {
    btnSolve.disabled = false;
  }
}

// ── animateSteps ──────────────────────────────────────────────────────────────

/**
 * Replay every solver step on the grid with colour-coded animation.
 *
 * Step types
 * ----------
 *   "logic"    → blue cell  (AI deduction)
 *   "GUESS"    → amber cell (AI guess)
 *   "BACKTRACK"→ flash-red animation then returns to cell-empty
 *
 * For each step:
 *   - val === 1 → fill the cell (black square)
 *   - val === 0 → mark as empty/crossed
 *
 * Speed is read live from #speed-slider on each frame.
 * dir="rtl" means slider all the way right = value 1 = 1 ms delay (fastest).
 *
 * @param {{ x:number, y:number, val:number, type:string }[]} steps
 */
async function animateSteps() {
  animationRunning = true;
  animationAborted = false;

  btnPlay.hidden  = true;
  btnPause.hidden = false;
  btnPrev.hidden  = true;
  btnNext.hidden  = true;
  btnSolve.disabled = true;

  for (; currentStepIndex < currentSteps.length; currentStepIndex++) {
    if (animationAborted) break;

    const step = currentSteps[currentStepIndex];

    // step.x = col index, step.y = row index  (from Flask history)
    let cell = getCell(step.y, step.x);
    if (!cell) continue;

    if (step.type === "logic") {
      // Blue — AI deduction
      setCellState(cell, "logic", step.val);

    } else if (step.type === "GUESS") {
      // Amber — AI guess
      setCellState(cell, "guess", step.val);

    } else if (step.type === "BACKTRACK") {
      setCellState(cell, "backtrack", step.val);
    }

    // Wait before next step — read slider value every frame so speed changes take effect
    await sleep(currentDelay());

    // Revert backtrack to normal state after the delay
    if (step.type === "BACKTRACK" && !animationAborted) {
      const restoredState = step.val === 1 ? "filled" : (step.val === 0 ? "crossed" : "empty");
      setCellState(cell, restoredState, step.val);
    }
  }

  // ── Finish ────────────────────────────────────────────────────────────────
  animationRunning = false;
  btnSolve.disabled = false;

  if (currentStepIndex >= currentSteps.length) {
    btnPause.hidden   = true;
    btnPlay.hidden    = false;
    btnPrev.hidden    = false;
    btnNext.hidden    = false;
    if (!animationAborted) {
      setStatus("solved", "✓", "Animation complete!");
    }
  }
}

// ── Puzzle loading ────────────────────────────────────────────────────────────

let savedPuzzles = {};

async function loadSavedPuzzles() {
  try {
    const res = await fetch(`${API_BASE}/api/get_puzzles`);
    if (!res.ok) return;
    const puzzles = await res.json();
    
    // Clear old custom db options
    Array.from(puzzleSelect.options).forEach(opt => {
      if (opt.value.startsWith("db-")) opt.remove();
    });

    savedPuzzles = {};
    puzzles.forEach(p => {
      try {
        savedPuzzles[`db-${p.id}`] = {
          label: p.name,
          rows: parseClueString(p.rowsClues),
          cols: parseClueString(p.colsClues)
        };
        
        const opt = document.createElement("option");
        opt.value = `db-${p.id}`;
        opt.textContent = `💾 ${p.name}`;
        puzzleSelect.insertBefore(opt, puzzleSelect.querySelector('option[value="custom"]'));
      } catch (parseErr) {
        console.warn(`Skipping puzzle ${p.id} due to invalid clues:`, parseErr);
      }
    });
  } catch (err) {
    console.error("Failed to load saved puzzles:", err);
  }
}

async function saveCurrentPuzzle() {
  const name = customNameInput ? customNameInput.value.trim() : "";
  const rows = customRowsInput.value;
  const cols = customColsInput.value;

  if (!name) {
    alert("Vui lòng đặt tên cho câu đố!");
    return;
  }

  try {
    const rClues = parseClueString(rows);
    const cClues = parseClueString(cols);
    validateNonogramClues(rClues, cClues);
  } catch (e) {
    alert("Câu đố không hợp lệ, không thể giải được!\nChi tiết: " + e.message);
    return;
  }

  const puzzleData = {
    name: name,
    rows_clues: rows,
    cols_clues: cols
  };

  try {
    const res = await fetch(`${API_BASE}/api/save_puzzle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(puzzleData)
    });

    if (res.ok) {
      alert("Đã lưu câu đố vào database!");
      const data = await res.json();
      await loadSavedPuzzles();
      puzzleSelect.value = `db-${data.id}`;
      puzzleSelect.dispatchEvent(new Event("change"));
    } else {
      const err = await res.json();
      alert(`Lỗi lưu: ${err.error || "Unknown error"}`);
    }
  } catch (err) {
    alert("Network error: " + err.message);
  }
}

async function deleteCurrentPuzzle() {
  const val = puzzleSelect.value;
  if (!val.startsWith("db-")) return;
  const id = val.replace("db-", "");

  if (!confirm("Bạn có chắc chắn muốn xóa câu đố này?")) return;

  try {
    const res = await fetch(`${API_BASE}/api/delete_puzzle/${id}`, {
      method: "DELETE"
    });
    if (res.ok) {
      alert("Đã xóa câu đố!");
      await loadSavedPuzzles();
      puzzleSelect.value = "easy";
      puzzleSelect.dispatchEvent(new Event("change"));
    } else {
      const err = await res.json();
      alert(`Lỗi xóa: ${err.error || "Unknown error"}`);
    }
  } catch (err) {
    alert("Network error: " + err.message);
  }
}

function loadPreset(key) {
  const p = PUZZLE_LIBRARY[key] || savedPuzzles[key];
  if (!p) return;
  currentRowsClues = p.rows;
  currentColsClues = p.cols;

  // Show the clues in the input fields (readonly)
  if (customNameInput) customNameInput.value = p.label || p.name || "";
  customRowsInput.value = currentRowsClues.map(r => r.join(",")).join(" | ");
  customColsInput.value = currentColsClues.map(c => c.join(",")).join(" | ");

  renderBoard(currentRowsClues, currentColsClues);
  resetBoard();
  resetControls();
}

function loadCustom() {
  if (puzzleSelect.value !== "custom") return;
  try {
    const r = parseClueString(customRowsInput.value);
    const c = parseClueString(customColsInput.value);
    validateNonogramClues(r, c);
    currentRowsClues = r;
    currentColsClues = c;
    renderBoard(currentRowsClues, currentColsClues);
    resetControls();
    setStatus("idle", "◈", "Custom puzzle loaded. Press ⚡ Solve or fill manually.");
  } catch (e) {
    setStatus("error", "✕", `Lỗi: ${e.message}`);
  }
}

function resetControls() {
  animationAborted  = true;
  animationRunning  = false;
  btnPlay.hidden      = true;
  btnPause.hidden     = true;
  btnPrev.hidden      = true;
  btnNext.hidden      = true;
  speedControl.hidden = true;
  btnSolve.disabled   = false;
  setStatus("idle", "◈", "Select a puzzle and press ⚡ Solve, or fill cells manually.");
}

function resetBoard() {
  resetGrid();
  statTime.textContent       = "0 ms";
  statSteps.textContent      = "0";
  statLogic.textContent      = "0";
  statGuess.textContent      = "0";
  statBacktracks.textContent = "0";
}

// ── Event wiring ──────────────────────────────────────────────────────────────

puzzleSelect.addEventListener("change", () => {
  const val = puzzleSelect.value;
  const isCustom = val === "custom";
  const isDb = val.startsWith("db-");

  // Editable if it's Custom (to create new) OR a DB puzzle (to rename)
  if (customNameInput) customNameInput.readOnly = (!isCustom && !isDb);
  customRowsInput.readOnly = !isCustom;
  customColsInput.readOnly = !isCustom;
  if (btnSave) btnSave.hidden = !isCustom;
  if (btnDelete) btnDelete.hidden = !isDb;

  if (!isCustom) {
    loadPreset(val);
  } else {
    if (customNameInput) customNameInput.value = "";
    customRowsInput.value = "";
    customColsInput.value = "";
    resetBoard();
  }
});

customRowsInput.addEventListener("change", loadCustom);
customColsInput.addEventListener("change", loadCustom);
if (btnSave) btnSave.addEventListener("click", saveCurrentPuzzle);
if (btnDelete) btnDelete.addEventListener("click", deleteCurrentPuzzle);

if (customNameInput) {
  customNameInput.addEventListener("change", async () => {
    const val = puzzleSelect.value;
    if (!val.startsWith("db-")) return; // Only rename DB puzzles

    const newName = customNameInput.value.trim();
    if (!newName) return;
    const id = val.replace("db-", "");

    try {
      const res = await fetch(`${API_BASE}/api/rename_puzzle/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName })
      });
      if (res.ok) {
        // Update dropdown option text silently
        const opt = puzzleSelect.querySelector(`option[value="${val}"]`);
        if (opt) opt.textContent = `💾 ${newName}`;
        if (savedPuzzles[val]) savedPuzzles[val].label = newName;
      } else {
        const err = await res.json();
        alert(`Lỗi đổi tên: ${err.error || "Unknown error"}`);
      }
    } catch (err) {
      alert("Network error: " + err.message);
    }
  });
}

btnClear.addEventListener("click", () => {
  animationAborted = true;
  animationRunning = false;
  resetBoard();
  resetControls();
});

btnReset.addEventListener("click", () => {
  animationAborted = true;
  animationRunning = false;
  resetGrid();
  resetControls();
});

// ⚡ Solve — main entry point
btnSolve.addEventListener("click", fetchAndSolve);

// ⏸ Pause — abort the running animation loop
btnPause.addEventListener("click", () => {
  animationAborted = true;
  animationRunning = false;
  btnPause.hidden  = true;
  btnPlay.hidden   = false;
  btnPrev.hidden   = false;
  btnNext.hidden   = false;
  btnSolve.disabled = false;
  setStatus("idle", "◈", `Animation paused. Step ${currentStepIndex} / ${currentSteps.length}`);
});

btnPrev.addEventListener("click", () => {
  if (animationRunning || currentStepIndex <= 0) return;
  currentStepIndex--;
  resetGrid();
  for (let i = 0; i < currentStepIndex; i++) {
    const isLast = (i === currentStepIndex - 1);
    applyStepInstant(currentSteps[i], isLast);
  }
  setStatus("idle", "◈", `Step ${currentStepIndex} / ${currentSteps.length}`);
});

btnNext.addEventListener("click", () => {
  if (animationRunning || currentStepIndex >= currentSteps.length) return;
  currentStepIndex++;
  resetGrid();
  for (let i = 0; i < currentStepIndex; i++) {
    const isLast = (i === currentStepIndex - 1);
    applyStepInstant(currentSteps[i], isLast);
  }
  setStatus("idle", "◈", `Step ${currentStepIndex} / ${currentSteps.length}`);
});

function applyStepInstant(step, animateBacktrack = false) {
  let cell = getCell(step.y, step.x);
  if (!cell) return;
  if (step.type === "logic") {
    setCellState(cell, "logic", step.val);
  } else if (step.type === "GUESS") {
    setCellState(cell, "guess", step.val);
  } else if (step.type === "BACKTRACK") {
    if (animateBacktrack) {
      setCellState(cell, "backtrack", step.val);
    } else {
      // For fast-forwarding previous steps, we don't show the red color, but we still apply the restored state
      const restoredState = step.val === 1 ? "filled" : (step.val === 0 ? "crossed" : "empty");
      setCellState(cell, restoredState, step.val);
    }
  }
}

// Speed slider — update label in real time (value IS the delay in ms)
speedSlider.addEventListener("input", () => {
  speedLabel.textContent = `${speedSlider.value} ms`;
});

// ── Boot ──────────────────────────────────────────────────────────────────────
loadSavedPuzzles().then(() => {
  loadPreset("easy");
});
