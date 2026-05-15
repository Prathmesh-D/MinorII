# Entropy AES-256 Benchmark Project Summary

This document provides a high-level, simplified overview of the Entropy AES-256 Benchmark project. It is designed to be a quick reference for presenting to mentors, highlighting the tech stack, library usage, methodology, and final results.

## 1. Tech Stack Overview

*   **Language:** Python 3.11+
*   **UI Framework:** Tkinter (Custom stylized desktop application)
*   **Architecture:** Modular OOP design separating UI components, benchmark logic, statistical calculations, and data visualization.

## 2. Core Libraries Used (How & Where)

*   **`cryptography`**
    *   **Where:** `src/benchmark/aes_runner.py`
    *   **How:** The absolute core of the project. Utilizes the OpenSSL backend for raw AES-256-CTR and AES-256-GCM encryption/decryption primitives. 
*   **`pandas` & `numpy`**
    *   **Where:** `src/reporting/benchmark_report.py`, `src/visualization/graph_generator.py`, `src/ui/tab_summary.py`
    *   **How:** Used for heavily processing the raw CSV logs into aggregated statistics (grouping by file size, calculating means, processing standard deviations).
*   **`scipy`**
    *   **Where:** `src/reporting/benchmark_report.py` (Historical / Underlying logic)
    *   **How:** Provided statistical rigor (Welch's t-test) to prove if performance differences between CTR and GCM were statistically significant rather than just noise.
*   **`matplotlib`**
    *   **Where:** `src/visualization/graph_generator.py`, `src/ui/tab_graphs.py`
    *   **How:** Embedded directly into the Tkinter UI using `FigureCanvasTkAgg` to generate responsive charts (Throughput, Overhead, Cost per MB).
*   **`psutil` & `platform`**
    *   **Where:** `src/ui/tab_sysinfo.py`
    *   **How:** Dynamically fetches physical/logical CPU cores, total RAM, OS version, and OpenSSL backend version to provide environmental context for the benchmarks.

## 3. Data Generation & File Support

The benchmark supports both manual file testing (any file type can be browsed and tested) and a robust auto-generation engine to ensure standardized testing environments.

### Supported Data Profiles (Generated Files)
The auto-generator creates three distinct types of data to test how the AES algorithms handle different levels of entropy:
*   **Zeros / Binary (`.bin`):** Files completely filled with null bytes (`\x00`). Used to test the algorithm against highly predictable, zero-entropy data.
*   **Pattern / Text (`.txt`):** Files filled with a highly repetitive, predictable ASCII string pattern (`AES_BENCHMARK_TEST_STRING_...`).
*   **Random / Image (`.jpg`):** Simulates high-entropy, compressed data. It writes a standard JPEG header and trailer, but fills the body entirely with cryptographically secure random bytes generated via `os.urandom`.

### How Files are Generated
*   **Libraries Used:** Generation relies entirely on Python's native standard library to remain lightweight. It uses `pathlib` for directory orchestration, `os.urandom()` to generate cryptographically secure random entropy, and Python's built-in `open()` for binary file I/O operations.
*   **Incremental Storage:** When the user selects "Generate", the tool creates an incremental subdirectory (e.g., `_generated/batch_1`, `_generated/batch_2` or `single_1`). This preserves previous test datasets so historical data is never unintentionally destroyed.
*   **File Sizes:** Standard benchmark suites generate these three profiles across a standard distribution of sizes: **1 MB, 5 MB, 10 MB, 50 MB, and 100 MB**. 
*   **Performance:** Generation is handled cleanly on background threads using buffered chunk writes (`1MB` chunks at a time) to ensure memory safety even when generating very large 100MB+ files.

## 4. Key Metrics Evaluated

Instead of relying purely on simple stopwatch times, the benchmark evaluates real-world practical metrics:

*   **Average Encryption/Decryption Time (ms):** The raw time taken to process files.
*   **Throughput (MB/s):** The primary measure of speed, calculated as `(File Size in MB) / (Elapsed Time in seconds)`.
*   **Authentication Overhead (%):** Measures the specific performance tax incurred by GCM's GMAC authentication tag calculation compared to CTR's simple stream encryption.
*   **Cost per MB (ms/MB):** Normalizes the time taken so efficiency can be compared regardless of file size.
*   **Coefficient of Variation (CV %):** Assesses the stability/predictability of the algorithms by evaluating their standard deviation relative to their mean.
*   **Throughput Ratio:** Directly compares GCM's throughput as a percentage of CTR's throughput.

## 5. Timing & Accuracy Methodology

To ensure absolute precision, the project measures encryption times using Python's **`time` library**, specifically the highest-resolution hardware clock available: `time.perf_counter_ns()` (nanosecond precision).

### How It Works:
1.  **Isolation from File I/O:** The file is completely loaded into memory *before* the timer starts. Reading and writing files to the disk are explicitly excluded from the measurement to prevent hard drive speed from skewing the results.
2.  **Garbage Collection Pauses:** Before starting the clock, the tool actively forces Python to clear its memory by calling `gc.collect()`. This prevents random garbage collection pauses from interrupting the encryption phase.
3.  **Strict Operation Window:** The nanosecond timer starts, the OpenSSL cryptography function runs, and the timer instantly stops. Only the raw mathematical AES calculation is tracked.

## 6. Final Results & Insights (Example Run)

Based on a comprehensive benchmark run (1MB to 100MB files, Random/Zeros/Pattern data):

*   **Overall Speed:** AES-CTR maintains a slight speed advantage over AES-GCM.
    *   *CTR Mean Throughput:* ~887 MB/s
    *   *GCM Mean Throughput:* ~856 MB/s
*   **Authentication Overhead:** The mathematical cost of GCM providing Data Integrity (AEAD) alongside confidentiality is roughly **9.8% overhead** compared to CTR.
*   **Scaling Behavior:** 
    *   For **small files** (1MB - 10MB), the performance difference is statistically significant, heavily favoring CTR because the setup cost of GCM's authenticator is noticeable.
    *   For **large files** (50MB - 100MB), the throughput gap closes to near-parity (GCM achieves ~97% to 103% of CTR's throughput), indicating GCM scales incredibly well for large payloads.
*   **Security vs. Performance Trade-off:** The tool's Tamper Demo conclusively proves CTR is completely malleable (fails silently on bit-flips). Given that GCM's overhead drops to negligible levels on larger files (less than 5% overhead on 100MB files), **AES-GCM is the highly recommended default**, as the minor performance hit is well worth the guarantee of cryptographic integrity.

## 7. Anticipated Mentor Questions & Defensive Points

To prepare for the presentation, here are answers to common high-level questions a mentor might ask:

*   **"Why test AES-256 instead of AES-128?"**
    *   *Answer:* AES-256 is the gold standard for top-secret grade data encryption. With the theoretical horizon of quantum computing, AES-256 provides a wide enough security margin to remain secure against Grover's algorithm, making it the most future-proof and relevant benchmark target.
*   **"What is the fundamental difference between CTR and GCM?"**
    *   *Answer:* CTR (Counter mode) provides pure *Confidentiality*. It turns AES into a stream cipher but cannot detect if the data is tampered with. GCM (Galois/Counter Mode) provides *AEAD (Authenticated Encryption with Associated Data)*. It encrypts like CTR but also computes a GMAC tag, ensuring both *Confidentiality* and *Data Integrity/Authenticity*.
*   **"How do you prevent CPU throttling or 'cold-start' delays from ruining the data?"**
    *   *Answer:* The tool utilizes **Warm-up Runs**. Before the actual recorded benchmark runs, the system encrypts dummy data. This forces the CPU out of idle states, warms up the CPU cache, and ensures all Python modules are fully loaded into memory. The times from warm-up runs are strictly discarded.
*   **"Why test different file types (Zeroes vs Random/Image)?"**
    *   *Answer:* To prove that AES does not take "shortcuts". A good encryption algorithm must process all data equally, regardless of how compressible or repetitive the input is. The benchmark proves that whether it is encrypting zeros (`.bin`) or pure randomness (`.jpg`), the throughput remains highly consistent.
*   **"Does your hardware impact these results?"**
    *   *Answer:* Yes, drastically. The system info tab explicitly tracks the presence of **AES-NI (Advanced Encryption Standard New Instructions)**. This is hardware-level acceleration built into modern Intel/AMD chips. Our OpenSSL backend leverages this, which is why we achieve massive throughput speeds approaching ~1 GB/s. Without AES-NI, speeds would drop significantly.
