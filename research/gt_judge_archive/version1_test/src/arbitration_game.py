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

# Numerically safe logit / sigmoid for the log-odds opinion pool (§5).
_EPS = 1e-6


def _logit(p: float) -> float:
    p = min(1.0 - _EPS, max(_EPS, float(p)))
    return math.log(p / (1.0 - p))


def _sigmoid(x: float) -> float:
    # Overflow-safe.
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


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
        correlation_correction: bool = True,
        prior_rho: float = 0.6,
    ):
        self.C_H = human_review_cost
        self.beta = beta_effort_scale
        self.alpha_debate_influence = alpha_debate_influence
        self.alpha_d = alpha_d
        # Correlated-error correction (issue §5). When no empirical correlation
        # matrix is supplied for a single item, we assume equicorrelation with
        # prior_rho (>0 because evaluators share a base model). A batch runner
        # can pass a measured Σ via run(correlation_matrix=...).
        self.correlation_correction = correlation_correction
        self.prior_rho = prior_rho

    def run(
        self,
        debate_results: dict[str, DebateResult],
        calibration_results: list[CalibrationResult],
        correlation_matrix=None,
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

        # Compute aggregated confidence, with correlated-error correction (§5).
        verdict_y = self._verdict_to_y(best_verdict)

        # --- Naive (independence-assuming) opinion pool -------------------
        # A logarithmic opinion pool treats each of the n evaluators as an
        # INDEPENDENT piece of evidence and adds their log-odds increments on
        # top of the debate prior. This is exactly the assumption Kohli et al.
        # (2026) show is violated by panels sharing a base model: it counts n
        # correlated judges as n independent votes and becomes overconfident.
        #   L_naive = L_prior + n * (mean_logit - L_prior)
        L_prior = _logit(debate_prior)
        logits = [_logit(cal.reported_confidence) for cal in calibration_results]
        L_bar_uniform = sum(logits) / n
        L_naive = L_prior + n * (L_bar_uniform - L_prior)
        p_agg_naive = _sigmoid(L_naive)
        confidence_uncorrected = 1.0 - abs(verdict_y - p_agg_naive)

        n_eff = float(n)
        rho_hat = 0.0
        p_corrected = p_agg_naive

        if self.correlation_correction and n >= 2:
            from src.correlation import (
                effective_n, gls_weights, equicorrelation, shrink_to_identity,
            )
            if correlation_matrix is not None:
                sigma = shrink_to_identity(correlation_matrix, lam=0.1)
            else:
                sigma = equicorrelation(n, self.prior_rho)

            n_eff = effective_n(sigma)
            # GLS (min-variance) weights handle HETEROGENEOUS correlation/variance
            # across evaluators; for equicorrelation they are uniform.
            w_gls = gls_weights(sigma)
            L_bar_gls = float(sum(w_gls[i] * logits[i] for i in range(n)))
            # --- Corrected pool: count only n_eff INDEPENDENT judges ---------
            #   L_corr = L_prior + n_eff * (weighted_mean_logit - L_prior)
            # ρ=0  -> n_eff=n   -> recovers the full independent pool.
            # ρ=1  -> n_eff=1   -> counts the redundant panel as a single judge.
            L_corr = L_prior + n_eff * (L_bar_gls - L_prior)
            p_corrected = _sigmoid(L_corr)
            # Back out the implied mean pairwise correlation from n_eff:
            #   n_eff = n / (1 + (n-1) rho)  =>  rho = (n/n_eff - 1) / (n-1)
            rho_hat = (n / n_eff - 1.0) / (n - 1) if n_eff > 0 else 0.0

        confidence = 1.0 - abs(verdict_y - p_corrected)

        return ArbitrationResult(
            verdict=best_verdict,
            nash_product=best_product if best_product > -float("inf") else 0.0,
            weights=weights,
            confidence=confidence,
            n_effective=n_eff,
            effective_correlation=max(0.0, min(1.0, rho_hat)),
            confidence_uncorrected=confidence_uncorrected,
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
