"""
Game 3: Consensus Arbitration Game
=====================================
Implements Nash Bargaining Solution (G₃ = ⟨N, V, d, U⟩).
Ref: Phase 1 Formalization, Section 4.

When evaluators disagree, this game resolves the dispute by maximizing
the weighted Nash product:
    v* = argmax_{v ∈ V} ∏ᵢ (Uᵢ(v) - dᵢ)^wᵢ   [Eq. 24]

Bargaining weights wᵢ are computed from debate + calibration scores [Eq. 21].
Disagreement point dᵢ = -C_H - βᵢ · effortᵢ                       [Eq. 20].
"""

from __future__ import annotations

import math
from typing import Optional

from src.models import (
    ArbitrationResult, CalibrationResult, DebateResult, Verdict,
)


class ArbitrationGame:
    """
    Resolves evaluator disagreement via Nash Bargaining.
    
    The bargaining outcome is the verdict that maximizes the weighted
    Nash product over the feasible utility set.
    """

    def __init__(
        self,
        human_review_cost: float = 10.0,
        beta_effort_scale: float = 0.1,
        alpha_debate_influence: float = 0.3,
        alpha_d: float = 0.1,
    ):
        self.C_H = human_review_cost
        self.beta = beta_effort_scale
        self.alpha_debate_influence = alpha_debate_influence
        self.alpha_d = alpha_d

    def run(
        self,
        debate_results: dict[str, DebateResult],
        calibration_results: list[CalibrationResult],
    ) -> ArbitrationResult:
        """
        Compute the Nash Bargaining Solution over the verdict space.
        
        Args:
            debate_results: Dict with keys "A" and "B", each a DebateResult.
            calibration_results: List of CalibrationResult with calibration scores.
            
        Returns:
            ArbitrationResult with the final verdict.
        """
        n = len(calibration_results)

        # Step 1: Compute bargaining weights wᵢ [Eq. 21]
        weights = self._compute_weights(debate_results, calibration_results)

        # Step 2: Compute disagreement points dᵢ [Eq. 20]
        disagreement = self._compute_disagreement_points(debate_results, calibration_results)

        # Step 3: Compute utility of each verdict for each evaluator
        # Incorporate Debate Prior Term [Fix A-1]
        score_a = debate_results["A"].debate_score
        score_b = debate_results["B"].debate_score
        delta_debate = score_a - score_b
        # Use sigmoid to map debate score difference to a prior probability in [0, 1]
        debate_prior = 1.0 / (1.0 + math.exp(-delta_debate))

        verdict_utilities = {}
        for verdict in Verdict:
            verdict_y = self._verdict_to_y(verdict)
            utilities = []
            for cal in calibration_results:
                # Evaluator's utility for this verdict: alignment with their belief
                alignment = 1.0 - abs(verdict_y - cal.reported_confidence)
                # Debate prior alignment
                debate_alignment = 1.0 - abs(verdict_y - debate_prior)
                # Plus their calibration quality bonus
                utility = alignment + 0.5 * cal.calibration_score + self.alpha_debate_influence * debate_alignment
                utilities.append(utility)
            verdict_utilities[verdict] = utilities

        # Step 4: Maximize weighted Nash product [Eq. 24]
        # v* = argmax_{v} ∏ᵢ (Uᵢ(v) - dᵢ)^wᵢ
        best_verdict = Verdict.TIE
        best_product = -float("inf")

        for verdict, utilities in verdict_utilities.items():
            nash_product = 0.0  # We work in log space for numerical stability
            feasible = True

            for i, (u_i, d_i) in enumerate(zip(utilities, disagreement)):
                surplus = u_i - d_i
                if surplus <= 0:
                    feasible = False
                    break
                w_i = weights.get(i, 1.0 / n)
                nash_product += w_i * math.log(surplus)

            if feasible and nash_product > best_product:
                best_product = nash_product
                best_verdict = verdict

        # Compute aggregated confidence
        verdict_y = self._verdict_to_y(best_verdict)
        weighted_confidence = sum(
            weights.get(i, 0) * cal.reported_confidence
            for i, cal in enumerate(calibration_results)
        )
        # Confidence = how strongly the weighted consensus points toward the verdict
        confidence = 1.0 - abs(verdict_y - weighted_confidence)

        return ArbitrationResult(
            verdict=best_verdict,
            nash_product=best_product if best_product > -float("inf") else 0.0,
            weights=weights,
            confidence=confidence,
        )

    def _compute_weights(
        self,
        debate_results: dict[str, DebateResult],
        calibration_results: list[CalibrationResult],
    ) -> dict[int, float]:
        """
        Compute bargaining weights wᵢ [Eq. 21]:
        wᵢ = DebateScore(i) · CalibrationScore(i) / Σⱼ ...
        
        Since our debate is answer-level (not evaluator-level), we assign
        debate contribution proportionally by token usage.
        """
        n = len(calibration_results)
        total_debate_effort = sum(
            dr.total_proposer_tokens + dr.total_challenger_tokens
            for dr in debate_results.values()
        )

        raw_weights = []
        for i, cal in enumerate(calibration_results):
            # Debate contribution proxy: split evenly among evaluators
            debate_contribution = max(0.1, sum(
                dr.debate_score for dr in debate_results.values()
            ) / n)
            cal_score = max(0.01, cal.calibration_score)
            raw_weights.append(abs(debate_contribution) * cal_score)

        # Normalize
        total = sum(raw_weights) or 1.0
        return {i: w / total for i, w in enumerate(raw_weights)}

    def _compute_disagreement_points(
        self,
        debate_results: dict[str, DebateResult],
        calibration_results: list[CalibrationResult],
    ) -> list[float]:
        """
        Compute dᵢ = -C_H - β · effortᵢ  [Eq. 20]
        Effort is measured by tokens consumed during the debate.
        """
        total_tokens = sum(
            dr.total_proposer_tokens + dr.total_challenger_tokens
            for dr in debate_results.values()
        )
        n = len(calibration_results)
        per_evaluator_effort = total_tokens / max(n, 1)

        # Scale disagreement point to be on the same scale as utilities [Fix B-3]
        return [
            -self.alpha_d - self.beta * (per_evaluator_effort / 1000.0)
            for _ in calibration_results
        ]

    @staticmethod
    def _verdict_to_y(verdict: Verdict) -> float:
        """Convert verdict to the ground truth proxy ỹ [Fix 4, Eq. 10']."""
        if verdict == Verdict.A_WINS:
            return 1.0
        elif verdict == Verdict.B_WINS:
            return 0.0
        else:
            return 0.5
