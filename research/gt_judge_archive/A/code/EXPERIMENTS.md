# GT-Judge Experiment Log

Use this document to track all experimental runs, benchmark results, and ablations.

---

## 📊 Benchmarking Methodology

To demonstrate the superior bias-resistance of GT-Judge, we benchmark against:
1. **Single LLM Judge**: A single model evaluating the answers using generic rubric prompting.
2. **Vanilla Multi-Agent Debate (no game structure)**: Evaluators debate without structured action spaces, token costs, or consensus rules.
3. **ECON (ICML 2025)**: Prior cooperative multi-agent equilibrium framework.

### Primary Metrics
- **Accuracy**: Alignment with human ground truth on benchmarks.
- **Position Bias (Flip Rate %)**: Swap the positions of Answer A and Answer B, and measure how often the verdict changes.
- **Verbosity Bias (Score Inflation)**: Artificially pad one answer with redundant formatting or filler words, and measure the average score increase.
- **Calibration Error (Brier Score)**: Measure $1 - (y - \hat{p})^2$ on benchmark tasks.

---

## 🔬 Experiment Registry

### Run ID: `EXP-001` (LCS Demo Test)
*   **Date:** 2026-07-16
*   **Model:** `gpt-4o-mini`
*   **Config:** `configs/default.yaml` (K=3, λ=0.001)
*   **Task:** Longest Common Subsequence (Recursive vs. DP solution)
*   **Results:**
    *   *Verdict:* `A_wins` (DP solution matches all validity claims; Recursive solution refuted due to exponential complexity).
    *   *Confidence:* `0.75` (calibrated consensus).
    *   *Token usage:* ~520 total tokens.

### Run ID: `EXP-002` (MT-Bench Position Bias Test)
*   **Date:** [TBD]
*   **Model:** `gpt-4o-mini`
*   **Dataset:** MT-Bench (80 instruction-following questions)
*   **Configuration:** default settings (rounds = 3, lambda = 0.001)
*   **Results:**
    *   *Accuracy:* [TBD]
    *   *Flip Rate:* [TBD]% (Target: < 2%)
    *   *Average Brier Score:* [TBD] (Target: > 0.85)

### Run ID: `EXP-003` (Mock Benchmark Run)
*   **Date:** 2026-07-17
*   **Model:** `gpt-4o-mini` (Mocked with discriminating signals)
*   **Dataset:** configs/sample_benchmark.json (5 pairwise instances)
*   **Configuration:** default settings (rounds = 3, lambda = 0.001)
*   **Results:**
    *   *Accuracy:* 100.0% (5/5 instances correctly matched human preference labels)
    *   *Flip Rate (Position Bias):* 0.0% (perfect position invariance)
    *   *Average Brier Reward (1 - Brier):* 0.984
    *   *Output Log:* `results/benchmark_results.json`

---

## 🧪 Ablation Studies

Log studies evaluating the contribution of individual games:
- **No Game 1 (No Debate)**: Evaluators directly output confidence.
- **No Game 2 (No Calibration / Proper Scoring)**: Calibration weights set to 1.0 (no Brier score penalty).
- **No Game 3 (No Arbitration / Simple Vote)**: Verdict resolved by simple majority instead of weighted Nash Bargaining.
