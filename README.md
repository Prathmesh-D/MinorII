# Entropy — AES-256 Benchmark Tool

**Research Title:**
*An Experimental Performance Analysis of AES-GCM and AES-CTR with Emphasis on Authentication Overhead*

**Team:** Entropy | Cybersecurity Research

---

## Download & Quick Start

Clone the repository, create a virtual environment, install requirements, and run the GUI or CLI:

```bash
# clone the repo
git clone https://github.com/Prathmesh-D/MinorII.git
cd MinorII/entropy-aes-benchmark

# create and activate a venv (Windows example)
python -m venv .venv
.\.venv\Scripts\activate

# upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# run the GUI
python app.py

# or run CLI examples
python main.py --run-experiments
python main.py --generate-graphs
```

Note: On Linux you may need `sudo apt install python3-tk` to get `tkinter` support.

---

## Research Question

> How much performance overhead does authentication add when using AES-GCM compared to AES-CTR?

AES-GCM provides both encryption and authentication (AEAD), while AES-CTR provides encryption only. This project benchmarks the two modes across varying file sizes and types, isolates the authentication overhead, and demonstrates the security trade-off through a tamper detection demo.

---

## Tech Stack

| Component | Purpose |
|---|---|
| Python 3.11+ | Core language |
| `cryptography` (PyCA) | AES-CTR and AES-GCM implementation |
| `time.perf_counter_ns()` | Nanosecond-precision timing |
| `numpy` | Statistical calculations (mean, std dev, min, max) |
| `pandas` | CSV loading and data manipulation |
| `matplotlib` + `seaborn` | Graph generation |
| `matplotlib.backends.backend_tkagg` | Embed matplotlib graphs in Tkinter |
| `tkinter` / `tkinter.ttk` | Desktop GUI (stdlib) |
| `rich` | Pretty console output for CLI mode |
| `configparser` | config.ini loading |
| `pytest` | Unit testing |
| `threading` | Background benchmark execution |

---

## Installation

```bash
# Clone or extract the project
cd entropy-aes-benchmark

# Install dependencies
pip install -r requirements.txt
```

**Requirements file contents:**
```
cryptography>=42.0.0
numpy>=1.26.0
pandas>=2.2.0
matplotlib>=3.8.0
seaborn>=0.13.0
rich>=13.7.0
scipy>=1.11.0
pytest>=8.0.0
```

> **Note:** `tkinter` is included with standard Python installations. If missing on Linux, install via `sudo apt install python3-tk`.

---

## How to Run

### GUI (primary demo)
```bash
python app.py
```
Opens the desktop application with 6 tabs:
1. **Single File Test** — encrypt one file, see CTR vs GCM comparison
2. **Full Benchmark** — run complete suite in either **Manual Files** mode or **Generated** mode (fresh random files each run)
3. **Graphs** — browse 6 comparison charts with interpretation notes, key numeric takeaways, and 95% confidence-interval error bars where applicable
4. **Results** — filter and sort the CSV results table
5. **Summary** — KPI cards, auto-generated benchmark conclusions, and Welch t-test significance metrics
6. **Tamper Demo** — animated GCM vs CTR tamper detection

**Keyboard shortcuts:**
| Shortcut | Action |
|---|---|
| `Ctrl+1` through `Ctrl+6` | Switch tabs |
| `Ctrl+Q` | Quit |

### CLI
```bash
python main.py --all            # Run everything (config check + demo + benchmark + graphs)
python main.py --run-experiments # Run benchmark suite only
python main.py --generate-graphs # Generate graphs from existing CSV
python main.py --demo           # Tamper detection demo in terminal
python main.py --check-config   # Validate config and list discovered files
```

### Tests
```bash
pytest tests/
```

---

## Input File Setup

You now have two options:

- **Manual mode**: place your own files under the configured `data/input_files/F*_...` folders.
- **Generated mode**: in the Benchmark tab choose `Generated` to auto-create fresh text/image/binary files for each selected size group before testing.

Create the following folder structure under `data/input_files/`:

```
data/input_files/
├── F1_1MB/
│   ├── text.txt      (1 MB text file)
│   ├── image.jpg     (1 MB image file)
│   └── binary.bin    (1 MB random binary)
├── F2_5MB/
│   ├── text.txt      (5 MB)
│   ├── image.jpg     (5 MB)
│   └── binary.bin    (5 MB)
├── F3_10MB/
│   ├── text.txt      (10 MB)
│   ├── image.jpg     (10 MB)
│   └── binary.bin    (10 MB)
├── F4_50MB/
│   ├── text.txt      (50 MB)
│   ├── image.jpg     (50 MB)
│   └── binary.bin    (50 MB)
└── F5_100MB/
    ├── text.txt      (100 MB)
    ├── image.jpg     (100 MB)
    └── binary.bin    (100 MB)
```

**Quick generation (Python):**
```python
import os
for name, size in [("F1_1MB",1),("F2_5MB",5),("F3_10MB",10),("F4_50MB",50),("F5_100MB",100)]:
    d = f"data/input_files/{name}"
    os.makedirs(d, exist_ok=True)
    with open(f"{d}/text.txt","wb") as f: f.write(b"A"*(size*1024*1024))
    with open(f"{d}/binary.bin","wb") as f: f.write(os.urandom(size*1024*1024))
    # For image.jpg, use any JPEG resized/padded to the target size
```

---

## config.ini Reference

| Section | Key | Default | Description |
|---|---|---|---|
| `[paths]` | `input_dir` | `data/input_files` | Root directory containing file groups |
| | `results_dir` | `data/results` | Output directory for CSV and graphs |
| | `csv_file` | `data/results/benchmark_results.csv` | Path to results CSV |
| | `graphs_dir` | `data/results/graphs` | Directory for generated PNG graphs |
| `[experiment]` | `runs` | `5` | Total runs per file×mode (including warm-up) |
| | `warmup_runs` | `1` | Runs discarded as warm-up (run 0) |
| | `file_groups` | `F1_1MB,...,F5_100MB` | Comma-separated group folder names |
| `[crypto]` | `key_size_bytes` | `32` | AES key length (32 = AES-256) |
| | `ctr_nonce_size` | `16` | CTR nonce length in bytes |
| | `gcm_nonce_size` | `12` | GCM nonce length in bytes |
| | `gcm_tag_length` | `16` | GCM authentication tag length (128 bits) |
| `[ui]` | `window_title` | `Entropy — AES Benchmark Tool` | GUI window title |
| | `window_width` | `1100` | Window width in pixels |
| | `window_height` | `720` | Window height in pixels |
| | `theme` | `clam` | ttk theme name |

---

## CSV Column Reference

Each benchmark run produces two rows (one CTR, one GCM) with these columns:

| Column | Type | Description |
|---|---|---|
| `timestamp` | ISO 8601 | UTC timestamp of the experiment |
| `file_group` | string | Group label (e.g. `F1_1MB`) |
| `file_type` | string | `text`, `image`, or `binary` |
| `mode` | string | `AES-CTR` or `AES-GCM` |
| `file_size_bytes` | int | File size in bytes |
| `file_size_mb` | float | File size in megabytes |
| `avg_enc_time_ns` | float | Average encryption time (ns), runs 1–4 |
| `avg_dec_time_ns` | float | Average decryption time (ns), runs 1–4 |
| `avg_enc_time_ms` | float | Same, converted to milliseconds |
| `avg_dec_time_ms` | float | Same, converted to milliseconds |
| `enc_throughput_mbps` | float | Encryption throughput (MB/s) |
| `dec_throughput_mbps` | float | Decryption throughput (MB/s) |
| `authentication_overhead_ns` | float | GCM enc − CTR enc (ns). 0 for CTR rows |
| `overhead_percent` | float | `((GCM − CTR) / CTR) × 100`. 0 for CTR rows |
| `cost_per_mb_enc` | float | Encryption cost (ms/MB) |
| `cost_per_mb_dec` | float | Decryption cost (ms/MB) |
| `std_dev_enc_ns` | float | Std deviation of encryption times (ns) |
| `std_dev_dec_ns` | float | Std deviation of decryption times (ns) |
| `min_enc_ns` / `max_enc_ns` | int | Min/max encryption time (ns) |
| `min_dec_ns` / `max_dec_ns` | int | Min/max decryption time (ns) |
| `raw_enc_times_ns` | pipe-sep | All 5 raw encryption times, pipe-separated |
| `raw_dec_times_ns` | pipe-sep | All 5 raw decryption times, pipe-separated |

---

## Generated Graphs

Six PNG charts are produced in `data/results/graphs/`:

| File | Title | Description |
|---|---|---|
| `enc_time_vs_size.png` | Encryption Time vs File Size | Line chart of CTR vs GCM encryption latency with 95% CI error bars |
| `dec_time_vs_size.png` | Decryption Time vs File Size | Line chart of CTR vs GCM decryption latency with 95% CI error bars |
| `throughput_vs_size.png` | Throughput vs File Size | Grouped bar chart of encryption throughput (MB/s) with 95% CI error bars |
| `overhead_percent.png` | Authentication Overhead % | Bar chart of GCM overhead percentage by file group with 95% CI error bars |
| `cost_per_mb.png` | Cost per MB | Grouped bar chart of ms/MB for CTR vs GCM with 95% CI error bars |
| `variance_by_filetype.png` | Variance by File Type | Heatmap of encryption-time standard deviation by file type and group |

---

## Experimental Limitations

- **Single machine**: Results are specific to the hardware, OS, and Python version used. AES-NI support varies by CPU.
- **Python overhead**: Python's interpreter adds per-call overhead that may mask small differences at very small file sizes. A C/C++ implementation would yield lower absolute times.
- **GC and OS scheduling**: Despite `gc.collect()` before each timed run and warm-up discarding, garbage collection pauses and OS thread scheduling can introduce variance.
- **In-memory only**: Files are read into memory before timing. This does not capture real-world I/O-bound scenarios where disk speed is a factor.
- **No AAD tested**: AES-GCM supports Additional Authenticated Data (AAD), which is not benchmarked here. AAD would add further overhead.
- **Statistical sample size**: 4 measured runs (after 1 warm-up) per configuration is adequate for trend detection but not for publishable statistical significance.
- **No parallel/pipelined benchmarking**: Each experiment runs sequentially; real-world usage may involve concurrent encryption.

---

## Project Structure

```
entropy-aes-benchmark/
├── config.ini              Configuration
├── requirements.txt        Python dependencies
├── main.py                 CLI entry point
├── app.py                  GUI entry point
├── data/
│   ├── input_files/        Test files (F1_1MB … F5_100MB)
│   └── results/
│       ├── benchmark_results.csv
│       └── graphs/         Generated PNG charts
├── src/
│   ├── crypto/             AES-CTR, AES-GCM, key management
│   ├── benchmark/          Timing utils, runner, config loader
│   ├── metrics/            Throughput, overhead, cost, stats
│   ├── logging/            CSV logger
│   ├── reporting/          KPI summary + Welch t-test analysis
│   ├── visualization/      Graph generator (matplotlib + seaborn)
│   ├── demo/               Tamper detection demo logic
│   └── ui/                 Tkinter GUI (6 tabs)
└── tests/                  pytest unit tests
```

---

*Entropy — Cybersecurity Research Project*
