"""
GT-Judge Demo Runner
=====================
Run a single evaluation instance through the full GT-Judge pipeline.

Usage:
    cd A/code
    python run_demo.py
    
    # Or with a custom config:
    python run_demo.py --config configs/default.yaml
    
    # Or in offline mock mode (no API key required):
    python run_demo.py --mock
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add code directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.gt_judge import GTJudge


# ---------------------------------------------------------------------------
# Example evaluation instance (MT-Bench style)
# ---------------------------------------------------------------------------

DEMO_QUESTION = """Write a function to find the longest common subsequence of two strings. 
Explain your approach and analyze its time complexity."""

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
    
    # Backtrack to find the actual subsequence
    result = []
    i, j = m, n
    while i > 0 and j > 0:
        if s1[i-1] == s2[j-1]:
            result.append(s1[i-1])
            i -= 1
            j -= 1
        elif dp[i-1][j] > dp[i][j-1]:
            i -= 1
        else:
            j -= 1
    
    return ''.join(reversed(result))
```

**Approach**: Classic bottom-up DP. We build a 2D table where `dp[i][j]` represents the length of the LCS of `s1[:i]` and `s2[:j]`. We then backtrack through the table to reconstruct the actual subsequence.

**Time Complexity**: O(m × n) where m and n are the lengths of the two strings. 
**Space Complexity**: O(m × n) for the DP table."""

DEMO_ANSWER_B = """The longest common subsequence can be found using recursion:

```python
def lcs(s1, s2):
    if not s1 or not s2:
        return ""
    if s1[-1] == s2[-1]:
        return lcs(s1[:-1], s2[:-1]) + s1[-1]
    else:
        r1 = lcs(s1[:-1], s2)
        r2 = lcs(s1, s2[:-1])
        return r1 if len(r1) > len(r2) else r2
```

This works by checking if the last characters match. If they do, we include that character and recurse on the remaining strings. Otherwise, we try both possibilities and take the longer result.

The time complexity is O(2^n) in the worst case because we explore all possible combinations. This could be improved with memoization but the recursive approach shows the core logic clearly."""


def create_mock_llm():
    """Create a mock LLMClient that returns realistic structured responses for the demo."""
    mock_llm = MagicMock()
    call_counts = {"proposer": 0, "challenger": 0, "validity": 0, "calibration": 0}
    
    def call_structured_mock(system_prompt, user_prompt, temperature=None):
        if "PROPOSER" in system_prompt:
            call_counts["proposer"] += 1
            
            # Check if this is a defense turn or standard turn
            if "A claim you made has been attacked" in user_prompt:
                is_ans_a = "Claim A" in user_prompt
                if is_ans_a:
                    return {
                        "action": "defend",
                        "argument": "Defending A: The bottom-up dynamic programming approach computes overlaps in O(m * n) time, resolving overlapping subproblems efficiently.",
                        "target_claim_id": 1
                    }, 100
                else:
                    return {
                        "action": "defend",
                        "argument": "Defending B: While standard recursion has exponential complexity, it requires no extra setup space.",
                        "target_claim_id": 1
                    }, 100
            
            # Regular claim/clarify turn
            is_ans_a = "dynamic programming" in user_prompt or "bottom-up DP" in user_prompt
            if is_ans_a:
                return {
                    "action": "claim",
                    "argument": "Claim A: The dynamic programming solution runs in O(m * n) polynomial time and correctly computes the LCS.",
                    "target_claim_id": None
                }, 120
            else:
                return {
                    "action": "claim",
                    "argument": "Claim B: The naive recursive solution has O(2^n) time complexity and will time out on long strings.",
                    "target_claim_id": None
                }, 150
                
        elif "CHALLENGER" in system_prompt:
            call_counts["challenger"] += 1
            is_ans_a = "dynamic programming" in user_prompt or "bottom-up DP" in user_prompt
            if is_ans_a:
                return {
                    "action": "concede",
                    "argument": "Concede: The proposer's claim about O(m*n) complexity and accuracy is correct.",
                    "target_claim_id": None
                }, 80
            else:
                return {
                    "action": "attack",
                    "argument": "Attack B: The recursive solution has exponential complexity and lack of memoization makes it highly inefficient.",
                    "target_claim_id": 1
                }, 110
                
        elif "VALIDITY" in system_prompt:
            call_counts["validity"] += 1
            is_ans_a = "Claim A" in user_prompt
            if is_ans_a:
                return {
                    "attack_severity": 0.1,
                    "defense_success": True,
                    "reasoning": "DP correctness is mathematically sound; the challenger concedes."
                }, 50
            else:
                return {
                    "attack_severity": 0.9,
                    "defense_success": False,
                    "reasoning": "Recursion without memoization fails on practical inputs due to redundant subproblem evaluations."
                }, 50
            
        elif "calibrated evaluator" in system_prompt:
            call_counts["calibration"] += 1
            score_a = float(user_prompt.split("- Answer A debate score: ")[1].split("\n")[0])
            score_b = float(user_prompt.split("- Answer B debate score: ")[1].split("\n")[0])
            
            if score_a > score_b:
                confidence = 0.85 if call_counts["calibration"] % 2 == 1 else 0.90
            else:
                confidence = 0.15 if call_counts["calibration"] % 2 == 1 else 0.10
                
            return {
                "confidence": confidence,
                "reasoning": f"Reported confidence based on debate scores: A={score_a}, B={score_b}"
            }, 150
            
        return {"raw_response": "Dummy response"}, 50

    mock_llm.call_structured.side_effect = call_structured_mock
    mock_llm.model = "gpt-4o-mini"
    return mock_llm


def main():
    parser = argparse.ArgumentParser(description="GT-Judge Demo Runner")
    parser.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--ground-truth",
        default=None,
        choices=["A", "B", "Tie"],
        help="Ground truth label for benchmark mode",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in offline mock mode (no OpenAI API calls)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  GT-Judge v1.0 — Game-Theoretic Multi-Agent LLM Judge")
    print("=" * 60)
    print()

    # Initialize pipeline
    if args.mock:
        print("[Mock Mode] Running with mocked LLM responses.")
        os.environ["OPENAI_API_KEY"] = "sk-test-dummy-key-for-demo-mock"
        mock_llm = create_mock_llm()
        judge = GTJudge.from_config(args.config)
        judge.llm = mock_llm
        judge.debate_game.llm = mock_llm
        judge.calibration_game.llm = mock_llm
    else:
        # Check API Key
        if not os.getenv("OPENAI_API_KEY"):
            print("Error: OPENAI_API_KEY environment variable is not set.")
            print("Please set the key or run with --mock for offline validation.")
            sys.exit(1)
        judge = GTJudge.from_config(args.config)

    print(f"[Config] Loaded from: {args.config}")
    print(f"[Config] Model: {judge.llm.model}")
    print(f"[Config] Debate rounds: {judge.debate_game.max_rounds}")
    print()

    # Run evaluation
    print("[Pipeline] Starting evaluation...")
    print(f"[Pipeline] Question: {DEMO_QUESTION[:80]}...")
    print()

    result = judge.evaluate(
        question=DEMO_QUESTION,
        answer_a=DEMO_ANSWER_A,
        answer_b=DEMO_ANSWER_B,
        ground_truth=args.ground_truth,
    )

    # Print results
    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    print()
    print(result.justification)
    print()
    print(f"Total tokens consumed: {result.total_tokens}")
    print()

    # Save to file
    output_path = Path("results/demo_output.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result.model_dump(), f, indent=2, default=str)
    print(f"[Output] Saved to: {output_path}")


if __name__ == "__main__":
    main()
