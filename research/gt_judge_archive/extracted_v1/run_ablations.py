"""
scripts/run_ablations.py  (issue §3)
=====================================
Runs the three GT-Judge ablations — No Game 1 (debate), No Game 2
(calibration), No Game 3 (arbitration) — alongside the full pipeline, on the
pilot benchmark, and writes a comparison report.

Each ablation neutralises exactly one game (see GTJudge.evaluate and the
_neutral_debate / _flat_calibration / _simple_arbitration helpers), so the
delta between "full" and "no_X" isolates game X's contribution to accuracy,
position-flip rate, and calibration.

IMPORTANT (ground rule 0): this runner makes real LLM calls for every
configuration and is therefore subject to the same budget/network constraints
as run_benchmark.py. In an environment without provider access it can only be
exercised with --mock, which uses the scripted test oracle and proves the four
pipelines are wired and distinct — it does NOT produce citable numbers. Real
ablation numbers require a funded key (see EXPERIMENTS.md, Tier-2).

Usage:
    python scripts/run_ablations.py --mock
    python scripts/run_ablations.py --provider openai --model gpt-4o-mini --yes
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.gt_judge import GTJudge  # noqa: E402

ABLATIONS = [None, "no_debate", "no_calibration", "no_arbitration"]
LABELS = {
    None: "full",
    "no_debate": "no_G1_debate",
    "no_calibration": "no_G2_calibration",
    "no_arbitration": "no_G3_arbitration",
}


def load_dataset(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text())
    return data["items"] if isinstance(data, dict) else data


def build_judge(config: str, ablation, args):
    if args.mock:
        # Wire the scripted oracle into every game (offline plumbing check).
        from tests.scripted_llm import _scripted_llm_for_tests
        judge = GTJudge.from_config(config, overrides={"ablation": ablation,
                                                       "api_key": "sk-mock"})
        mock = _scripted_llm_for_tests(profile="benchmark")
        judge.llm = mock
        judge.debate_game.llm = mock
        judge.calibration_game.llm = mock
        return judge
    overrides = {"ablation": ablation}
    if args.provider:
        overrides["provider"] = args.provider
    if args.model:
        overrides["model"] = args.model
    if args.api_key:
        overrides["api_key"] = args.api_key
    return GTJudge.from_config(config, overrides=overrides)


def evaluate_config(judge, dataset) -> dict:
    """Return summary metrics for one judge configuration over the dataset."""
    n = len(dataset)
    correct = 0
    flips = 0
    briers = []
    for item in dataset:
        gt = item.get("human_preference")
        # forward
        fwd = judge.evaluate(item["question"], item["answer_a"],
                             item["answer_b"], ground_truth=gt)
        # backward (swap positions) to measure position-flip
        bwd = judge.evaluate(item["question"], item["answer_b"],
                             item["answer_a"], ground_truth=_swap(gt))
        v_fwd = fwd.verdict.value if hasattr(fwd.verdict, "value") else fwd.verdict
        v_bwd = bwd.verdict.value if hasattr(bwd.verdict, "value") else bwd.verdict
        if _swap_verdict(v_fwd) != v_bwd:
            flips += 1
        if gt is not None and v_fwd == _pref_to_verdict(gt):
            correct += 1
        for c in fwd.calibration_results:
            if c.calibration_score:
                briers.append(c.calibration_score)
    return {
        "accuracy": correct / n if n else 0.0,
        "flip_rate": flips / n if n else 0.0,
        "mean_brier_reward": (sum(briers) / len(briers)) if briers else None,
        "n_items": n,
    }


def _swap(pref):
    return {"A": "B", "B": "A", "Tie": "Tie"}.get(pref, pref)


def _swap_verdict(v):
    return {"A_wins": "B_wins", "B_wins": "A_wins", "Tie": "Tie"}.get(v, v)


def _pref_to_verdict(pref):
    return {"A": "A_wins", "B": "B_wins", "Tie": "Tie"}.get(pref, "Tie")


def main() -> int:
    ap = argparse.ArgumentParser(description="GT-Judge ablation harness (§3)")
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--dataset", default="configs/sample_benchmark.json")
    ap.add_argument("--provider")
    ap.add_argument("--model")
    ap.add_argument("--api-key", dest="api_key")
    ap.add_argument("--mock", action="store_true",
                    help="Offline plumbing check with the scripted oracle (NOT citable).")
    ap.add_argument("--yes", action="store_true", help="Skip the spend confirmation.")
    ap.add_argument("--output", default="results/ablation_results.json")
    args = ap.parse_args()

    if args.mock:
        print("=" * 68)
        print("  ABLATION HARNESS — MOCK MODE (scripted oracle, NOT citable)")
        print("  Proves the 4 pipelines are wired and distinct only.")
        print("=" * 68)
    elif not args.yes:
        print("This will run 4 pipeline variants x 2 orders x N items of REAL "
              "LLM calls.\nRe-run with --yes once you've checked the cost with "
              "run_benchmark.py's estimator.")
        return 1

    dataset = load_dataset(args.dataset)
    report = {
        "run_id": f"ABL-{date.today().isoformat()}",
        "date": date.today().isoformat(),
        "mock": bool(args.mock),
        "provider": args.provider,
        "model": args.model,
        "dataset": args.dataset,
        "configurations": {},
    }
    for ablation in ABLATIONS:
        label = LABELS[ablation]
        judge = build_judge(args.config, ablation, args)
        summary = evaluate_config(judge, dataset)
        report["configurations"][label] = summary
        acc = summary["accuracy"]
        flip = summary["flip_rate"]
        print(f"  {label:<20} acc={acc:5.1%}  flip={flip:5.1%}  n={summary['n_items']}")

    if args.mock:
        report["WARNING"] = ("SCRIPTED ORACLE OUTPUT — not citable. Wiring/"
                             "distinctness check only.")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(f"\nReport saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
