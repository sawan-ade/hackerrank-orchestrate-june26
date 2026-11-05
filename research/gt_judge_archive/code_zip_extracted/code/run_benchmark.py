"""
GT-Judge Benchmark Runner
==========================
Evaluates the GT-Judge pipeline on a sample benchmark dataset.
Measures accuracy, position bias (flip rate), and calibration quality.

Usage:
    cd A/code
    python run_benchmark.py
    
    # Or run in mock mode (no API key required):
    python run_benchmark.py --mock
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.table import Table

from src.gt_judge import GTJudge
from src.models import Verdict, AgentMove


def create_mock_llm():
    """Create a mock LLMClient that returns realistic structured responses for the benchmark."""
    mock_llm = MagicMock()
    
    # Track calls to return different things depending on the system/user prompts
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
                        "argument": "Defending A: The logic holds perfectly; the alternative is suboptimal.",
                        "target_claim_id": 1
                    }, 100
                else:
                    return {
                        "action": "defend",
                        "argument": "Defending B: While verbose, more details help explanation.",
                        "target_claim_id": 1
                    }, 100
            
            # Regular claim/clarify turn
            is_ans_a = any(kw in user_prompt for kw in [
                "dynamic programming", "1/15", "democratized literacy", 
                "successfully landed", "equipping students with foundational skills"
            ])
            
            if is_ans_a:
                return {
                    "action": "claim",
                    "argument": "Claim A: This answer is mathematically and logically sound, concise, and direct.",
                    "target_claim_id": None
                }, 120
            else:
                return {
                    "action": "claim",
                    "argument": "Claim B: This answer contains a lot of detailed background information and tries to explain everything.",
                    "target_claim_id": None
                }, 150
                
        elif "CHALLENGER" in system_prompt:
            call_counts["challenger"] += 1
            is_ans_a = any(kw in user_prompt for kw in [
                "dynamic programming", "1/15", "democratized literacy", 
                "successfully landed", "equipping students with foundational skills"
            ])
            
            if is_ans_a:
                # Concede to high-quality Answer A
                return {
                    "action": "concede",
                    "argument": "Concede: Proposer's claim is mathematically correct and clear.",
                    "target_claim_id": None
                }, 80
            else:
                # Attack low-quality Answer B
                return {
                    "action": "attack",
                    "argument": "Attack B: The answer is excessively verbose and uses inefficient recursion/bad assumptions.",
                    "target_claim_id": 1
                }, 110
                
        elif "VALIDITY" in system_prompt:
            call_counts["validity"] += 1
            is_ans_a = "Claim A" in user_prompt
            if is_ans_a:
                return {
                    "attack_severity": 0.1,
                    "defense_success": True,
                    "reasoning": "Impeccable defense of a correct claim."
                }, 50
            else:
                return {
                    "attack_severity": 0.9,
                    "defense_success": False,
                    "reasoning": "Attack exposes fundamental verbosity and inefficiency."
                }, 50
            
        elif "calibrated evaluator" in system_prompt:
            call_counts["calibration"] += 1
            # Parse scores from prompt
            score_a = float(user_prompt.split("- Answer A debate score: ")[1].split("\n")[0])
            score_b = float(user_prompt.split("- Answer B debate score: ")[1].split("\n")[0])
            
            # Calibration evaluator should report high confidence in the superior answer.
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
    parser = argparse.ArgumentParser(description="GT-Judge Benchmark Evaluator")
    parser.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Path to game configuration file",
    )
    parser.add_argument(
        "--dataset",
        default="configs/sample_benchmark.json",
        help="Path to benchmark dataset file",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in offline mock mode (no OpenAI API calls)",
    )
    args = parser.parse_args()

    console = Console()
    console.print("[bold cyan]============================================================[/bold cyan]")
    console.print("[bold cyan]  GT-Judge Phase 3 — Benchmark Evaluation Suite[/bold cyan]")
    console.print("[bold cyan]============================================================[/bold cyan]")
    console.print()

    # Load dataset
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        console.print(f"[red]Error: Dataset not found at {dataset_path}[/red]")
        sys.exit(1)
        
    with open(dataset_path) as f:
        data = json.load(f)

    # Instantiate Judge
    if args.mock:
        console.print("[yellow][Mock Mode] Running with mocked LLM responses.[/yellow]")
        # Inject dummy API key so the OpenAI constructor doesn't raise
        os.environ["OPENAI_API_KEY"] = "sk-test-dummy-key-for-benchmark-mock"
        mock_llm = create_mock_llm()
        judge = GTJudge.from_config(args.config)
        judge.llm = mock_llm
        judge.debate_game.llm = mock_llm
        judge.calibration_game.llm = mock_llm
    else:
        # Check API Key
        if not os.getenv("OPENAI_API_KEY"):
            console.print("[red]Error: OPENAI_API_KEY environment variable is not set.[/red]")
            console.print("Please set the key or run with [bold]--mock[/bold] for offline validation.")
            sys.exit(1)
        judge = GTJudge.from_config(args.config)

    console.print(f"[green]Loaded config:[/green] {args.config}")
    console.print(f"[green]Loaded dataset:[/green] {dataset_path} ({len(data)} items)")
    console.print()

    table = Table(title="Evaluation Runs (Symmetric Order Testing)")
    table.add_column("ID", justify="center", style="dim")
    table.add_column("Category", style="cyan")
    table.add_column("Human Pref", justify="center", style="bold green")
    table.add_column("Verdict (A, B)", justify="center")
    table.add_column("Verdict (B, A)", justify="center")
    table.add_column("Match?", justify="center")
    table.add_column("Flip?", justify="center")
    table.add_column("Brier Reward", justify="center")

    results_log = []
    correct_count = 0
    flip_count = 0
    brier_sum = 0.0
    total_runs = 0

    with console.status("[bold green]Running evaluation...") as status:
        for idx, item in enumerate(data):
            q_id = item.get("id", idx + 1)
            category = item.get("category", "General")
            question = item["question"]
            ans_a = item["answer_a"]
            ans_b = item["answer_b"]
            human_pref = item["human_preference"] # "A", "B", or "Tie"

            # 1. Evaluate original order: (Answer A, Answer B)
            res_forward = judge.evaluate(question, ans_a, ans_b, ground_truth=human_pref)
            verdict_forward = res_forward.verdict

            # 2. Evaluate swapped order: (Answer B, Answer A)
            # When swapping, the inputs are swapped. So the judge's verdict 'A_wins' means ans_b wins.
            res_backward = judge.evaluate(question, ans_b, ans_a, ground_truth=human_pref)
            verdict_backward = res_backward.verdict
            
            # Map backward verdict back to original labels to check position bias
            # If backward says 'A_wins', it means the first arg (ans_b) wins, i.e., 'B_wins' in original terms.
            mapped_backward = Verdict.TIE
            if verdict_backward == Verdict.A_WINS:
                mapped_backward = Verdict.B_WINS
            elif verdict_backward == Verdict.B_WINS:
                mapped_backward = Verdict.A_WINS

            # Check flip (Position Bias)
            flipped = (verdict_forward != mapped_backward)
            if flipped:
                flip_count += 1
                flip_str = "[red]Yes[/red]"
            else:
                flip_str = "[green]No[/green]"

            # Check match with Human Preference
            # Map human preference ('A' -> A_wins, 'B' -> B_wins, 'Tie' -> Tie)
            mapped_human = Verdict.TIE
            if human_pref == "A":
                mapped_human = Verdict.A_WINS
            elif human_pref == "B":
                mapped_human = Verdict.B_WINS

            matches_human = (verdict_forward == mapped_human)
            if matches_human:
                correct_count += 1
                match_str = "[green]Pass[/green]"
            else:
                match_str = "[red]Fail[/red]"

            # Calculate Brier score for forward run
            avg_brier = sum(c.calibration_score for c in res_forward.calibration_results) / len(res_forward.calibration_results)
            brier_sum += avg_brier

            # Add to table
            table.add_row(
                str(q_id),
                category,
                human_pref,
                verdict_forward.value,
                verdict_backward.value,
                match_str,
                flip_str,
                f"{avg_brier:.3f}"
            )

            # Log details
            results_log.append({
                "id": q_id,
                "category": category,
                "forward": {
                    "verdict": verdict_forward.value,
                    "confidence": res_forward.confidence,
                    "tokens": res_forward.total_tokens
                },
                "backward": {
                    "verdict": verdict_backward.value,
                    "confidence": res_backward.confidence,
                    "tokens": res_backward.total_tokens
                },
                "matches_human": matches_human,
                "position_flip": flipped,
                "calibration_brier": avg_brier
            })
            total_runs += 1

    console.print(table)
    console.print()

    # Calculate final aggregate statistics
    accuracy = (correct_count / total_runs) * 100 if total_runs > 0 else 0.0
    flip_rate = (flip_count / total_runs) * 100 if total_runs > 0 else 0.0
    mean_brier = brier_sum / total_runs if total_runs > 0 else 0.0

    console.print("[bold]Summary Statistics:[/bold]")
    console.print(f"  - [bold]Accuracy (vs. Human Labels):[/bold] {accuracy:.1f}% ({correct_count}/{total_runs})")
    console.print(f"  - [bold]Position Flip Rate (Bias):[/bold] {flip_rate:.1f}% ({flip_count}/{total_runs})")
    console.print(f"  - [bold]Mean Brier Calibration Reward (1-Brier):[/bold] {mean_brier:.3f}")
    console.print()

    # Save outputs
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / "benchmark_results.json"
    
    report_data = {
        "config": args.config,
        "mock": args.mock,
        "summary": {
            "total_instances": total_runs,
            "accuracy_pct": accuracy,
            "flip_rate_pct": flip_rate,
            "mean_brier_score": mean_brier
        },
        "results": results_log
    }
    
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
        
    console.print(f"[green]Report saved successfully to:[/green] {report_path}")


if __name__ == "__main__":
    main()
