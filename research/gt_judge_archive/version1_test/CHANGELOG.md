# CHANGELOG — GT-Judge rigor pass

All changes from the audit → fix → experiment-scaffold → paper-rewrite pass.
Grouped by the issue section that motivated them. Each entry states **what**
changed and **why**.

---

## §1.1 — Remove fabricated headline results

- **Deleted `results/benchmark_results.json` and `results/demo_output.json`.**
  *Why:* they held the paper's 100% / 0.0% / 0.984 figures, which were produced
  by a mock hard-coded to pick the labelled-correct answer — they measure
  nothing. Added `results/.gitkeep`.
- **Moved the mock out of the runners into `tests/scripted_llm.py`, renamed
  `create_mock_llm` → `_scripted_llm_for_tests(profile=...)`.** *Why:* keep a
  test-only oracle clearly quarantined from library/runner code so it can never
  be mistaken for a baseline or a result. Files: `tests/scripted_llm.py` (new),
  `run_benchmark.py`, `run_demo.py`, `tests/test_gt_judge.py`.
- **`run_benchmark.py --mock` now prints a loud banner and writes only to
  `results/mock_ci_results.json` (with a `WARNING` field); never to
  `benchmark_results.json`.** *Why:* mock output must be structurally impossible
  to confuse with real output. File: `run_benchmark.py`.
- **On the balanced pilot set the scripted oracle now scores ~20%.** *Why:*
  concrete demonstration that the old 100% was an artefact of the rigged
  dataset + mock, not evidence.

## §1.2 — Authorship / provenance

- **Removed the AI co-author ("AI Research Assistant, antigravity@gemini.ai,
  Advanced Agentic Coding Team") from the paper; sole author is now
  Sawan Ade (IISER Bhopal & IIT Patna).** File: `paper/paper.tex`.
- **Added a "Reproducibility and Use of AI Assistance" statement.** *Why:*
  disclose AI coding/drafting assistance honestly and state that no experimental
  number was model-generated. **Caveat:** the exact venue-appropriate wording of
  the AI-use disclosure must be re-checked against the chosen venue's policy
  before submission. File: `paper/paper.tex`.

## §1.3 — Citations

- **Dropped unverifiable references:** "Anonymous 2026a", "Anonymous 2026b",
  "Amazon CollabEval 2025", "ACL ConfMAD 2025". *Why:* could not be verified
  against arXiv / ACL Anthology / Semantic Scholar; some used org names as
  authors.
- **Added and differentiated real competitors** (all verified):
  - **Kohli (2026)**, *Nine Judges, Two Effective Votes* (Apple,
    arXiv:2605.29800) — the correlated-errors result that motivates §5.
  - **Xie et al. (2025) / ECON** (ICML 2025, arXiv:2506.08292) — differentiated
    as multi-agent *reasoning/coordination*, not judging.
  - **Jung et al. (2025) / Trust-or-Escalate** (ICLR 2025, arXiv:2407.18370) —
    differentiated as *selective* evaluation with abstention.
  - **TrustJudge (2025)** (arXiv:2509.21117) — the real identity of the former
    "Anonymous 2026b".
  - **Verga et al. (2024) / PoLL** (arXiv:2404.18796) — panel baseline.
  - Kept **Zheng et al. (2023) / MT-Bench** (NeurIPS 2023, arXiv:2306.05685) and
    **Prelec (2004) / Bayesian Truth Serum** (Science) with corrected details.
  File: `paper/paper.tex`.

## §2 — Multi-provider LLM client

- **Rewrote `src/llm_client.py`** around an abstract `BaseLLMClient` holding all
  shared logic (retry/backoff + jitter, temp-0 cache, robust JSON extraction,
  token/call counters) with `OpenAIClient` / `AnthropicClient` / `GoogleClient`
  subclasses that lazily import their SDKs. *Why:* one code path for three
  providers; §4 bug-fixes apply everywhere at once. `LLMClient(...)` is kept as a
  factory function so existing `LLMClient(model=, temperature=)` call sites keep
  working; the only new argument is `provider`. Added `LLMConfigError` with
  actionable messages and `PROVIDER_ENV_VAR` mapping.
- **`configs/default.yaml`:** `model.provider` is now authoritative
  (`openai|anthropic|google`) with example model strings per provider.
- **CLI overrides `--provider` / `--model` / `--api-key`** on both `run_demo.py`
  and `run_benchmark.py`, threaded through `GTJudge.from_config(overrides=...)`.
- **Added `.env.example`** (one obvious place for keys) and
  **`scripts/test_connection.py`** (one cheap temp-0 call; prints latency +
  tokens + truncated response; exit 2 on config/key error, 3 on call error).

## §3 — Real experiment pipeline (scaffolding; live runs pending)

- **Expanded `configs/sample_benchmark.json` from 5 → 20 items** via
  `scripts/build_pilot_benchmark.py`. *Why:* the original 5 all had the better
  answer in position A and label A, so "always pick A" scored 100% and the set
  measured nothing. New set: 4 items × 5 categories, superior answer seed-placed
  in A or B, labels balanced 8 A / 8 B / 4 Tie ("always A"/"always B" ≤ 40%).
  Original 5-item file preserved as `sample_benchmark.original5.json.bak`.
- **`run_benchmark.py` cost estimator + confirmation** before any paid call
  (`estimate_calls` / `confirm_spend`), `--tier {pilot,full}`, `--repeats`,
  mean±std aggregation, and a post-hoc correlation estimate that reports the
  *measured* `n_eff`.
- **Ablation harness `scripts/run_ablations.py`** running the full pipeline plus
  No-G1 / No-G2 / No-G3 lesions (implemented in `GTJudge`).
- **Live Tier-1/Tier-2 runs are NOT done** — the sandbox has no network route to
  any provider. All headline numbers remain `TODO — pending real run`.

## §4 — Code quality

- **Race condition fixed in `src/debate_game.py`:** replaced instance-level
  `_claim_counter` / `_attack_counter` (mutated by the same `DebateGame` instance
  running concurrently for A and B) with per-run `itertools.count`. *Why:* real
  cross-thread id collision under the `ThreadPoolExecutor`.
- **Formula reconciliation (code ↔ paper):**
  - Debate score is a **length-normalised mean** in the code; the paper's Def-1
    score (previously an unnormalised sum) was updated to match
    (Eq. debate score). *Why:* a sum re-introduces the verbosity bias the game is
    meant to remove.
  - The arbitration utility's extra terms (`½·U_cal` calibration bonus and
    `α_deb`·debate-prior alignment) are now stated explicitly in the paper
    (Eq. utility). *Why:* paper must match `src/arbitration_game.py`.
- **Test suite expanded 22 → 54 tests** (`tests/test_gt_judge.py`): multi-provider
  factory + error paths, robust JSON extraction, the correlation module
  (`n_eff` identity, GLS weights sum to 1, bounds), arbitration correction
  behaviour, ablation modes, and edge cases (single evaluator, ties, empty
  answers, malformed model output, logit/sigmoid roundtrip). These caught two
  real schema issues during the pass.
- **Pinned `requirements.txt`** to tested versions and added `numpy` (new §5
  dependency); provider SDKs listed as optional. *Why:* reproducible fresh-env
  install.
- **Seed strategy:** the synthetic validation and the pilot builder are seeded
  (`20260718`); dataset sampling and persona ordering are seed-controlled. Live
  LLM sampling at temperature > 0 cannot be seeded and is run-to-run variable —
  hence the Tier-2 repeats with mean±std.

## §5 — New contribution: correlated-error correction

- **New `src/correlation.py`:** `equicorrelation`, `pearson_correlation_matrix`,
  `shrink_to_identity` (Ledoit–Wolf-style), `effective_n = 1ᵀΣ⁻¹1` (clipped
  `[1,n]`), and `gls_weights` (min-variance, uniform fallback).
- **`src/arbitration_game.py` confidence stage rewritten** as a **logarithmic
  opinion pool that counts `n_eff` (not `n`) independent judges**:
  `ℓ* = ℓ_prior + n_eff·(GLS-mean-logit − ℓ_prior)`. *Why:* this is the faithful
  correction to the Kohli et al. failure mode — a naive pool treats correlated
  judges as `n` independent votes and becomes overconfident. Reduces to the full
  independent pool at ρ=0 and to a single judge at ρ→1. Added safe
  `_logit`/`_sigmoid`. `ArbitrationResult` gained `n_effective`,
  `effective_correlation`, `confidence_uncorrected` (`src/models.py`);
  config gained `correlation_correction` + `prior_rho`
  (`configs/default.yaml`, `src/gt_judge.py`).
- **`scripts/validate_correlation_correction.py`** (seeded, no LLM): verifies the
  `n_eff` identity and shows the correction is the identity at ρ=0 and improves
  ECE / overconfidence-on-wrong / Brier as ρ grows. This is the one real
  empirical result available offline (see `VAL-001` in EXPERIMENTS.md).
- *Framing note:* the correction targets **calibration**, not accuracy — it does
  not claim to recover the independent information Kohli et al. show is lost.

## §6 — Paper rewrite

- **Reconstructed the paper as LaTeX source** (`paper/paper.tex`; no `.tex`
  existed before, only `paper.pdf`) and recompiled `paper.pdf`. Abstract,
  contributions, and conclusion now carry real-or-`TODO` numbers with `n` stated;
  the fabricated Table 1 is replaced by an honest status section plus the real
  §5 synthetic Table 1; Related Work adds ECON / Kohli / Trust-or-Escalate /
  TrustJudge / PoLL; Limitations is honest (live benchmark not run, `n_eff`
  validated on synthetic panels, single-provider tested, `prior_rho`
  hyperparameter).
- **`README.md`** rewritten: multi-provider setup, `.env.example`,
  `test_connection.py`, mock-mode warning, 20-item pilot, Python 3.12, and an
  up-front status block; removed "complete, verified" overclaims.
- **`EXPERIMENTS.md`** rewritten: removed the fabricated `EXP-003` (100% / 0.984);
  added the real `VAL-001` synthetic result and `pending` protocol entries for
  the pilot and full runs.

## §7 — This CHANGELOG

- Added `CHANGELOG.md` (this file), grouped by section with what + why + files.
