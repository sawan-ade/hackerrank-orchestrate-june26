# Deliverables checklist (§8)

Honest status. "Done" means done and verified in this environment; anything that
requires live LLM access is marked blocked, with the reason.

## Done and verified

- [x] **§1.1** Fabricated results removed; mock quarantined to
  `tests/scripted_llm.py`; `--mock` writes only `results/mock_ci_results.json`
  with a warning banner + field. Verified by running both runners.
- [x] **§1.2** AI co-author removed from paper; sole author Sawan Ade;
  Reproducibility/AI-use statement added. (Venue-specific wording still to be
  re-checked — noted in CHANGELOG.)
- [x] **§1.3** Unverifiable citations dropped; real competitors added and
  differentiated (Kohli 2026, ECON, Trust-or-Escalate, TrustJudge, PoLL,
  MT-Bench, Prelec). All verified against arXiv / proceedings.
- [x] **§2** Multi-provider client (`BaseLLMClient` + OpenAI/Anthropic/Google),
  `model.provider` config, `.env.example`, `--provider/--model/--api-key`
  overrides on both runners, `scripts/test_connection.py`. Backward-compatible
  factory verified against existing retry tests.
- [x] **§3 (scaffolding)** Balanced 20-item stratified pilot set; cost estimator
  + spend confirmation in `run_benchmark.py`; ablation harness
  `scripts/run_ablations.py` (all four pipelines run and are distinct offline).
- [x] **§4** Race condition fixed (per-run id counters); formulas reconciled
  code↔paper; test suite 22 → 54 passing; `requirements.txt` pinned + `numpy`;
  seed strategy documented.
- [x] **§5** New contribution implemented (`src/correlation.py` +
  log-odds/`n_eff` correction in `arbitration_game.py`) and **validated on
  seeded synthetic data** — the one real empirical result
  (`scripts/validate_correlation_correction.py`, `results/correlation_validation.txt`).
- [x] **§6** Paper rewritten as `paper/paper.tex`, recompiled to `paper.pdf`,
  with real-or-`TODO` numbers; README and EXPERIMENTS rewritten honestly.
- [x] **§7** `CHANGELOG.md` (what + why + files, grouped by section).

## Blocked — live LLM access required (NOT done)

- [ ] **§3 Tier-1 pilot run** — dataset ready; needs a backbone.
  `pending backbone access`.
- [ ] **§3 Tier-2 full benchmark** (≥2 backbones, 3–5 repeats, ablations, real
  measured `n_eff`) — `pending Tier-2 budget`.
- [ ] **Headline paper numbers** (accuracy vs. human, position-flip rate,
  verbosity bias) — remain `TODO — pending real run`; deliberately not estimated.

**Reason blocked:** the development sandbox has no network route to any external
LLM provider (every provider endpoint returns `host_not_allowed`); only
`api.anthropic.com` is reachable and no Anthropic key was available. Live runs
must be executed in an environment with provider access. Per ground rule 0, no
number was fabricated to close the gap.

## To do before submission (owner: author)

- [ ] Re-check the AI-use disclosure wording against the target venue's policy.
- [ ] Run Tier-1, then Tier-2; paste real run IDs/dates/models into
  `EXPERIMENTS.md` and the paper, replacing the `TODO` markers.
- [ ] Rotate the API keys that were shared in chat during this pass (they were
  never written to any file in this repository).
