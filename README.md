# Dokumentasi Teknis, Roadmap & Workflow — 8-Puzzle AI Solver

Dokumen ini berisi spesifikasi teknis pengembangan **Backend (Python)**, **Roadmap Proyek**, serta **Aturan & Workflow GitHub Kelompok** agar proses kolaborasi dan integrasi sistem berjalan lancar.

---

## 1. Roadmap Pengembangan Proyek

Status progres pengerjaan sistem saat ini (mengacu pada jadwal Bab III Proposal):

- [x] **Tahap 1 — Penyusunan Proposal & Pemodelan AI:** Perumusan masalah, aturan permainan $3 \times 3$, dan metrik evaluasi.
- [x] **Tahap 2 — Perancangan & Implementasi Frontend (UI):** Antarmuka *Single-View* 1 tab (`index.html`, `style.css`, `app.js`), mode geser manual, generator papan acak *solvable*, kontrol *playback* animasi, dan tabel komparasi.
- [ ] **Tahap 3 — Pengembangan Logika Dasar & Algoritma BFS:** Implementasi *environment* papan $3 \times 3$, validator *solvability*, dan algoritma Breadth-First Search pada `solver.py`.
- [ ] **Tahap 4 — Pengembangan Algoritma Heuristik (GBFS & $A^*$):** Implementasi fungsi heuristik *Manhattan Distance*, Greedy Best-First Search, dan $A^*$ Search pada `solver.py`.
- [ ] **Tahap 5 — REST API & Integrasi Frontend–Backend:** Pembuatan endpoint `/solve` di `app.py` (Flask/FastAPI) dan menghubungkan `SolverBridge` di `app.js` menggunakan `fetch()`.
- [ ] **Tahap 6 — Eksperimen Komparasi Kinerja:** Pengujian ketiga algoritma pada berbagai *initial state* acak yang identik untuk mencatat data *expanded nodes*, *execution time*, dan *path cost*.
- [ ] **Tahap 7 — Penyusunan Laporan Akhir & Presentasi:** Analisis hasil eksperimen ke dalam laporan akhir dan persiapan demo aplikasi.

---

## 2. GitHub Rules & Workflow Kelompok

Agar kode antar anggota tim tidak saling menimpa (*conflict*) dan cabang utama selalu stabil untuk demo, seluruh anggota wajib mengikuti aturan berikut:

### A. Struktur Branch
* `main` $\rightarrow$ **Branch Produksi / Stabil.** Hanya berisi kode yang sudah teruji dan siap presentasi. **Dilarang `git push` langsung ke `main`.**
* `dev` $\rightarrow$ **Branch Integrasi.** Tempat menggabungkan hasil kerja fitur Frontend dan Backend sebelum masuk ke `main`.
* `feat/<nama-fitur>` $\rightarrow$ **Branch Pengerjaan Fitur Baru** (contoh: `feat/backend-bfs`, `feat/heuristic-astar`, `feat/api-integration`).
* `fix/<nama-bug>` $\rightarrow$ **Branch Perbaikan Bug** (contoh: `fix/cors-error`, `fix/solvable-check`).

### B. Alur Kerja (*Workflow*) Harian
1. **Selalu tarik update terbaru** sebelum mulai ngoding:
   ```bash
   git checkout dev
   git pull origin dev
   ```
2. **Buat branch baru** sesuai tugas masing-masing:
   ```bash
   git checkout -b feat/nama-tugas-kamu
   ```
3. **Kerjakan & Commit secara berkala** dengan pesan yang jelas.
4. **Push branch** ke GitHub:
   ```bash
   git push origin feat/nama-tugas-kamu
   ```
5. **Buat Pull Request (PR)** di GitHub menuju branch `dev`, lalu minta minimal **1 anggota lain** untuk *review* sebelum di-*merge*.

### C. Format Pesan Commit (*Conventional Commits*)
Gunakan awalan berikut agar riwayat perubahan mudah dibaca:
* `feat:` menambah fitur baru (contoh: `feat: implementasi algoritma A* dengan manhattan distance`)
* `fix:` memperbaiki bug (contoh: `fix: perbaiki perhitungan expanded nodes pada BFS`)
* `docs:` mengubah dokumentasi/README (contoh: `docs: update kontrak API di BACKEND_SPEC.md`)
* `style:` merapikan tampilan CSS atau format kode tanpa mengubah logika
* `refactor:` merestrukturisasi kode agar lebih efisien

### D. Aturan Kebersihan Repositori
* **Wajib menggunakan `.gitignore`:** Jangan meng-upload folder `venv/`, `__pycache__/`, `.vscode/`, atau file sistem seperti `.DS_Store`.
* **Jaga Kontrak API:** Jangan mengubah nama *key* JSON (`steps`, `metrics`, `expandedNodes`, `executionTimeMs`, `pathCost`) tanpa koordinasi dengan penanggung jawab Frontend.

---

## 3. Tech Stack & Struktur Direktori

* **Frontend:** HTML5, CSS3, Vanilla JavaScript (Selesai)
* **Backend:** Python 3.9+ dengan **Flask** (`flask`, `flask-cors`) atau **FastAPI**
* **Library Bawaan Python:** `collections` (`deque`), `heapq`, `time`

```text
SlidingTilePuzzle/
├── frontend/               # [SELESAI] Antarmuka Single-View Dashboard
│   ├── index.html
│   ├── style.css
│   └── app.js
├── backend/                # [NEXT] Server & Logika Solver AI (Python)
│   ├── app.py              # Entry point server REST API & konfigurasi CORS
│   ├── solver.py           # Logika environment 8-Puzzle, Manhattan Distance, BFS, GBFS, & A*
│   └── requirements.txt    # Daftar dependensi (flask, flask-cors)
├── README.md         # Dokumen spesifikasi teknis, roadmap, & workflow
```

---

## 4. Pemodelan Environment & Aturan Permainan

| Komponen | Spesifikasi Teknis |
| :--- | :--- |
| **Representasi State** | List/Tuple 1D berisi 9 integer (`1`–`8` untuk ubin angka, `0` untuk ubin kosong). |
| **Goal State** | `[1, 2, 3, 4, 5, 6, 7, 8, 0]` (ubin kosong di indeks ke-8 / pojok kanan bawah). |
| **Aksi Legal (*Action*)** | Ubin kosong (`0`) bertukar posisi dengan tetangga terdekat (**Atas, Bawah, Kiri, Kanan**) dalam batas grid $3 \times 3$. |
| **Biaya Langkah (*Step Cost*)** | Setiap 1 kali pergeseran bernilai tetap sebesar `1`. |
| **Validasi Solvability** | Wajib mengecek jumlah *inversion* sebelum pencarian. Jika jumlah inversi ganjil (*unsolvable*), langsung kembalikan error HTTP `400` agar BFS tidak mengalami *infinite loop* atau kehabisan memori. |

---

## 5. Spesifikasi Tiga Algoritma Solver

### A. Breadth-First Search (BFS)
* **Struktur Data:** `collections.deque` (FIFO Queue) dan `set` untuk menyimpan `visited` states.
* **Fungsi Evaluasi:**
  $$f(n) = g(n)$$
* **Karakteristik:** Menjamin solusi optimal (*path cost* terpendek), namun membutuhkan alokasi memori besar pada kedalaman tinggi.

### B. Greedy Best-First Search (GBFS)
* **Struktur Data:** `heapq` (Priority Queue) dan `set` untuk menyimpan `visited` states.
* **Fungsi Evaluasi:**
  $$f(n) = h(n)$$
* **Heuristik $h(n)$:** **Manhattan Distance** — jumlah jarak horizontal ($|x_1 - x_2|$) dan vertikal ($|y_1 - y_2|$) untuk setiap ubin bernomor `1`–`8` terhadap posisinya di *Goal State* (ubin `0` tidak dihitung).

### C. $A^*$ (A-Star) Search
* **Struktur Data:** `heapq` (Priority Queue).
  > **Tips Implementasi:** Simpan item ke dalam `heapq` dengan format tuple `(f_score, tie_breaker_counter, g_score, state_tuple, path)` untuk mencegah `TypeError` saat membandingkan state apabila nilai $f(n)$ identik.
* **Fungsi Evaluasi:**
  $$f(n) = g(n) + h(n)$$
  dengan $g(n)$ sebagai jumlah langkah aktual dari *initial state* dan $h(n)$ menggunakan **Manhattan Distance**.

---

## 6. Standar Pengukuran Metrik Evaluasi

Untuk menjamin validitas data pada eksperimen perbandingan kinerja algoritma:
1. **`expandedNodes` (Konsumsi Memori):** Jumlah total simpul (*node*) yang dikeluarkan (*pop*) dari antrean (*queue* / *priority queue*) untuk diekspansi ke *successor*-nya.
2. **`executionTimeMs` (Waktu Eksekusi):** Durasi murni eksekusi algoritma pencarian menggunakan `time.perf_counter()`, dikonversi ke satuan milidetik (`round((end - start) * 1000, 2)`).
3. **`pathCost` (Kualitas Solusi):** Jumlah total langkah pergeseran dari *initial state* hingga *goal state*, yaitu `len(steps) - 1`.

---

## 7. Kontrak REST API (Frontend $\leftrightarrow$ Backend)

Frontend mengirimkan permintaan ke endpoint berikut saat tombol **Selesaikan** ditekan:

* **URL:** `http://localhost:5000/solve`
* **Method:** `POST`
* **Headers:** `Content-Type: application/json` (Pastikan `CORS` aktif untuk mengizinkan akses dari origin frontend).

### Request Body (Dari Frontend)
```json
{
  "algorithm": "ASTAR",
  "board": [1, 2, 3, 5, 0, 6, 4, 7, 8]
}
```
*Nilai valid untuk `"algorithm"`: `"BFS"`, `"GBFS"`, atau `"ASTAR"`.*

### Response Body Sukses — `200 OK` (Dari Backend)
```json
{
  "steps": [
    [1, 2, 3, 5, 0, 6, 4, 7, 8],
    [1, 2, 3, 0, 5, 6, 4, 7, 8],
    [1, 2, 3, 4, 5, 6, 0, 7, 8],
    [1, 2, 3, 4, 5, 6, 7, 0, 8],
    [1, 2, 3, 4, 5, 6, 7, 8, 0]
  ],
  "metrics": {
    "expandedNodes": 840,
    "executionTimeMs": 18.45,
    "pathCost": 4
  }
}
```
> **Catatan Penting:** Array `steps` **wajib** menyertakan konfigurasi awal pada indeks ke-`0` dan konfigurasi akhir (*Goal State*) pada indeks terakhir agar fitur *playback* animasi (*Play, Pause, Next, Prev*) pada frontend dapat berjalan sesuai urutan langkah.

### Response Body Error — `400 Bad Request` (Jika Board Unsolvable)
```json
{
  "error": "Konfigurasi papan tidak dapat diselesaikan (unsolvable)."
}
```