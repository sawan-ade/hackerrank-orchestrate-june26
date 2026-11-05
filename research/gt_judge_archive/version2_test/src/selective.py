"""
src/selective.py  (issue: new contribution --- risk-controlled selective judging)
==================================================================================
Redundancy-aware selective judging: turn a verdict + confidence into a
*selective* decision (accept / abstain) that carries a finite-sample risk
certificate which remains valid when the evaluators' errors are CORRELATED.

Why this module exists
----------------------
Selective LLM-judging methods such as SCOPE (Badshah et al., 2026) and
Trust-or-Escalate (Jung et al., 2025) calibrate an acceptance threshold on a
labelled set so that the error rate among *accepted* judgements is at most a
user level alpha, with high probability. Their finite-sample guarantee assumes
the calibration observations are exchangeable / i.i.d. Bernoulli (e.g. a
Clopper-Pearson upper bound). Kohli (2026) shows LLM judge panels violate that
assumption: judges make the same mistakes on the same items, so errors are
positively correlated and the panel carries far fewer than n independent votes.

Under positive correlation the empirical accepted-error rate has variance
inflated by the *design effect* D = 1 + (n-1) * rho (Kish, 1965), so an i.i.d.
upper confidence bound is anti-conservative: the deployed risk exceeds alpha
more often than the nominal delta. Replacing the nominal count n by the
effective count n_eff = n / D (equivalently, inflating the standard error by
sqrt(D)) restores the (1 - delta) guarantee. This is the same effective-sample-
size quantity Kohli uses to *diagnose* the panel; here we push it into the risk
bound to *fix* the guarantee.

This module is pure statistics --- no LLM calls --- so its behaviour is
verifiable offline (see scripts/validate_selective_risk.py and the unit tests).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

# One-sided normal quantiles z_{1-delta} for the common delta values, so the
# module has no scipy dependency. Falls back to an inverse-erf computation.
_Z_TABLE = {0.10: 1.2815515594, 0.05: 1.6448536270, 0.01: 2.3263478740}


def _z_one_sided(delta: float) -> float:
    """z such that P(N(0,1) > z) = delta."""
    if delta in _Z_TABLE:
        return _Z_TABLE[delta]
    # Acklam-free: use the relation z = sqrt(2) * erfinv(1 - 2*delta).
    return math.sqrt(2.0) * _erfinv(1.0 - 2.0 * delta)


def _erfinv(x: float) -> float:
    """Rational approximation of the inverse error function (Winitzki)."""
    a = 0.147
    ln = math.log(1.0 - x * x)
    t1 = 2.0 / (math.pi * a) + ln / 2.0
    return math.copysign(math.sqrt(math.sqrt(t1 * t1 - ln / a) - t1), x)


def design_effect(cluster_size: float, rho: float) -> float:
    """Kish cluster-sampling design effect D = 1 + (b - 1) * rho, where b is the
    average correlation-cluster size and rho the intra-cluster error
    correlation.

    Using the CLUSTER size (not the total sample size) keeps D bounded: errors
    are correlated within shared-bias clusters (e.g. items on which the base
    model fails together), but clusters are approximately independent. With
    rho = 0, or singleton clusters (b = 1), D = 1 (no inflation).
    """
    b = max(float(cluster_size), 1.0)
    rho = max(0.0, min(1.0, float(rho)))
    return 1.0 + (b - 1.0) * rho


def effective_count(n: int, rho: float, cluster_size: float = None) -> float:
    """Effective number of independent calibration observations
    n_eff = n / D, clipped to [1, n].

    cluster_size defaults to n (the global-equicorrelation special case, as in
    the within-panel §5 correction). For across-item calibration pass the
    average cluster size b so the design effect stays bounded.
    """
    if n <= 0:
        return 0.0
    b = n if cluster_size is None else cluster_size
    d = design_effect(b, rho)
    return float(min(max(n / d, 1.0), float(n)))


def error_rate_ucb(k: int, n: int, delta: float, rho: float = 0.0,
                   cluster_size: float = None) -> float:
    """One-sided upper confidence bound on the accepted-error rate.

    Uses a Wilson-style normal interval evaluated at the EFFECTIVE sample size
    n_eff = n / (1 + (b-1) rho), where b = cluster_size. With rho = 0 (or b = 1)
    this reduces to the ordinary i.i.d. Wilson upper bound; with rho > 0 the
    bound widens by ~sqrt(D), the correction needed under correlated errors.

    Args:
        k: number of errors among the n accepted calibration items.
        n: number of accepted calibration items.
        delta: allowed failure probability (bound holds w.p. >= 1 - delta).
        rho: average intra-cluster error correlation (0 = i.i.d. baseline).
        cluster_size: average correlation-cluster size b (default: n).
    Returns:
        Upper bound in [0, 1]. Returns 1.0 for an empty accepted set.
    """
    if n <= 0:
        return 1.0
    n_eff = effective_count(n, rho, cluster_size)
    p_hat = k / n
    z = _z_one_sided(delta)
    # Wilson upper bound at the effective sample size.
    z2 = z * z
    denom = 1.0 + z2 / n_eff
    center = p_hat + z2 / (2.0 * n_eff)
    half = z * math.sqrt(p_hat * (1.0 - p_hat) / n_eff + z2 / (4.0 * n_eff * n_eff))
    return float(min(1.0, (center + half) / denom))


@dataclass
class SelectiveCertificate:
    """The result of calibrating a selective judging threshold."""
    threshold: float          # accept an item iff confidence >= threshold
    alpha: float              # target accepted-error rate
    delta: float              # allowed failure probability of the bound
    rho: float                # correlation used in the design-effect correction
    coverage: float           # fraction of calibration items accepted
    empirical_error: float    # accepted-error rate on the calibration set
    risk_ucb: float           # (1 - delta) upper bound on the accepted error
    n_accepted: int
    n_effective: float
    corrected: bool           # whether the design-effect correction was applied

    def certifies(self) -> bool:
        """True iff the (1 - delta) upper bound respects the target risk."""
        return self.risk_ucb <= self.alpha + 1e-12


def calibrate_threshold(
    confidences: Sequence[float],
    errors: Sequence[int],
    alpha: float = 0.10,
    delta: float = 0.10,
    rho: float = 0.0,
    cluster_size: float = None,
    correct: bool = True,
    n_grid: int = 40,
) -> SelectiveCertificate:
    """Pick the acceptance threshold that maximises coverage subject to a
    (1 - delta) guarantee that the accepted-error rate is <= alpha.

    Candidate thresholds are a FIXED grid of confidence quantiles (size
    n_grid). Because we search the grid and keep the most permissive
    certifying threshold, we Bonferroni-correct the per-threshold failure
    probability to delta / n_grid so the selection is simultaneously valid
    (this makes the i.i.d. baseline valid at rho = 0). Each candidate's error
    rate is bounded by the design-effect-corrected UCB.

    Set correct=False to reproduce the i.i.d. behaviour of prior selective
    judges (design effect ignored); this is the baseline that fails under
    correlation. cluster_size (b) is the average correlation-cluster size used
    in the design-effect correction.
    """
    conf = np.asarray(confidences, dtype=float)
    err = np.asarray(errors, dtype=int)
    if conf.size == 0:
        return SelectiveCertificate(1.01, alpha, delta, rho, 0.0, 0.0, 1.0, 0, 0.0, correct)

    rho_used = rho if correct else 0.0
    # Fixed quantile grid of candidate thresholds (high -> low), Bonferroni delta.
    qs = np.linspace(0.0, 1.0, n_grid)
    candidates = np.unique(np.quantile(conf, qs))[::-1]
    delta_bonf = delta / max(len(candidates), 1)

    best: Optional[SelectiveCertificate] = None
    total = conf.size
    for tau in candidates:
        mask = conf >= tau
        n_acc = int(mask.sum())
        if n_acc == 0:
            continue
        k = int(err[mask].sum())
        ucb = error_rate_ucb(k, n_acc, delta_bonf, rho_used, cluster_size)
        if ucb <= alpha + 1e-12:
            best = SelectiveCertificate(
                threshold=float(tau),
                alpha=alpha, delta=delta, rho=rho_used,
                coverage=n_acc / total,
                empirical_error=k / n_acc,
                risk_ucb=ucb,
                n_accepted=n_acc,
                n_effective=effective_count(n_acc, rho_used, cluster_size),
                corrected=correct,
            )
    if best is None:
        return SelectiveCertificate(
            threshold=float(candidates[0]) + 1e-6,
            alpha=alpha, delta=delta, rho=rho_used,
            coverage=0.0, empirical_error=0.0, risk_ucb=0.0,
            n_accepted=0, n_effective=0.0, corrected=correct,
        )
    return best
