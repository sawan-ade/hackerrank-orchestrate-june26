"""
GT-Judge Pipeline
==================
The main orchestrator implementing the full GT-Judge evaluation function:
    GT-Judge(Q, A, B) = NBS(Calibrate(Debate(Q, A, B)))   [Definition 6]

Sequential pipeline:
    Game 1 (Debate) → Game 2 (Calibration) → Game 3 (Arbitration) → Verdict
"""

from __future__ import annotations

import yaml
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from src.models import EvaluationInput, EvaluationOutput, Verdict
from src.llm_client import LLMClient
from src.debate_game import DebateGame
from src.calibration_game import CalibrationGame
from src.arbitration_game import ArbitrationGame


class GTJudge:
    """
    The GT-Judge: a game-theoretic multi-agent LLM-as-a-judge.
    
    Usage:
        judge = GTJudge.from_config("configs/default.yaml")
        result = judge.evaluate(question, answer_a, answer_b)
    """

    # Recognised ablation modes (issue §3). None = full pipeline.
    ABLATIONS = (None, "no_debate", "no_calibration", "no_arbitration")

    def __init__(
        self,
        llm: LLMClient,
        debate_game: DebateGame,
        calibration_game: CalibrationGame,
        arbitration_game: ArbitrationGame,
        ablation: Optional[str] = None,
    ):
        if ablation not in self.ABLATIONS:
            raise ValueError(
                f"Unknown ablation {ablation!r}. Options: {self.ABLATIONS}"
            )
        self.llm = llm
        self.debate_game = debate_game
        self.calibration_game = calibration_game
        self.arbitration_game = arbitration_game
        self.ablation = ablation

    @classmethod
    def from_config(cls, config_path: str, overrides: Optional[dict] = None) -> "GTJudge":
        """
        Construct a GTJudge from a YAML config file.

        Args:
            config_path: Path to the YAML config (e.g. configs/default.yaml).
            overrides: Optional dict of ad-hoc overrides applied on top of the
                file, e.g. {"provider": "google", "model": "gemini-1.5-flash",
                "api_key": "...", "ablation": "no_debate"}. Used by the CLI
                --provider/--model/--api-key flags and the ablation harness.
        """
        with open(config_path) as f:
            cfg = yaml.safe_load(f)

        overrides = overrides or {}
        model_cfg = cfg.get("model", {})
        provider = overrides.get("provider") or model_cfg.get("provider", "openai")
        model_name = overrides.get("model") or model_cfg.get("evaluator_model", "gpt-4o-mini")
        api_key = overrides.get("api_key")  # None -> falls back to env var in the client

        llm = LLMClient(
            provider=provider,
            model=model_name,
            temperature=model_cfg.get("temperature_debate", 0.7),
            max_tokens=model_cfg.get("max_tokens", 1024),
            api_key=api_key,
        )

        g1_cfg = cfg.get("game1_debate", {})
        debate = DebateGame(
            llm=llm,
            max_rounds=g1_cfg.get("rounds", 3),
            lambda_cost=g1_cfg.get("lambda_token_cost", 0.001),
        )

        g2_cfg = cfg.get("game2_calibration", {})
        calibration = CalibrationGame(
            llm=LLMClient(
                provider=provider,
                model=model_name,
                temperature=model_cfg.get("temperature_calibration", 0.0),
                max_tokens=model_cfg.get("max_tokens", 1024),
                api_key=api_key,
            ),
            n_evaluators=cfg.get("pipeline", {}).get("evaluator_count", 2),
            ground_truth_mode=g2_cfg.get("ground_truth_mode", "consensus_proxy"),
        )

        g3_cfg = cfg.get("game3_arbitration", {})
        arbitration = ArbitrationGame(
            human_review_cost=g3_cfg.get("human_review_cost", 10.0),
            beta_effort_scale=g3_cfg.get("beta_effort_scale", 0.1),
            alpha_debate_influence=g3_cfg.get("alpha_debate_influence", 0.3),
            alpha_d=g3_cfg.get("alpha_d", 0.1),
            correlation_correction=g3_cfg.get("correlation_correction", True),
            prior_rho=g3_cfg.get("prior_rho", 0.6),
        )

        return cls(llm=llm, debate_game=debate, calibration_game=calibration,
                   arbitration_game=arbitration,
                   ablation=overrides.get("ablation"))

    def evaluate(
        self,
        question: str,
        answer_a: str,
        answer_b: str,
        ground_truth: Optional[str] = None,
    ) -> EvaluationOutput:
        """
        Run the full GT-Judge pipeline on one evaluation instance.
        
        GT-Judge(Q, A, B) = NBS(Calibrate(Debate(Q, A, B)))
        
        Args:
            question: The evaluation question/instruction.
            answer_a: First candidate answer.
            answer_b: Second candidate answer.
            ground_truth: Optional human label ('A', 'B', 'Tie') for benchmark mode.
            
        Returns:
            EvaluationOutput with the final verdict, confidence, and all game results.
        """
        # Validate inputs via EvaluationInput schema (C-3)
        inputs = EvaluationInput(
            question=question,
            answer_a=answer_a,
            answer_b=answer_b,
            ground_truth=ground_truth,
        )
        question = inputs.question
        answer_a = inputs.answer_a
        answer_b = inputs.answer_b
        ground_truth = inputs.ground_truth

        # =====================================================================
        # Stage 1: Debate Game (Game 1)
        # Run debate for BOTH answers to ensure position invariance (Prop 1')
        # Ablation "no_debate": skip Game 1 entirely and feed neutral debate
        # results downstream, isolating the debate stage's contribution (§3).
        # =====================================================================
        if self.ablation == "no_debate":
            debate_a = self._neutral_debate("A")
            debate_b = self._neutral_debate("B")
        else:
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_a = executor.submit(self.debate_game.run, question, answer_a, "A")
                future_b = executor.submit(self.debate_game.run, question, answer_b, "B")
                debate_a = future_a.result()
                debate_b = future_b.result()
        debate_results = {"A": debate_a, "B": debate_b}

        # =====================================================================
        # Stage 2: Calibration Game (Game 2)
        # Each evaluator reports calibrated confidence p̂ ∈ [0,1]
        # Ablation "no_calibration": skip the confidence-elicitation game and
        # substitute flat, uninformative confidences (0.5), isolating Game 2 (§3).
        # =====================================================================
        if self.ablation == "no_calibration":
            calibration_results = self._flat_calibration()
        else:
            calibration_results = self.calibration_game.run(
                question=question,
                answer_a=answer_a,
                answer_b=answer_b,
                debate_a=debate_a,
                debate_b=debate_b,
                ground_truth=ground_truth,
            )

        # =====================================================================
        # Stage 3: Arbitration Game (Game 3)
        # Resolve disagreement via Nash Bargaining.
        # Ablation "no_arbitration": skip Nash bargaining and fall back to a
        # simple decision rule (argmax debate score, tie-break on mean
        # confidence), isolating Game 3's contribution (§3).
        # =====================================================================
        if self.ablation == "no_arbitration":
            arbitration_result = self._simple_arbitration(
                debate_results, calibration_results
            )
            total_tokens = (
                debate_a.total_proposer_tokens + debate_a.total_challenger_tokens +
                debate_b.total_proposer_tokens + debate_b.total_challenger_tokens
            )
            justification = self._generate_justification(
                debate_results, calibration_results, arbitration_result
            )
            return EvaluationOutput(
                verdict=arbitration_result.verdict,
                confidence=arbitration_result.confidence,
                debate_results=debate_results,
                calibration_results=calibration_results,
                arbitration_result=arbitration_result,
                total_tokens=total_tokens,
                justification=justification,
            )

        # Implement iterative fixed point convergence loop for consensus proxy (B-4)
        MAX_CONSENSUS_ITERS = 5
        prev_verdict = None
        arbitration_result = None

        for iteration in range(MAX_CONSENSUS_ITERS):
            arbitration_result = self.arbitration_game.run(
                debate_results=debate_results,
                calibration_results=calibration_results,
            )

            if arbitration_result.verdict == prev_verdict:
                break
                
            prev_verdict = arbitration_result.verdict

            if ground_truth is not None:
                # Benchmark mode: use human label
                gt_y = {"A": 1.0, "B": 0.0, "Tie": 0.5}.get(ground_truth, 0.5)
            else:
                # Deployment mode: consensus proxy ỹ from the verdict
                gt_y = ArbitrationGame._verdict_to_y(arbitration_result.verdict)

            # Compute Brier scores with resolved ground truth
            calibration_results = self.calibration_game.compute_brier_scores(
                calibration_results, gt_y
            )

            if ground_truth is not None:
                # In benchmark mode, ground truth is static; run arbitration one more time and break
                arbitration_result = self.arbitration_game.run(
                    debate_results=debate_results,
                    calibration_results=calibration_results,
                )
                break

        # =====================================================================
        # Compose output
        # =====================================================================
        total_tokens = (
            debate_a.total_proposer_tokens + debate_a.total_challenger_tokens +
            debate_b.total_proposer_tokens + debate_b.total_challenger_tokens
        )

        justification = self._generate_justification(
            debate_results, calibration_results, arbitration_result
        )

        return EvaluationOutput(
            verdict=arbitration_result.verdict,
            confidence=arbitration_result.confidence,
            debate_results=debate_results,
            calibration_results=calibration_results,
            arbitration_result=arbitration_result,
            total_tokens=total_tokens,
            justification=justification,
        )

    # ------------------------------------------------------------------
    # Ablation helpers (issue §3). Each isolates one game's contribution.
    # ------------------------------------------------------------------
    @staticmethod
    def _neutral_debate(label: str) -> "DebateResult":
        """A debate result carrying no signal (score 0, no claims/attacks, no
        tokens). Used by the 'no_debate' ablation so the debate prior collapses
        to 0.5 and the verdict rests entirely on calibration + arbitration."""
        from src.models import DebateResult
        return DebateResult(
            answer_label=label,
            debate_score=0.0,
            surviving_claims=0,
            successful_attacks=0,
            total_proposer_tokens=0,
            total_challenger_tokens=0,
            transcript=[],
        )

    def _flat_calibration(self) -> list:
        """Uninformative confidences (0.5) for each evaluator. Used by the
        'no_calibration' ablation so no calibrated confidence signal enters
        arbitration."""
        from src.models import CalibrationResult
        n = getattr(self.calibration_game, "n_evaluators", 2)
        return [
            CalibrationResult(evaluator_id=i, reported_confidence=0.5,
                              calibration_score=0.0)
            for i in range(n)
        ]

    def _simple_arbitration(self, debate_results: dict, calibration_results: list):
        """Non-strategic fallback used by the 'no_arbitration' ablation.

        Verdict = argmax debate score; if debate scores tie, fall back to the
        mean reported confidence (>0.5 -> A, <0.5 -> B, ==0.5 -> Tie). Confidence
        is the mean reported confidence mapped to the chosen side. No Nash
        bargaining, no correlation correction.
        """
        from src.models import ArbitrationResult, Verdict
        score_a = debate_results["A"].debate_score
        score_b = debate_results["B"].debate_score
        mean_conf = (
            sum(c.reported_confidence for c in calibration_results)
            / max(len(calibration_results), 1)
        )
        if abs(score_a - score_b) > 1e-9:
            verdict = Verdict.A_WINS if score_a > score_b else Verdict.B_WINS
        else:
            if mean_conf > 0.5 + 1e-9:
                verdict = Verdict.A_WINS
            elif mean_conf < 0.5 - 1e-9:
                verdict = Verdict.B_WINS
            else:
                verdict = Verdict.TIE
        verdict_y = ArbitrationGame._verdict_to_y(verdict)
        confidence = 1.0 - abs(verdict_y - mean_conf)
        return ArbitrationResult(
            verdict=verdict,
            nash_product=0.0,
            weights={i: 1.0 / max(len(calibration_results), 1)
                     for i in range(len(calibration_results))},
            confidence=confidence,
            n_effective=float(len(calibration_results)),
            effective_correlation=0.0,
            confidence_uncorrected=confidence,
        )

    def _generate_justification(
        self,
        debate_results: dict,
        calibration_results: list,
        arbitration_result,
    ) -> str:
        """Generate a human-readable justification for the verdict."""
        lines = [f"GT-Judge Verdict: {arbitration_result.verdict.value}"]
        lines.append(f"Confidence: {arbitration_result.confidence:.3f}")
        lines.append("")
        lines.append("--- Debate Scores ---")
        for label, dr in debate_results.items():
            lines.append(f"  Answer {label}: score={dr.debate_score:.3f}, "
                         f"surviving_claims={dr.surviving_claims}, "
                         f"successful_attacks={dr.successful_attacks}")
        lines.append("")
        lines.append("--- Calibration ---")
        for cal in calibration_results:
            lines.append(f"  Evaluator {cal.evaluator_id}: p_hat={cal.reported_confidence:.3f}, "
                         f"Brier={cal.calibration_score:.3f}")
        lines.append("")
        lines.append("--- Bargaining Weights ---")
        for eid, w in arbitration_result.weights.items():
            lines.append(f"  Evaluator {eid}: w={w:.3f}")
        return "\n".join(lines)
