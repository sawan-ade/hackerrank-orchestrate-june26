"""
GT-Judge Demo Runner
=====================
Run a single evaluation instance (DP vs. naive-recursive LCS) through the full
GT-Judge pipeline.

Usage:
    python run_demo.py --provider google --model gemini-1.5-flash   # real
    python run_demo.py --mock                                        # scripted oracle

The --mock path uses the scripted CI oracle from tests/ (issue §1.1); it exercises
the pipeline without a model and is clearly labelled as non-empirical.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.gt_judge import GTJudge

DEMO_QUESTION = ("Write a function to find the longest common subsequence of two strings. "
                 "Explain your approach and analyze its time complexity.")

DEMO_ANSWER_A = """Here's a dynamic programming solution:

```python
def lcs(s1, s2):
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    result = []
    i, j = m, n
    while i > 0 and j > 0:
        if s1[i-1] == s2[j-1]:
            result.append(s1[i-1]); i -= 1; j -= 1
        elif dp[i-1][j] > dp[i][j-1]:
            i -= 1
        else:
            j -= 1
    return ''.join(reversed(result))
```

Bottom-up DP. Time O(m*n), space O(m*n)."""

DEMO_ANSWER_B = """The longest common subsequence can be found using recursion:

```python
def lcs(s1, s2):
    if not s1 or not s2:
        return ""
    if s1[-1] == s2[-1]:
        return lcs(s1[:-1], s2[:-1]) + s1[-1]
    else:
        r1 = lcs(s1[:-1], s2); r2 = lcs(s1, s2[:-1])
        return r1 if len(r1) > len(r2) else r2
```

Checks if last characters match. Time complexity is O(2^n) in the worst case."""


def _build_mock_judge(config_path):
    from tests.scripted_llm import _scripted_llm_for_tests
    from src.debate_game import DebateGame
    from src.calibration_game import CalibrationGame
    from src.arbitration_game import ArbitrationGame
    import yaml
    cfg = yaml.safe_load(open(config_path))
    llm = _scripted_llm_for_tests("demo")
    debate = DebateGame(llm=llm, max_rounds=cfg.get("game1_debate", {}).get("rounds", 3),
                        lambda_cost=cfg.get("game1_debate", {}).get("lambda_token_cost", 0.001))
    calib = CalibrationGame(llm=llm, n_evaluators=cfg.get("pipeline", {}).get("evaluator_count", 2))
    g3 = cfg.get("game3_arbitration", {})
    arb = ArbitrationGame(correlation_correction=g3.get("correlation_correction", True),
                          prior_rho=g3.get("prior_rho", 0.6))
    return GTJudge(llm=llm, debate_game=debate, calibration_game=calib, arbitration_game=arb)


def main():
    p = argparse.ArgumentParser(description="GT-Judge Demo Runner")
    p.add_argument("--config", default="configs/default.yaml")
    p.add_argument("--provider", default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--api-key", default=None)
    p.add_argument("--ground-truth", default=None, choices=["A", "B", "Tie"])
    p.add_argument("--mock", action="store_true")
    args = p.parse_args()

    print("=" * 60)
    print("  GT-Judge — Game-Theoretic Multi-Agent LLM Judge (demo)")
    print("=" * 60)

    if args.mock:
        print("\n*** MOCK MODE: scripted oracle, NOT a real model. Demo only. ***\n")
        judge = _build_mock_judge(args.config)
    else:
        overrides = {k: v for k, v in
                     {"provider": args.provider, "model": args.model, "api_key": args.api_key}.items()
                     if v is not None}
        try:
            judge = GTJudge.from_config(args.config, overrides=overrides)
        except Exception as e:
            print(f"Error building judge: {e}")
            sys.exit(1)

    print(f"[Config] {args.config} | model={judge.llm.model} | rounds={judge.debate_game.max_rounds}")
    print("[Pipeline] Running...\n")
    result = judge.evaluate(DEMO_QUESTION, DEMO_ANSWER_A, DEMO_ANSWER_B, ground_truth=args.ground_truth)

    print("=" * 60 + "\n  RESULTS\n" + "=" * 60)
    print(result.justification)
    print(f"\nEffective evaluators n_eff: {result.arbitration_result.n_effective:.2f} "
          f"(implied rho={result.arbitration_result.effective_correlation:.2f})")
    print(f"Confidence: {result.confidence:.3f} "
          f"(uncorrected {result.arbitration_result.confidence_uncorrected:.3f})")
    print(f"Total tokens consumed: {result.total_tokens}")

    out = Path("results/demo_output.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = result.model_dump()
    payload["_mock"] = args.mock
    json.dump(payload, open(out, "w"), indent=2, default=str)
    print(f"\n[Output] Saved to: {out}" + ("  (mock)" if args.mock else ""))


if __name__ == "__main__":
    main()
