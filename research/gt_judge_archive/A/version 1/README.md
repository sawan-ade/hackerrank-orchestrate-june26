# GT-Judge

A training-free, **game-theoretic multi-agent LLM-as-a-judge**. GT-Judge scores a
pairwise evaluation (question + answer A/B) as the outcome of three coupled games:

1. **Reasoning Debate** (extensive-form, token-penalised) — Game 1
2. **Confidence Calibration** (Brier proper scoring) — Game 2
3. **Consensus Arbitration** (Nash bargaining + correlated-error correction) — Game 3

See `paper/paper.tex` (compiled `paper.pdf`) for the formal treatment.

> **Status (read this first).** The theory, implementation, a 54-test correctness
> suite, an ablation harness, and a *reproducible synthetic validation* of the
> correlated-error correction (§5) are complete. **The end-to-end LLM benchmark
> (accuracy vs. human preference, position-flip rate, verbosity bias) has NOT been
> run on live models yet.** Those numbers are reported as `TODO — pending real run`
> in the paper and `EXPERIMENTS.md`, never estimated. The repository contains no
> fabricated results.

---

## Directory layout

```
.
├── src/
│   ├── models.py             # Pydantic schemas for game state & moves
│   ├── llm_client.py         # Multi-provider client (OpenAI / Anthropic / Google)
│   ├── prompts.py            # Structured-action prompt templates
│   ├── debate_game.py        # Game 1: extensive-form reasoning debate
│   ├── calibration_game.py   # Game 2: Brier-scored confidence calibration
│   ├── arbitration_game.py   # Game 3: Nash bargaining + n_eff correction
│   ├── correlation.py        # §5: effective-evaluator count, GLS weights, shrinkage
│   └── gt_judge.py           # Pipeline orchestrator (+ ablation modes)
├── configs/
│   ├── default.yaml          # Game hyper-parameters + model.provider
│   └── sample_benchmark.json # 20-item balanced, stratified PILOT set
├── scripts/
│   ├── test_connection.py            # One cheap call to check a provider/key
│   ├── build_pilot_benchmark.py      # Regenerates the balanced pilot set
│   ├── run_ablations.py              # No-G1 / No-G2 / No-G3 harness
│   └── validate_correlation_correction.py  # §5 synthetic validation (no LLM)
├── results/                  # Run outputs (mock outputs clearly flagged)
├── tests/
│   ├── test_gt_judge.py      # 54 tests
│   └── scripted_llm.py       # TEST-ONLY deterministic oracle (never a baseline)
├── paper/                    # paper.tex source (+ compiled copy)
├── paper.pdf                 # Compiled paper
├── .env.example              # Where to put API keys
├── requirements.txt          # Pinned dependencies
├── run_demo.py               # Single-instance demo
├── run_benchmark.py          # Benchmark runner (cost-gated)
├── CHANGELOG.md              # What changed and why
└── EXPERIMENTS.md            # Experiment protocol + status
```

---

## Setup

Tested on **Python 3.12**.

```bash
pip install -r requirements.txt
```

Provider SDKs are imported lazily; install only what you use (`openai` is pinned
in `requirements.txt`; `anthropic` / `google-genai` are optional — see comments
there).

### API keys

Copy `.env.example` and fill in the key for the provider you want:

```bash
cp .env.example .env
# then edit .env — one of:
#   OPENAI_API_KEY=sk-...
#   ANTHROPIC_API_KEY=sk-ant-...
#   GOOGLE_API_KEY=...
```

Check a key/provider with one cheap call (prints latency + token use; non-zero
exit on failure):

```bash
python scripts/test_connection.py --provider openai --model gpt-4o-mini
```

---

## Usage

Select the backbone in `configs/default.yaml` (`model.provider`) or override on
the CLI. Both runners accept `--provider`, `--model`, and `--api-key`.

### Demo (one instance)

```bash
python run_demo.py --provider openai --model gpt-4o-mini
python run_demo.py --mock            # offline; scripted oracle, NOT a real result
```

### Benchmark (cost-gated)

```bash
python run_benchmark.py --provider openai --model gpt-4o-mini --tier pilot --repeats 1
```

The runner **estimates the API spend and asks for confirmation before any paid
call** (pass `--yes` to skip the prompt). `--mock` runs the scripted oracle
offline, prints a loud banner, and writes only to `results/mock_ci_results.json`
— those numbers are a plumbing check and must never be cited.

### Ablations

```bash
python scripts/run_ablations.py --provider openai --model gpt-4o-mini --yes
python scripts/run_ablations.py --mock   # offline wiring/distinctness check
```

### §5 correlated-error correction (real, no API needed)

```bash
python scripts/validate_correlation_correction.py
```

This is seeded (seed `20260718`) and fully reproducible offline; its output is
`results/correlation_validation.txt` and Table 1 in the paper.

---

## Tests

```bash
python -m pytest tests/ -v      # 54 tests
```

---

## A note on `--mock`

The scripted oracle in `tests/scripted_llm.py` is a deterministic, hand-written
stand-in used only to exercise the pipeline offline. On the *balanced* pilot set
it scores ~20% — deliberately, to make clear it measures nothing about model
behaviour. It is never a baseline, an ablation, or a source of reported numbers.
