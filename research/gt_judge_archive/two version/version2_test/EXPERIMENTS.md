# GT-Judge Experiment Log

This log tracks experimental runs and their **status**. Ground rule: no number
here is invented. Anything requiring live model calls that has not been run is
marked `pending`, not estimated.

---

## Benchmarking methodology

GT-Judge is intended to be compared against:
1. **Single LLM judge** — one model, generic rubric prompt.
2. **Vanilla multi-agent debate** — evaluators debate with no game structure,
   token cost, or consensus rule.
3. **Panel / majority vote** — the setting Kohli et al. (2026, arXiv:2605.29800)
   show is undermined by correlated errors; the §5 correction targets this.

### Primary metrics
- **Accuracy** vs. human preference labels.
- **Position flip rate (%)** — how often the verdict changes when A/B are swapped.
- **Verbosity bias** — score change when one answer is padded with filler.
- **Brier reward** — `1 - (y - p_hat)^2` on labelled tasks.

---

## Experiment registry

### `VAL-001` — Correlated-error correction, synthetic (REAL, reproducible now)
- **Date:** 2026-07-18
- **Script:** `scripts/validate_correlation_correction.py` (seed `20260718`, no LLM)
- **Setup:** synthetic judge panels, `n=3`, 20,000 trials, known error-correlation ρ.
- **Results (real):**
  - `n_eff` identity `1ᵀΣ⁻¹1` matches closed form `n/(1+(n-1)ρ)` to `<1e-6` for
    all tested `(n,ρ)`.
  - Correction is the **identity at ρ=0** (ΔECE = 0.0000).
  - At **ρ=0.9**: ECE 0.391 → 0.267 (−32%), overconfidence-on-wrong 0.314 → 0.169
    (−46%), Brier 0.177 → 0.158.
  - Full table: paper Table 1; raw output `results/correlation_validation.txt`.
- **Scope:** validates the *mechanism* on data with known ρ. Measuring the
  realised correlation of live judge backbones is a Tier-2 experiment (below).

### `DEMO-001` — LCS demo (pipeline plumbing only)
- **Status:** runs end-to-end with `--mock` (scripted oracle) offline; a real
  run needs a backbone. The mock's verdict/confidence are **not** empirical.
- **Real run:** `pending backbone access`.

### `PILOT-001` — Tier-1 stratified pilot
- **Dataset:** `configs/sample_benchmark.json` — 20 items, 4 per category
  (Coding, Math & Logic, Writing & Reasoning, Summarization, Argumentation).
  Superior answer placed in A or B by fixed seed; labels balanced 8 A / 8 B /
  4 Tie, so "always A" and "always B" each score only 40%.
- **Model / repeats:** free-tier backbone, single run.
- **Results:** `accuracy pending`, `flip rate pending`, `Brier pending`.
- **Status:** dataset released; run **pending backbone access**.

### `FULL-001` — Tier-2 full benchmark
- **Dataset:** 150–300 items from public preference data (MT-Bench / Chatbot
  Arena; Zheng et al. 2023, arXiv:2306.05685).
- **Backbones:** ≥ 2 judge backbones; 3–5 repeats reported as mean ± std.
- **Includes:** the three ablations below; post-hoc correlation estimate to
  report the *measured* `n_eff` across evaluators.
- **Results:** `pending Tier-2 budget`.
- **Cost control:** `run_benchmark.py` estimates and confirms spend before any
  paid call.

> **Why the live runs are pending.** The sandbox used to prepare this release has
> no network route to any external LLM provider (all provider endpoints return
> `host_not_allowed`), so live runs must be executed in an environment with
> provider access. Per the project's ground rules, no headline number was
> fabricated to fill the gap.

---

## Ablation studies

Harness: `scripts/run_ablations.py` runs the full pipeline plus three lesions:
- **No Game 1 (no debate):** debate results are neutralised (score 0, no tokens).
- **No Game 2 (no calibration):** flat, uninformative confidences (0.5).
- **No Game 3 (no arbitration):** verdict by simple argmax-debate-score rule.

**Offline wiring check (`--mock`, scripted oracle — NOT citable):** the four
configurations run and are distinct. Notably, removing Game 3 breaks position
invariance (flip rate → 100%) while the full pipeline stays at 0%, an offline
signal consistent with the position-invariance proposition. **Real ablation
numbers:** `pending Tier-2 budget`.
