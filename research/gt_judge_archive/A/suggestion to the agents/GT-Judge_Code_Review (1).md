# GT-Judge — Code Review

**Scope reviewed:** `src/` (models, llm_client, prompts, debate_game, calibration_game, arbitration_game, gt_judge), `run_demo.py`, `run_benchmark.py`, `configs/`, `tests/`, docs.
**Status:** All 17 tests pass locally. Findings below were verified by reading the code and, for the most important ones, by executing it.

> **Headline finding (read this first):** The pipeline's final verdict is determined *entirely* by the Game 2 calibration confidences. The Game 1 debate scores never enter the verdict decision. I verified this directly: holding calibration confidences fixed and flipping the debate scores from `(A=+10, B=-10)` to `(A=-10, B=+10)` produces the **same** verdict both times. The elaborate Debate game is, mathematically, decorative with respect to the outcome. See Issue A-1.

---

## 1. Critical Issues

### A-1 — Debate scores have zero effect on the verdict
- **File:** `src/arbitration_game.py` (+ `src/gt_judge.py`)
- **Function/Class:** `ArbitrationGame.run`, `_compute_weights`
- **Issue:** The verdict is chosen by maximizing the Nash product over `verdict_utilities`, and those utilities depend only on `cal.reported_confidence` and `cal.calibration_score`. `DebateResult.debate_score` feeds *only* `_compute_weights`, where the debate contribution `sum(dr.debate_score ...) / n` is **identical for every evaluator** and therefore cancels out during normalization. Net result: the debate outcome cannot change the verdict.
- **Why it's a problem:** Game 1 is the centerpiece of the framework (the extensive-form debate, endogenous validity, Thm 1). If its scalar output is discarded, the "3-game" pipeline is really a 1.5-game pipeline: an LLM confidence poll (Game 2) plus a monotone transform (Game 3). Every theoretical claim resting on the debate influencing the decision is unsupported by the implementation.
- **Recommended improvement:** Make the debate output an *input to the evaluators' priors or the verdict utilities*. Concretely: (a) feed `debate_score_a - debate_score_b` into the verdict utility as a prior term, or (b) derive each evaluator's `reported_confidence` partly from the debate result rather than a free-standing LLM call, or (c) make bargaining weights depend on *per-evaluator* debate participation (see A-2). Add a regression test asserting that swapping debate scores while fixing confidences changes the verdict.
- **Priority:** Critical

### A-2 — The "multi-agent" evaluators are identical deterministic calls
- **File:** `src/calibration_game.py`
- **Function/Class:** `CalibrationGame.run` / `_elicit_confidence`
- **Issue:** The loop `for evaluator_id in range(self.n_evaluators)` calls `_elicit_confidence` with the **same prompt, same model, and `temperature=0.0`** every time. All evaluators therefore return the same confidence, the same Brier score, and (via A-1) the same weight (`0.5 / 0.5`). There is no persona, no independent evidence, no seed variation, nothing to make evaluator 0 ≠ evaluator 1.
- **Why it's a problem:** The entire premise — adversarial/independent multi-agent judging that resists single-model bias — collapses. `n_evaluators=2` just doubles cost for a bit-identical answer. Nash *bargaining* between two agents who always agree is vacuous.
- **Recommended improvement:** Give evaluators genuine diversity: distinct system personas/rubrics, different temperatures or seeds, or different underlying models. Elicit confidences in parallel (see P-1). Then weights and bargaining become meaningful. At minimum, document that `n_evaluators>1` currently adds no signal.
- **Priority:** Critical

### A-3 — The token-cost penalty λ is never applied to any score
- **File:** `src/debate_game.py`, `src/prompts.py`
- **Function/Class:** `DebateGame.run`; `PROPOSER_SYSTEM`/`CHALLENGER_SYSTEM`
- **Issue:** `lambda_cost` is interpolated into the prompt text ("every extra token costs you λ=…") but never subtracted from any utility. `DebateScore = Σv(c) − Σsev(a,c)` contains no token term. `proposer_tokens`/`challenger_tokens` are tracked but only reused as "effort" in the (inert) disagreement point.
- **Why it's a problem:** `EXPERIMENTS.md` claims verbosity-bias resistance and the README ties λ to "Fix 2 / Thm 1." The mechanism that is supposed to produce that property does not exist in code — an LLM being *told* about a penalty is not the penalty. This is a theory-vs-implementation gap that undermines a headline result.
- **Recommended improvement:** Actually deduct `λ · tokens` from the relevant agent's utility and, if the debate score is meant to reflect it, from `debate_score`. Then verify the verbosity-bias metric empirically rather than asserting it.
- **Priority:** Critical

---

## 2. High-Priority Issues

### B-1 — Two answers are debated in isolation, making debate scores non-comparable and pro-verbosity
- **File:** `src/debate_game.py`, `src/gt_judge.py`
- **Function/Class:** `DebateGame.run`, `GTJudge.evaluate`
- **Issue:** Answer A's debate never sees Answer B (`answer_b=""` in A's `DebateState`, and vice-versa). `DebateScore = Σv(c) − Σsev` is unbounded and scales with the *number of claims the proposer happened to make*. An answer that elicits more claims scores higher regardless of quality.
- **Why it's a problem:** (1) Comparing `score_a` vs `score_b` compares two different scales. (2) It rewards verbosity — the exact bias the project claims to remove — because more text → more claims → higher Σv(c). Although the verdict currently ignores these scores (A-1), they still shape the calibration prompt and the (inert) weights, and any fix to A-1 would inherit this flaw.
- **Recommended improvement:** Either debate A and B head-to-head in one game with a shared claim ledger, or normalize the score (e.g., mean validity per claim, or `Σv − Σsev` divided by claim count) so it is scale-invariant and not monotone in verbosity.
- **Priority:** High

### B-2 — Validity is assessed before the defense exists; when a defense does exist the assessor's output is thrown away
- **File:** `src/debate_game.py`
- **Function/Class:** `DebateGame.run`, `_assess_validity`
- **Issue:** Within a round the order is: proposer moves → challenger attacks → validity assessed *immediately*. The proposer can only defend an attack in the *next* round, so at assessment time `defense_text` is empty (or references a stale earlier attack). Worse, when a claim *was* previously defended, the code ignores the assessor entirely and hard-codes `validity = validity * 0.8`, discarding both `attack_severity` and the `defense_success` boolean the prompt explicitly requests.
- **Why it's a problem:** The endogenous-validity mechanism (Fix 2, Def 2′) is the intellectual core of Game 1, and it's effectively bypassed. Defenses never actually rebut the attack they're meant to answer, and the LLM assessment call is wasted whenever a defense is present.
- **Recommended improvement:** Restructure a round as claim → attack → *defend-in-same-round* → assess, passing the fresh defense into the assessor. Use the returned `attack_severity` and `defense_success` to update validity (e.g., `validity = 1 − severity·(1 − defense_success_factor)`), instead of a flat 0.8.
- **Priority:** High

### B-3 — Nash bargaining is numerically inert; it reduces to "verdict closest to the mean confidence"
- **File:** `src/arbitration_game.py`
- **Function/Class:** `ArbitrationGame.run`, `_compute_disagreement_points`
- **Issue:** `d_i = −C_H − β·effort ≈ −20` in typical runs, while `u_i ∈ [0, 1.5]`. So `surplus = u_i − d_i ≈ u_i + 20`, always positive (feasibility never binds), and `log(u_i + 20)` is dominated by the constant, flattening differences between verdicts. With symmetric weights (A-2), the argmax reduces to picking the verdict whose `y` is nearest the (equal-weight) mean confidence.
- **Why it's a problem:** The "Nash Bargaining Solution over the feasible utility set" is presented as the mechanism (Thm 3, Eq. 24), but in practice it behaves like a fixed threshold on the average confidence. The `nash_product`, `weights`, disagreement point, and effort terms are cosmetic.
- **Recommended improvement:** Put the disagreement point and utilities on the same scale (e.g., normalize utilities to make `d_i` binding for genuinely bad verdicts), give weights real per-evaluator variance (A-2), and add a test showing the verdict differs from a naive average-confidence rule on some input. If it never differs, drop the bargaining machinery and state the aggregation rule honestly.
- **Priority:** High

### B-4 — Two-pass arbitration is an inconsistent one-step fixed point
- **File:** `src/gt_judge.py`
- **Function/Class:** `GTJudge.evaluate`
- **Issue:** In `consensus_proxy` mode: arbitration runs once → its verdict defines `gt_y` → Brier scores computed against that verdict → arbitration runs *again* with updated scores. If the second pass changes the verdict, the Brier scores (and thus weights) are now computed against a verdict that no longer holds. There's no convergence check.
- **Why it's a problem:** The output can be internally inconsistent (weights justified by a verdict the pipeline then overrides). Non-deterministic-feeling behavior that's hard to reason about.
- **Recommended improvement:** Either iterate to a fixed point with a max-iteration guard and convergence check, or compute Brier once and don't re-run, or (cleaner) decouple the verdict from Brier-derived weights so the circularity disappears.
- **Priority:** High

### B-5 — Claimed position-invariance is only partial
- **File:** `src/calibration_game.py`, `src/prompts.py`, `run_benchmark.py`
- **Function/Class:** `_elicit_confidence`, `CALIBRATION_USER`
- **Issue:** The architecture debates A and B separately to be order-invariant, but the calibration prompt is positional: it always presents "ANSWER A" first with `score_a` first. With a real LLM (not the symmetric mock), that ordering can bias the confidence. The benchmark's 0% flip rate comes from the deterministic mock, not from a demonstrated property.
- **Why it's a problem:** Position-bias resistance is a primary selling point (`EXPERIMENTS.md`, target <2%). The current 0.0% figure is an artifact of a symmetric mock and does not validate the claim.
- **Recommended improvement:** Randomize/counterbalance A/B order inside calibration, or average confidence over both orderings, and measure flip rate with a real model before reporting it.
- **Priority:** High

---

## 3. Medium-Priority Issues

### C-1 — `clarify` proposer action is silently dropped
- **File:** `src/debate_game.py` — `DebateGame.run`
- **Issue:** The state machine handles `claim` and `defend` but not `clarify`. A `clarify` move is appended to the transcript and then ignored (no claim created, no claim updated).
- **Why it's a problem:** A whole declared action is a no-op; an evaluator that clarifies effectively wastes a round and tokens.
- **Recommended improvement:** Handle `clarify` explicitly (e.g., attach clarifying text to the targeted claim) or remove it from the action space and prompts.
- **Priority:** Medium

### C-2 — Concede does not end the debate
- **File:** `src/debate_game.py` — `DebateGame.run`
- **Issue:** On `concede`, the code `continue`s and the loop keeps running to `max_rounds`, prompting the proposer to make fresh claims again.
- **Why it's a problem:** Wasted LLM calls and muddied semantics — conceding "all claims are strong" should terminate, not restart.
- **Recommended improvement:** `break` on concede (or track a terminal flag). Combined with early-exit this roughly halves calls on easy instances.
- **Priority:** Medium

### C-3 — Dead code / unused config surface
- **File:** multiple
- **Issue:** `total_debate_effort` (`arbitration_game.py:128`) is computed and never used. `CalibrationGame.ground_truth_mode` is stored but never read (mode logic actually lives in `gt_judge.evaluate` via `ground_truth is not None`). `defense_success` is requested in the prompt but never parsed. `numpy` is in `requirements.txt` but unused. `EvaluationInput` model exists but `evaluate()` takes raw args, bypassing it.
- **Why it's a problem:** Misleads readers about what actually drives behavior; rots over time; inflates the dependency surface.
- **Recommended improvement:** Delete dead variables/deps, wire `EvaluationInput` into `evaluate()` for validation at the boundary, and either use `ground_truth_mode`/`defense_success` or remove them.
- **Priority:** Medium

### C-4 — No parallelism across independent work
- **File:** `src/gt_judge.py`, `src/calibration_game.py`
- **Issue:** Debate A then debate B run sequentially though they're independent; evaluators are polled sequentially; validity calls are sequential.
- **Why it's a problem:** End-to-end latency is ~2× (A/B) to ~N× (evaluators) larger than necessary — the dominant cost is network-bound LLM calls.
- **Recommended improvement:** Run the A and B debates and the evaluator confidences concurrently (`concurrent.futures.ThreadPoolExecutor` or async). This is the single biggest realistic speedup.
- **Priority:** Medium

### C-5 — No caching of repeated/identical LLM calls
- **File:** `src/llm_client.py`, `src/debate_game.py`
- **Issue:** Validity assessments (temperature 0) and other deterministic calls are recomputed even for identical inputs; the benchmark runs each instance forward and backward, duplicating work.
- **Why it's a problem:** Redundant cost and latency, especially at temperature 0 where results are stable.
- **Recommended improvement:** Add an optional `functools.lru_cache`/dict cache keyed on `(system, user, temperature)` in the client for deterministic calls.
- **Priority:** Medium

### C-6 — Benchmark headline result is degenerate (0% accuracy, everything Tie)
- **File:** `results/benchmark_results.json`, `EXPERIMENTS.md` (EXP-003)
- **Issue:** The recorded mock run yields 0% accuracy with every verdict = Tie and confidence 1.0. That's a symptom of the arbitration collapsing to Tie when confidences average to 0.5 (which the mock produces).
- **Why it's a problem:** A pipeline that can't distinguish a correct DP solution from a wrong recursive one on the demo task isn't demonstrating value; publishing 0% without flagging it is misleading.
- **Recommended improvement:** Make the mock produce asymmetric, discriminating signals; treat 0% as a failing smoke test, not a logged result. Better: gate CI on a small real-model run.
- **Priority:** Medium

---

## 4. Low-Priority Issues

### D-1 — "Brier score" naming is inverted
- **File:** `src/calibration_game.py`, `EXPERIMENTS.md`
- **Issue:** The code uses `1 − (y − p̂)²` (a reward, higher = better) and calls it the Brier score with "Target > 0.85". The Brier *score* is `(y − p̂)²` (lower = better).
- **Why it's a problem:** Confuses readers comparing against literature; a reviewer expecting lower-is-better will misread every number.
- **Recommended improvement:** Rename to "Brier reward / calibration utility (1 − Brier)", or report the true Brier and flip the target.
- **Priority:** Low

### D-2 — Redundant enum-vs-string membership checks
- **File:** `src/debate_game.py`
- **Issue:** `move.action in (ProposerAction.CLAIM, "claim")`. Because `ProposerAction` is a `str` Enum, `ProposerAction.CLAIM == "claim"`, so the tuple is redundant. Also `action` is always a plain `str` from `parsed.get(...)`, so the enum branch never triggers distinctly.
- **Why it's a problem:** Noise that suggests a type invariant that isn't enforced.
- **Recommended improvement:** Normalize `action` to the enum once at parse time (`ProposerAction(action)` with a fallback), then compare against enums only.
- **Priority:** Low

### D-3 — `call` exception handling is order-fragile
- **File:** `src/llm_client.py` — `LLMClient.call`
- **Issue:** `RateLimitError`/`APIConnectionError`/etc. are subclasses of `APIError`; they're caught first, which is correct, but the second `except APIError` relies on `e.status_code` truthiness and silently won't retry a 500 with `status_code=None`. Also non-retryable 4xx correctly re-raise — good — but this is easy to break in edits.
- **Why it's a problem:** Subtle; a refactor reordering the excepts would change retry semantics.
- **Recommended improvement:** Collapse into one handler that inspects `getattr(e, "status_code", None)` and an explicit retryable set; add a unit test for a 400 (no retry) and a 503 (retry).
- **Priority:** Low

### D-4 — Docs drift
- **File:** `README.md`, `run_demo.py`
- **Issue:** README's directory layout omits `run_benchmark.py`, `EXPERIMENTS.md`, `results/`. `run_demo.py` docstring says `cd A/code`. README claims `results/demo_output.json` is produced but only benchmark output is committed.
- **Recommended improvement:** Regenerate the layout section and fix stale paths.
- **Priority:** Low

---

## 5. Testing Review

**What's good:** The suite (17 tests) is fast, offline, and covers model validation, the Brier formula (including the Corollary-2 sanity note), `_verdict_to_y`, weight normalization, config loading, retry-then-success, retry exhaustion, a fully mocked end-to-end pipeline, and the mock benchmark path. Retry tests patch `time.sleep` correctly and assert call counts — nicely done.

**Gaps / missing cases (each of these would have caught a bug above):**

- **No test that the verdict responds to the debate outcome.** A property test flipping debate scores with fixed confidences would immediately expose A-1.
- **No test that two evaluators can disagree** — would surface A-2. Currently `test_full_pipeline_success` mocks the games wholesale, so it never exercises real evaluator elicitation.
- **`DebateGame.run` has no unit test at all.** The claim/attack/defend/concede state machine, ID counters, and the validity-update branch (B-2) are entirely untested. Mock the `LLMClient` and assert claims/attacks/validity transitions.
- **No test for `call_structured` parsing fallbacks** (raw JSON, fenced ```json block, and the `parse_error` last resort). This is core robustness code.
- **No position-bias test with an *asymmetric* mock** — the current mock is symmetric, so `test_..._flip` can't fail. Feed different responses for A-first vs B-first and assert behavior.
- **No test that verbosity does not inflate the score** — directly relevant to A-3/B-1; pad one answer and assert the score/verdict is unchanged.
- **No feasibility/edge test for arbitration** when `surplus <= 0` (the `feasible = False` branch is never hit in tests).
- **No test for the two-pass fixed point (B-4)** where the verdict changes between passes.

---

## Summary

### Biggest strengths
1. **Clean, well-typed data layer.** The Pydantic models in `models.py` are clear, well-bounded (`ge/le` constraints), and map explicitly to the formal definitions — genuinely easy to read.
2. **Solid, well-tested LLM client.** Exponential backoff with jitter, sensible retryable-error set, and a pragmatic 3-tier JSON parsing fallback. The retry tests are among the best in the suite.
3. **Good module separation and config-driven construction.** `from_config`, one file per game, and an orchestrator that reads top-to-bottom make the intended pipeline obvious.
4. **Offline-runnable benchmark + mock mode.** Being able to exercise the whole pipeline with no API key is excellent for CI and reviewers.
5. **Strong documentation intent.** README and EXPERIMENTS clearly state the design and metrics — which is also what let me spot the theory-vs-code gaps.

### Top 10 improvements by impact
1. **Make the debate actually influence the verdict** (A-1). Without this the framework's core claim is unimplemented.
2. **Give the evaluators real diversity** (A-2) — personas/temperature/models + independent elicitation — so "multi-agent" and "bargaining" mean something.
3. **Actually enforce the λ token penalty in scoring** (A-3), then re-measure verbosity bias.
4. **Fix the defend→assess ordering and use the assessor's real output** (B-2) so endogenous validity works.
5. **Debate A vs B head-to-head or normalize the debate score** (B-1) to kill the built-in verbosity reward and make scores comparable.
6. **Make arbitration non-degenerate or state the true aggregation rule** (B-3); prove it differs from a mean-confidence threshold or simplify honestly.
7. **Resolve the two-pass consistency problem** (B-4) with a guarded fixed point or a decoupled design.
8. **Counterbalance A/B order in calibration and measure real flip rate** (B-5).
9. **Add the missing tests** — debate state machine, verdict-vs-debate property, evaluator disagreement, parsing fallbacks, verbosity invariance (Testing section).
10. **Parallelize independent LLM calls and cache deterministic ones** (C-4, C-5) for a large latency/cost win; delete dead code (C-3).

### Ratings (out of 10)

| Dimension | Score | One-line rationale |
|---|---|---|
| Architecture | 6 | Clean module boundaries and config, but the pipeline's data flow is broken — Game 1's output is discarded and Game 3 is largely inert. |
| Code Quality | 6.5 | Readable, typed, documented; dropped by dead code, an illogical validity branch, and unenforced mechanisms. |
| Maintainability | 7 | Small, well-named modules with docstrings and tests make changes easy — the main risk is stale docs/theory drift. |
| Performance | 5 | Correct but naive: no parallelism, no caching, always runs full K rounds, and one wasted duplicate evaluator call per instance. |
| Game Logic | 4.5 | The three games are individually plausible but wired together so that the debate and bargaining don't actually drive the result. |
| **Overall** | **5.5** | A well-engineered *scaffold* with clean code and good tests, wrapped around a decision core that doesn't yet implement the game-theoretic behavior it claims. Fixing A-1 through A-3 and B-1/B-2 would raise this substantially. |

**Bottom line:** The engineering craftsmanship (schemas, client, tests, config, docs) is clearly above average. The gap is between the *stated* game-theoretic design and what the code *actually computes*: the debate and the bargaining are, today, mostly ceremony around an averaged confidence poll of two identical evaluators. That gap is fixable, and none of the fixes require rewriting the project — they're targeted changes to how the three games' outputs feed each other.
