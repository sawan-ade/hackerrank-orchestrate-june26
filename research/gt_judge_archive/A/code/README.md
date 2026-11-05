# GT-Judge Codebase

This folder contains the complete, verified, and game-theoretically grounded implementation of the **Game-Theoretic Multi-Agent LLM-as-a-Judge (GT-Judge)** pipeline.

---

## 📂 Directory Layout

```
code/
├── src/
│   ├── __init__.py
│   ├── models.py             # Pydantic schemas for game state & moves (Defs 1-6)
│   ├── llm_client.py         # OpenAI API Client wrapper with retry/cache logic (Fix 1, Fix 3)
│   ├── prompts.py            # Prompt templates enforcing structured action tags
│   ├── debate_game.py        # Game 1: Extensive-form Reasoning Debate (Thm 1, Fix 2)
│   ├── calibration_game.py   # Game 2: Proper Scoring-based Calibration (Thm 2, Fix 4)
│   ├── arbitration_game.py   # Game 3: Nash Bargaining-based Arbitration (Thm 3)
│   └── gt_judge.py           # Pipeline orchestrator: Debate -> Calibrate -> Arbitrate (Def 6)
│
├── configs/
│   ├── default.yaml          # Game hyper-parameters (K rounds, λ token cost, payoffs)
│   └── sample_benchmark.json # 5 pairwise evaluation instances with human labels
│
├── results/
│   ├── demo_output.json      # Output log from the LCS demo run
│   └── benchmark_results.json# Detailed metrics from the benchmark runner
│
├── tests/
│   ├── __init__.py
│   └── test_gt_judge.py      # Expanded test suite covering logic, calibration math, retry logic, and end-to-end mocking
│
├── requirements.txt          # Minimal required dependencies
├── run_demo.py               # Demo runner script with a sample LCS problem
├── run_benchmark.py          # Benchmark evaluation runner (symmetric testing)
├── EXPERIMENTS.md            # Log of baseline and experimental evaluation runs
└── README.md                 # This file
```

---

## 🚀 Setup & Installation

1. **Install Python dependencies:**
   Make sure you have Python 3.8+ installed. Run:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   Export your OpenAI API Key:
   ```bash
   export OPENAI_API_KEY="sk-..."
   # On Windows PowerShell:
   # $env:OPENAI_API_KEY="sk-..."
   ```

---

## 🧪 Running the Tests

To run the unit and integration tests (including retry logic and offline mock tests):
```bash
python -m pytest tests/ -v
```

---

## 📈 Running the Demo

To run a sample evaluation instance (comparing a Dynamic Programming LCS solution vs. a naive Recursive LCS solution):
```bash
python run_demo.py
```

This will run the full 3-game pipeline and output a detailed justification transcript, including individual agent moves, debate scores, calibrated confidence reports, bargaining weights, and the final arbitration outcome.
The results are saved to `results/demo_output.json`.

---

## ⚙️ Game Configurations (`configs/default.yaml`)

- **`game1_debate.rounds` (K)**: Maximum number of proposer-challenger rounds (default: `3`).
- **`game1_debate.lambda_token_cost` (λ)**: Marginal cost of verbose text generation (default: `0.001`).
- **`game2_calibration.ground_truth_mode`**: Select `consensus_proxy` for deployment (where Game 3's final verdict acts as the reference signal for Brier scores) or `benchmark` for evaluation datasets.
- **`game3_arbitration.human_review_cost` ($C_H$)**: Utility penalty of failing to reach consensus (default: `10.0`).
