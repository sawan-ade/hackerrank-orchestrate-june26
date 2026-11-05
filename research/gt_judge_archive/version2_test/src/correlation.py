"""
Correlated-Error Correction (issue §5)
======================================
Multiple LLM evaluators that share a base model have *correlated* errors. A
panel of n such judges therefore behaves like fewer than n independent judges:
consensus among them overstates confidence, and a correlated bloc can dominate
arbitration. Kohli et al. (2026) quantify exactly this failure in nine-judge
panels. GT-Judge's Discussion previously only gestured at "correlated priors"
via persona diversity; this module formalizes, implements, and (on synthetic
ensembles) validates a correction.

Formalization
-------------
Let s_i be evaluator i's signal (here: reported confidence deviation from the
panel view) with correlation matrix Sigma (unit diagonal). Two quantities:

  Effective evaluator count (Definition, §5):
      n_eff(Sigma) = 1^T Sigma^{-1} 1
  For the equicorrelation case Sigma = (1-rho)I + rho*J this reduces to
      n_eff = n / (1 + (n-1) rho),
  so n_eff = n when rho = 0 (independent) and n_eff -> 1 as rho -> 1 (fully
  redundant). This is the deflated "effective sample size."

  Correlation-aware combination weights (Bates & Granger, 1969; GLS):
      w* = Sigma^{-1} 1 / (1^T Sigma^{-1} 1)
  These are the minimum-variance weights for combining correlated estimators;
  perfectly correlated evaluators share a single evaluator's worth of weight.

Correction applied in arbitration (see arbitration_game.py):
  The aggregate confidence is shrunk toward the (independent) Game-1 debate
  prior by the factor n_eff / n:
      c_corr = prior + (c_gls - prior) * (n_eff / n).
  Intuition: the more redundant the panel, the less its consensus should be
  allowed to override the independent debate evidence.

Everything here is deterministic linear algebra and is unit-tested and
validated on synthetic correlated ensembles (scripts/validate_correlation_correction.py).
It requires NO LLM calls, so its numbers are real and reproducible now; measuring
the *realized* correlation of live judge backbones is the Tier-2 experiment.
"""

from __future__ import annotations

import numpy as np


def equicorrelation(n: int, rho: float) -> np.ndarray:
    """Return the n x n equicorrelation matrix (1-rho)I + rho*J."""
    if n <= 0:
        raise ValueError("n must be positive")
    m = np.full((n, n), float(rho))
    np.fill_diagonal(m, 1.0)
    return m


def pearson_correlation_matrix(signals: np.ndarray) -> np.ndarray:
    """Empirical correlation matrix across evaluators.

    Args:
        signals: array shape (n_items, n_evaluators) of per-item reported
                 confidences (or any comparable per-item signal).
    Returns:
        (n_evaluators, n_evaluators) correlation matrix. If an evaluator has
        zero variance (constant signal), it is treated as uncorrelated
        (identity row/col) to avoid NaNs.
    """
    signals = np.asarray(signals, dtype=float)
    if signals.ndim != 2:
        raise ValueError("signals must be 2D (n_items, n_evaluators)")
    n_items, n_eval = signals.shape
    if n_items < 2:
        # Not enough items to estimate correlation -> assume independence.
        return np.eye(n_eval)
    stds = signals.std(axis=0)
    corr = np.eye(n_eval)
    for i in range(n_eval):
        for j in range(i + 1, n_eval):
            if stds[i] == 0 or stds[j] == 0:
                c = 0.0
            else:
                c = float(np.corrcoef(signals[:, i], signals[:, j])[0, 1])
                if np.isnan(c):
                    c = 0.0
            corr[i, j] = corr[j, i] = c
    return corr


def shrink_to_identity(sigma: np.ndarray, lam: float = 0.1) -> np.ndarray:
    """Ledoit-Wolf-style shrinkage toward I: (1-lam)*Sigma + lam*I.

    Keeps the correlation matrix well-conditioned / positive definite so that
    the inverse used by n_eff and the GLS weights is stable. lam in [0,1].
    """
    sigma = np.asarray(sigma, dtype=float)
    n = sigma.shape[0]
    return (1.0 - lam) * sigma + lam * np.eye(n)


def _safe_inv(sigma: np.ndarray) -> np.ndarray:
    """Inverse with a pseudo-inverse fallback for (near-)singular matrices."""
    try:
        return np.linalg.inv(sigma)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(sigma)


def effective_n(sigma: np.ndarray) -> float:
    """Effective evaluator count n_eff = 1^T Sigma^{-1} 1, clipped to [1, n]."""
    sigma = np.asarray(sigma, dtype=float)
    n = sigma.shape[0]
    if n == 1:
        return 1.0
    ones = np.ones(n)
    inv = _safe_inv(sigma)
    val = float(ones @ inv @ ones)
    # Numerical guardrails: n_eff can never be <1 or >n for a valid corr matrix.
    return max(1.0, min(float(n), val))


def gls_weights(sigma: np.ndarray) -> np.ndarray:
    """Bates-Granger / GLS minimum-variance combination weights, summing to 1.

    Falls back to uniform weights if the result is degenerate (e.g. negative
    weights from an ill-conditioned matrix), which keeps arbitration stable.
    """
    sigma = np.asarray(sigma, dtype=float)
    n = sigma.shape[0]
    if n == 1:
        return np.array([1.0])
    ones = np.ones(n)
    inv = _safe_inv(sigma)
    w = inv @ ones
    denom = ones @ w
    if denom == 0 or not np.isfinite(denom):
        return np.full(n, 1.0 / n)
    w = w / denom
    # Guard against pathological negative weights.
    if np.any(w < -1e-9):
        return np.full(n, 1.0 / n)
    w = np.clip(w, 0.0, None)
    s = w.sum()
    return w / s if s > 0 else np.full(n, 1.0 / n)
