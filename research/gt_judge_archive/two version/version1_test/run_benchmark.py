"""
GT-Judge Benchmark Runner
==========================
Evaluates the GT-Judge pipeline on a benchmark dataset and reports accuracy,
position-bias (flip rate), calibration (Brier reward), and — for the §5
correction — the measured effective evaluator count.

Two tiers (issue §3):
  * Tier 1 (pilot): ~20-30 hand-stratified items, single repeat, free-tier model.
    First honest end-to-end numbers; explicitly NOT the paper's headline.
  * Tier 2 (full):  150+ items from a public preference dataset, >=2 backbones,
    3-5 repeats with mean +/- std. Requires paid keys.

Usage:
    # Real run (needs a key for the configured provider):
    python run_benchmark.py --provider google --model gemini-1.5-flash --repeats 3

    # CI smoke test (scripted oracle, NO model, NEVER writes benchmark_results.json):
    python run_benchmark.py --mock

Key handling: the key is read from the provider's env var (see .env.example) or
passed with --api-key. Nothing is hardcoded.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.table import Table

from src.gt_judge import GTJudge
from src.models import Verdict

console = Console()


def estimate_calls(n_items, rounds, n_eval, repeats, n_models):
    """Rough calls-per-item accounting for the cost estimator (issue §3)."""
    per_evaluate_max = 2 * (4 * rounds) + n_eval       # worst case per evaluate()
    per_evaluate_typical = 2 * (3 * rounds) + n_eval   # some early concedes
    factor = n_items * 2 * repeats * n_models          # 2 = forward + backward
    return {
        "typical": per_evaluate_typical * factor,
        "max": per_evaluate_max * factor,
        "factor_breakdown": f"{n_items} items x 2 orders x {repeats} repeats x {n_models} model(s)",
    }


def confirm_spend(est, assume_yes):
    console.print("\n[bold yellow]Cost / call estimate (issue §3)[/bold yellow]")
    console.print(f"  {est['factor_breakdown']}")
    console.print(f"  Estimated API calls: ~{est['typical']:,} typical, up to {est['max']:,} worst case")
    console.print("  (Actual $ cost depends on provider pricing and tokens per call.)")
    if assume_yes:
        console.print("  [dim]--yes given; proceeding without prompt.[/dim]")
        return
    try:
        resp = input("Proceed with live API calls? [y/N] ").strip().lower()
    except EOFError:
        resp = "n"
    if resp not in ("y", "yes"):
        console.print("[red]Aborted before spending.[/red]")
        sys.exit(1)


def run_once(judge, item):
    """Evaluate one item forward (A,B) and backward (B,A). Returns raw metrics."""
    q, a, b = item["question"], item["answer_a"], item["answer_b"]
    human = item["human_preference"]
    res_fwd = judge.evaluate(q, a, b, ground_truth=human)
    res_bwd = judge.evaluate(q, b, a, ground_truth=human)
    mapped_bwd = {Verdict.A_WINS: Verdict.B_WINS,
                  Verdict.B_WINS: Verdict.A_WINS}.get(res_bwd.verdict, Verdict.TIE)
    flipped = res_fwd.verdict != mapped_bwd
    mapped_human = {"A": Verdict.A_WINS, "B": Verdict.B_WINS}.get(human, Verdict.TIE)
    matches = res_fwd.verdict == mapped_human
    avg_brier = sum(c.calibration_score for c in res_fwd.calibration_results) / \
        max(len(res_fwd.calibration_results), 1)
    return {
        "verdict_forward": res_fwd.verdict.value,
        "verdict_backward": res_bwd.verdict.value,
        "matches_human": matches,
        "position_flip": flipped,
        "brier": avg_brier,
        "confidence": res_fwd.confidence,
        "confidence_uncorrected": res_fwd.arbitration_result.confidence_uncorrected,
        "n_effective": res_fwd.arbitration_result.n_effective,
        "effective_correlation": res_fwd.arbitration_result.effective_correlation,
        "tokens": res_fwd.total_tokens,
        "evaluator_confidences": [c.reported_confidence for c in res_fwd.calibration_results],
    }


def aggregate(runs):
    """Aggregate repeated runs of the SAME item -> mean/std of the metrics."""
    def ms(key):
        vals = [r[key] for r in runs]
        return {"mean": statistics.mean(vals),
                "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0}
    verdicts = [r["verdict_forward"] for r in runs]
    return {
        "verdict_forward_majority": max(set(verdicts), key=verdicts.count),
        "match_rate": sum(r["matches_human"] for r in runs) / len(runs),
        "flip_rate": sum(r["position_flip"] for r in runs) / len(runs),
        "brier": ms("brier"),
        "confidence": ms("confidence"),
        "n_effective": ms("n_effective"),
        "repeats": len(runs),
    }


def _build_mock_judge(config_path):
    """Build a judge wired to the scripted CI oracle (no SDK/key needed)."""
    from tests.scripted_llm import _scripted_llm_for_tests
    from src.debate_game import DebateGame
    from src.calibration_game import CalibrationGame
    from src.arbitration_game import ArbitrationGame
    import yaml
    cfg = yaml.safe_load(open(config_path))
    llm = _scripted_llm_for_tests("benchmark")
    debate = DebateGame(llm=llm, max_rounds=cfg.get("game1_debate", {}).get("rounds", 3),
                        lambda_cost=cfg.get("game1_debate", {}).get("lambda_token_cost", 0.001))
    calib = CalibrationGame(llm=llm, n_evaluators=cfg.get("pipeline", {}).get("evaluator_count", 2))
    g3 = cfg.get("game3_arbitration", {})
    arb = ArbitrationGame(correlation_correction=g3.get("correlation_correction", True),
                          prior_rho=g3.get("prior_rho", 0.6))
    return GTJudge(llm=llm, debate_game=debate, calibration_game=calib, arbitration_game=arb)


def main():
    p = argparse.ArgumentParser(description="GT-Judge Benchmark Evaluator")
    p.add_argument("--config", default="configs/default.yaml")
    p.add_argument("--dataset", default="configs/sample_benchmark.json")
    p.add_argument("--provider", default=None, help="openai | anthropic | google (overrides config)")
    p.add_argument("--model", default=None, help="model string (overrides config)")
    p.add_argument("--api-key", default=None, help="explicit key (else read from env var)")
    p.add_argument("--repeats", type=int, default=1, help="runs per item (>=3 for Tier 2)")
    p.add_argument("--tier", default="pilot", choices=["pilot", "full"])
    p.add_argument("--yes", action="store_true", help="skip cost-confirmation prompt")
    p.add_argument("--mock", action="store_true", help="CI smoke test w/ scripted oracle (NOT a result)")
    p.add_argument("--output", default=None)
    args = p.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        console.print(f"[red]Dataset not found: {dataset_path}[/red]")
        sys.exit(1)
    data = json.load(open(dataset_path))

    if args.mock:
        console.print("[bold white on red] MOCK MODE - SCRIPTED ORACLE, NOT A REAL RESULT [/bold white on red]")
        console.print("[yellow]These numbers are decided by a hand-written script that keyword-matches[/yellow]")
        console.print("[yellow]answer content. They validate pipeline plumbing ONLY and must never be[/yellow]")
        console.print("[yellow]cited as empirical. Output goes to results/mock_ci_results.json.[/yellow]\n")
        judge = _build_mock_judge(args.config)
        output_path = Path(args.output or "results/mock_ci_results.json")
        is_mock = True
    else:
        overrides = {k: v for k, v in
                     {"provider": args.provider, "model": args.model, "api_key": args.api_key}.items()
                     if v is not None}
        try:
            judge = GTJudge.from_config(args.config, overrides=overrides)
        except Exception as e:
            console.print(f"[red]Could not build judge: {e}[/red]")
            sys.exit(1)
        import yaml
        cfg = yaml.safe_load(open(args.config))
        est = estimate_calls(len(data), cfg.get("game1_debate", {}).get("rounds", 3),
                             cfg.get("pipeline", {}).get("evaluator_count", 2), args.repeats, 1)
        confirm_spend(est, args.yes)
        output_path = Path(args.output or "results/benchmark_results.json")
        is_mock = False

    console.print(f"[green]Config:[/green] {args.config}  [green]Dataset:[/green] {dataset_path} "
                  f"({len(data)} items)  [green]Repeats:[/green] {args.repeats}  [green]Tier:[/green] {args.tier}")

    table = Table(title=f"GT-Judge Benchmark ({'MOCK' if is_mock else args.tier})")
    for col in ["ID", "Category", "Human", "Verdict(maj)", "Match%", "Flip%", "Brier(mu+-sd)", "n_eff(mu)"]:
        table.add_column(col, justify="center")

    per_item_reports, all_matches, all_flips, all_briers = [], [], [], []
    evaluator_signal_rows = []

    for idx, item in enumerate(data):
        runs = [run_once(judge, item) for _ in range(args.repeats)]
        for r in runs:
            evaluator_signal_rows.append(r["evaluator_confidences"])
        agg = aggregate(runs)
        per_item_reports.append({"id": item.get("id", idx + 1),
                                 "category": item.get("category", "General"),
                                 "human_preference": item["human_preference"],
                                 "aggregate": agg, "runs": runs})
        all_matches.append(agg["match_rate"]); all_flips.append(agg["flip_rate"])
        all_briers.append(agg["brier"]["mean"])
        table.add_row(str(item.get("id", idx + 1)), item.get("category", "General")[:16],
                      item["human_preference"], agg["verdict_forward_majority"],
                      f"{agg['match_rate']*100:.0f}", f"{agg['flip_rate']*100:.0f}",
                      f"{agg['brier']['mean']:.3f}+-{agg['brier']['std']:.3f}",
                      f"{agg['n_effective']['mean']:.2f}")

    console.print(table)

    corr_report = {}
    try:
        import numpy as np
        from src.correlation import pearson_correlation_matrix, effective_n, shrink_to_identity
        sig = np.array(evaluator_signal_rows, dtype=float)
        if sig.shape[0] >= 2 and sig.shape[1] >= 2:
            sigma = pearson_correlation_matrix(sig)
            corr_report = {
                "measured_correlation_matrix": sigma.tolist(),
                "mean_offdiag_correlation": float(
                    (sigma.sum() - np.trace(sigma)) / (sigma.size - sigma.shape[0])),
                "n_effective_measured": effective_n(shrink_to_identity(sigma, 0.1)),
                "n_evaluators": int(sig.shape[1]),
            }
    except Exception as e:
        corr_report = {"note": f"correlation estimate skipped: {e}"}

    summary = {
        "accuracy_pct": statistics.mean(all_matches) * 100 if all_matches else 0.0,
        "flip_rate_pct": statistics.mean(all_flips) * 100 if all_flips else 0.0,
        "mean_brier_reward": statistics.mean(all_briers) if all_briers else 0.0,
        "n_items": len(data), "repeats": args.repeats,
        "n_runs_total": len(data) * args.repeats,
    }
    console.print("\n[bold]Summary[/bold]")
    console.print(f"  Accuracy: {summary['accuracy_pct']:.1f}%   Flip rate: {summary['flip_rate_pct']:.1f}%   "
                  f"Mean Brier reward: {summary['mean_brier_reward']:.3f}")
    if "n_effective_measured" in corr_report:
        console.print(f"  Measured evaluator correlation: {corr_report['mean_offdiag_correlation']:.3f} -> "
                      f"n_eff = {corr_report['n_effective_measured']:.2f}/{corr_report['n_evaluators']} (§5)")

    report = {
        "run_id": f"{'MOCK-CI' if is_mock else 'RUN'}-{date.today().isoformat()}",
        "date": date.today().isoformat(),
        "tier": "mock_ci" if is_mock else args.tier,
        "mock": is_mock,
        "provider": None if is_mock else (args.provider or "config-default"),
        "model": "scripted-test-oracle" if is_mock else (args.model or "config-default"),
        "config": args.config, "dataset": str(dataset_path),
        "summary": summary, "correlation": corr_report, "items": per_item_reports,
    }
    if is_mock:
        report["WARNING"] = ("SCRIPTED ORACLE OUTPUT - decided by a hand-written script, not a model. "
                             "Do NOT cite. Pipeline plumbing check only.")
    output_path.parent.mkdir(exist_ok=True)
    json.dump(report, open(output_path, "w"), indent=2)
    console.print(f"\n[green]Report saved:[/green] {output_path}")


if __name__ == "__main__":
    main()
