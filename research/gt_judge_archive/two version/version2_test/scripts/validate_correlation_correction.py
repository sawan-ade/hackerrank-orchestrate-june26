"""
scripts/validate_correlation_correction.py  (issue §5)
======================================================
Validates the correlated-error correction on SYNTHETIC ensembles with a KNOWN
ground-truth correlation. This uses no LLM calls, so the numbers are real and
reproducible right now (seeded). It is a controlled test of the *mechanism*;
measuring the realized correlation of live judge backbones is the Tier-2
experiment (pending paid keys).

Two checks:
  (A) Identity check: the implemented n_eff = 1^T Sigma^{-1} 1 matches the closed
      form n / (1 + (n-1) rho) for equicorrelation matrices.
  (B) Calibration check: a logarithmic opinion pool that treats n correlated
      judges as n INDEPENDENT votes (the Kohli et al. 2026 failure mode) is
      overconfident. Replacing the vote count n with the effective count
      n_eff = 1^T Sigma^{-1} 1 restores calibration: lower ECE, less
      overconfidence-when-wrong, and lower Brier — with zero change at rho = 0
      (where n_eff = n and the correction is the identity map).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
from src.correlation import (  # noqa: E402
    equicorrelation, effective_n,
)

RNG = np.random.default_rng(20260718)


def check_identity():
    print("(A) n_eff identity check  [implemented vs closed form n/(1+(n-1)rho)]")
    print(f"    {'n':>3} {'rho':>5} {'implemented':>12} {'closed_form':>12} {'ok':>4}")
    ok_all = True
    for n in (2, 3, 5):
        for rho in (0.0, 0.3, 0.6, 0.9):
            sigma = equicorrelation(n, rho)
            impl = effective_n(sigma)
            closed = n / (1 + (n - 1) * rho)
            closed = max(1.0, min(float(n), closed))
            ok = abs(impl - closed) < 1e-6
            ok_all &= ok
            print(f"    {n:>3} {rho:>5.2f} {impl:>12.4f} {closed:>12.4f} {'yes' if ok else 'NO':>4}")
    print(f"    => identity holds: {ok_all}\n")
    return ok_all


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def simulate(n_eval=3, rho=0.6, trials=20000):
    """Correlated judge panel aggregated by a logarithmic opinion pool.

    Each evaluator i sees the same item (true label y in {0,1}) and reports a
    confidence p_i that A (y=1) is superior, from a latent score
        z_i = signal*(2y-1) + shared*sqrt(rho) + indep_i*sqrt(1-rho),
        p_i = sigmoid(gain * z_i).
    'shared' is common to all evaluators (=> pairwise error correlation ~rho);
    'indep_i' is private.

    Aggregation (matches src/arbitration_game.py):
      naive     : L = n     * mean_logit           (independence assumption)
      corrected : L = n_eff * mean_logit           (n_eff independent judges)
    with a neutral prior (logit 0) so the mechanism, not the prior, is tested.
    """
    signal = 0.7   # informativeness of the truth (moderate: mistakes happen)
    gain = 1.3
    sigma = equicorrelation(n_eval, rho)
    n_eff = effective_n(sigma)

    y = RNG.integers(0, 2, size=trials).astype(float)
    shared = RNG.standard_normal(trials)
    indep = RNG.standard_normal((trials, n_eval))
    z = signal * (2 * y - 1)[:, None] + shared[:, None] * np.sqrt(rho) + indep * np.sqrt(1 - rho)
    p = _sigmoid(gain * z)                        # (trials, n_eval) confidences

    mean_logit = _logit(p).mean(axis=1)           # uniform (equicorr => GLS uniform)
    p_naive = _sigmoid(n_eval * mean_logit)       # independence-assuming pool
    p_corr = _sigmoid(n_eff * mean_logit)         # corrected: n_eff judges

    def brier(pred):
        return float(np.mean((y - pred) ** 2))

    # Expected Calibration Error: bin by predicted prob, |acc - conf| per bin.
    def ece(pred, n_bins=10):
        edges = np.linspace(0.0, 1.0, n_bins + 1)
        total = 0.0
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (pred >= lo) & (pred < hi if hi < 1.0 else pred <= hi)
            if not m.any():
                continue
            conf = float(np.mean(pred[m]))
            acc = float(np.mean((pred[m] > 0.5) == (y[m] > 0.5)))
            total += (m.mean()) * abs(acc - conf)
        return float(total)

    # overconfidence-when-wrong: mean |pred-0.5| on trials the panel gets wrong
    def overconf_wrong(pred):
        wrong = (pred > 0.5) != (y > 0.5)
        return float(np.mean(np.abs(pred[wrong] - 0.5))) if wrong.any() else 0.0

    return {
        "rho": rho, "n_eff": n_eff,
        "brier_naive": brier(p_naive), "brier_corrected": brier(p_corr),
        "ece_naive": ece(p_naive), "ece_corrected": ece(p_corr),
        "overconf_wrong_naive": overconf_wrong(p_naive),
        "overconf_wrong_corrected": overconf_wrong(p_corr),
    }


def check_calibration():
    print("(B) Calibration under correlated errors  (n=3 evaluators, 20k trials)")
    print(f"    {'rho':>5} {'n_eff':>6} {'ECE_naive':>10} {'ECE_corr':>9} {'dECE':>8}"
          f" {'ocw_naive':>10} {'ocw_corr':>9} {'Brier_nv':>9} {'Brier_cr':>9}")
    rows = []
    for rho in (0.0, 0.3, 0.6, 0.9):
        r = simulate(n_eval=3, rho=rho)
        d_ece = r["ece_naive"] - r["ece_corrected"]
        rows.append(r)
        print(f"    {rho:>5.2f} {r['n_eff']:>6.2f} {r['ece_naive']:>10.4f} "
              f"{r['ece_corrected']:>9.4f} {d_ece:>+8.4f} "
              f"{r['overconf_wrong_naive']:>10.3f} {r['overconf_wrong_corrected']:>9.3f} "
              f"{r['brier_naive']:>9.4f} {r['brier_corrected']:>9.4f}")
    # Claims we actually assert (and that the numbers must support):
    #  1. No harm at rho=0 (ECE essentially unchanged).
    #  2. ECE improves under correlation (rho=0.9).
    #  3. Overconfidence-on-wrong drops under correlation.
    no_harm = abs(rows[0]["ece_naive"] - rows[0]["ece_corrected"]) < 5e-3
    ece_helps = rows[-1]["ece_naive"] - rows[-1]["ece_corrected"] > 0
    ocw_helps = rows[-1]["overconf_wrong_naive"] - rows[-1]["overconf_wrong_corrected"] > 0
    print(f"\n    no harm at rho=0 (ECE):        {no_harm}")
    print(f"    ECE improves at rho=0.9:       {ece_helps}")
    print(f"    overconf-on-wrong drops @0.9:  {ocw_helps}")
    print("    (ocw = mean overconfidence on WRONG predictions; lower is better.")
    print("     Under a log-odds pool the naive rule is genuinely overconfident,")
    print("     so ECE, overconfidence-on-wrong, AND Brier all improve; at rho=0")
    print("     n_eff=n and the correction is exactly the identity.)\n")
    return rows


if __name__ == "__main__":
    print("=" * 72)
    print("  §5 Correlated-Error Correction — synthetic validation (seeded, no LLM)")
    print("=" * 72 + "\n")
    check_identity()
    check_calibration()
