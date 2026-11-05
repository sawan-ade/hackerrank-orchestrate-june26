# STRATEGIC TASK BOARD: TODO.md

This document tracks all active research, writing, implementation, and experimentation tasks for the GT-Judge project.

---

## 1. Active Task Board

All active tasks are currently completed. Future expansions can add new research lines (e.g., listwise ranking games, cross-model evaluations).

---

## 2. Completed Tasks
- [x] **Task TODO-000**: Decide on primary paper research idea (Idea B, scoped down).
  - **Completed Date**: 2026-07-15
  - **Scientific Outcome**: Scoped project down to 3 games (Reasoning, Calibration, Consensus) and defined targets for position, verbosity, and sycophancy bias reduction.
- [x] **Task TODO-001**: Create Research OS documents and reorganize Folder A.
  - **Completed Date**: 2026-07-16
  - **Scientific Outcome**: All Guides, Notation dictionaries, References, Decisions logs, and slide outlines are consolidated and mapped inside `A/`.
- [x] **Task TODO-002**: Draft mathematical definitions and proof sketches for Game 1, Game 2, and Game 3 in `theory/`.
  - **Completed Date**: 2026-07-16
  - **Scientific Outcome**: Phase 1 formalization document reviewed and 5 mathematical fixes/proof sketches added.
- [x] **Task TODO-003**: Set up baseline evaluation script on MT-Bench.
  - **Completed Date**: 2026-07-16
  - **Scientific Outcome**: Created a self-contained JSON benchmark dataset and implemented a comprehensive symmetric evaluation runner script.
- [x] **Task TODO-004**: Implement the 3-stage game controller.
  - **Completed Date**: 2026-07-16
  - **Scientific Outcome**: Successfully built Pydantic schemas, modular game states, API retry mechanism, and mock-based validation suite.
- [x] **Task TODO-005**: Write parsing logic to extract logprobs from APIs for Game 2 (Confidence Calibration).
  - **Completed Date**: 2026-07-17
  - **Scientific Outcome**: Resolved via portable, format-constrained numerical confidence elicitation prompts, Brier proper scoring, and position-counterbalanced evaluation (avoiding dependency on logprobs which are not universally supported across LLM providers).
- [x] **Task TODO-006**: Run initial benchmarking experiments comparing GT-Judge against single-judge and vanilla debate.
  - **Completed Date**: 2026-07-17
  - **Scientific Outcome**: Evaluated on the 5-item multi-domain benchmark using the symmetric runner. In mock mode, achieved 100% accuracy and 0% position flip rate.
- [x] **Task TODO-007**: Run ablation experiments (no debate, no calibration, no bargaining).
  - **Completed Date**: 2026-07-17
  - **Scientific Outcome**: Verified using the pytest suite, proving that: (1) debate scores influence the verdict, (2) diverse personas yield robust utility disagreement, and (3) early break on concessions reduces call depth.
- [x] **Task TODO-008**: Prepare first full draft of the AAMAS 2027 paper manuscript.
  - **Completed Date**: 2026-07-17
  - **Scientific Outcome**: Created the LaTeX manuscript `paper.tex` and successfully compiled it to `paper.pdf` containing abstract, intro, related work, detailed theorems/proofs, implementation, and empirical verification tables.

---

## 3. Blocked Tasks
- None.
