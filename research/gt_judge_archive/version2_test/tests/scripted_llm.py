"""
Scripted LLM fixture for CI / unit tests ONLY (issue §1.1)
==========================================================
This is the object formerly named `create_mock_llm` in run_benchmark.py and
run_demo.py. It is NOT an ablation, baseline, or sanity check — it is a scripted
oracle that keyword-matches answer *content* and always emits the "correct" move
for the hand-written sample items. Because the sample items are constructed so
that Answer A is objectively better and every human label is "A", any metric
computed from this fixture (accuracy, flip rate, Brier) is decided by the script,
not by any model. It therefore measures the plumbing of the pipeline, nothing more.

Consequences of that fact, enforced elsewhere in the repo:
  * It lives in tests/, not in the runnable entry points.
  * `run_benchmark.py --mock` uses it only to smoke-test the pipeline and writes
    to results/mock_ci_results.json behind a loud banner — never to
    results/benchmark_results.json.
  * No number produced with this fixture may appear in the paper.

Real numbers come only from `run_benchmark.py` against a live provider.
"""

from __future__ import annotations

from unittest.mock import MagicMock

# Content keywords that identify the (better) Answer A in the sample benchmark.
_ANSWER_A_KEYWORDS = [
    "dynamic programming", "bottom-up DP", "1/15", "democratized literacy",
    "successfully landed", "equipping students with foundational skills",
]


def _scripted_llm_for_tests(profile: str = "benchmark") -> MagicMock:
    """Return a MagicMock standing in for an LLM client.

    Args:
        profile: "benchmark" or "demo" — only affects the flavour of the canned
                 defense text; the decision logic is identical.
    """
    mock_llm = MagicMock()
    mock_llm.model = "scripted-test-oracle"
    mock_llm.total_calls = 0
    mock_llm.total_tokens = 0
    call_counts = {"proposer": 0, "challenger": 0, "validity": 0, "calibration": 0}

    def call_structured_mock(system_prompt, user_prompt, temperature=None):
        if "PROPOSER" in system_prompt:
            call_counts["proposer"] += 1
            if "A claim you made has been attacked" in user_prompt:
                is_ans_a = "Claim A" in user_prompt
                text = ("Defending A: the approach is correct and efficient."
                        if is_ans_a else
                        "Defending B: verbosity aside, the point stands.")
                return {"action": "defend", "argument": text, "target_claim_id": 1}, 100
            is_ans_a = any(kw in user_prompt for kw in _ANSWER_A_KEYWORDS)
            if is_ans_a:
                return {"action": "claim",
                        "argument": "Claim A: correct, concise, and direct.",
                        "target_claim_id": None}, 120
            return {"action": "claim",
                    "argument": "Claim B: lots of background detail, tries to explain everything.",
                    "target_claim_id": None}, 150

        if "CHALLENGER" in system_prompt:
            call_counts["challenger"] += 1
            is_ans_a = any(kw in user_prompt for kw in _ANSWER_A_KEYWORDS)
            if is_ans_a:
                return {"action": "concede",
                        "argument": "Concede: the claim is correct and clear.",
                        "target_claim_id": None}, 80
            return {"action": "attack",
                    "argument": "Attack B: excessively verbose / inefficient.",
                    "target_claim_id": 1}, 110

        if "VALIDITY" in system_prompt:
            call_counts["validity"] += 1
            is_ans_a = "Claim A" in user_prompt
            if is_ans_a:
                return {"attack_severity": 0.1, "defense_success": True,
                        "reasoning": "Strong defense of a correct claim."}, 50
            return {"attack_severity": 0.9, "defense_success": False,
                    "reasoning": "Attack exposes verbosity/inefficiency."}, 50

        if "calibrated evaluator" in system_prompt:
            call_counts["calibration"] += 1
            score_a = float(user_prompt.split("- Answer A debate score: ")[1].split("\n")[0])
            score_b = float(user_prompt.split("- Answer B debate score: ")[1].split("\n")[0])
            if score_a > score_b:
                confidence = 0.85 if call_counts["calibration"] % 2 == 1 else 0.90
            else:
                confidence = 0.15 if call_counts["calibration"] % 2 == 1 else 0.10
            return {"confidence": confidence,
                    "reasoning": f"Based on debate scores A={score_a}, B={score_b}."}, 150

        return {"raw_response": "Dummy response"}, 50

    mock_llm.call_structured.side_effect = call_structured_mock
    return mock_llm
