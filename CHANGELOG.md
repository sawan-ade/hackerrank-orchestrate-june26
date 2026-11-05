# RESEARCH CHANGELOG: CHANGELOG.md

This document tracks all modifications to code, theory, parameters, and paper drafts. Every entry is audited for scientific impact, risks, and alignment with the mathematical guidelines.

---

## [2026-07-15] - Initial Project Selection & Architecture Launch

### Added
*   **Selected Paper Framework** ([SELECTED_PAPER.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/A/SELECTED_PAPER.md)): Formalized the 3-Game GT-Judge pipeline:
    1.  *Reasoning Debate Game* (Extensive-form)
    2.  *Confidence Calibration Game* (Brier Score calibration)
    3.  *Consensus Arbitration Game* (Nash Bargaining resolution)
*   **Repository Constitution** ([GEMINI.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/GEMINI.md)): Instituted mathematical, coding, and AI rules.
*   **Research Workflow** ([paper-workflow.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/paper-workflow.md)): Outlined chronological checklists from concept to camera-ready.
*   **Reviewer Simulator** ([reviewer.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/reviewer.md)): Created Reviewer #2 persona templates for ML (NeurIPS/ICML/ICLR), NLP (ACL/EMNLP), and general AI (AAAI) venues.
*   **Repository Architecture Guide** ([repository-guide.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/repository-guide.md)): Specified directories, file permissions, archive rules, and branch strategies.
*   **Assignments System** ([assignments/assignment_1_mathematical_formulation.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/assignments/assignment_1_mathematical_formulation.md)): Launched the active assignments task system and created Assignment 1 targeting the mathematical formulation of the 3 subgames.
*   **GitHub Workflow & Templates** ([.github/](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/.github/)): Added continuous integration (`workflows/ci.yml`), pull request templates, and issue templates for new research ideas.
*   **Root Gateway README** ([README.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/README.md)): Created root readme linking to documentation and active directories.

### Changed
*   **Research OS Refactoring**: Shifted all static research documentation and guidebooks (`GEMINI.md`, `DECISIONS.md`, `IDEAS.md`, `NOTATION.md`, `REFERENCES.md`, `TEMPLATES.md`, etc.) from the root folder to the newly created `docs/` folder to align with GitHub repository standards.

### Scientific Impact
- Established a unified research direction that narrows the project's focus down from 7 complex subgames to 3 mathematically tractable games.
- Provides a clean theoretical boundary separating GT-Judge (ours) from ECON (ICML 2025). We shift the focus from *reasoning coordination* to *evaluation debiasing*.

### Affected Experiments
- None (pre-implementation phase). Sets the target benchmarks to MT-Bench, AlpacaEval 2.0, and RewardBench.

### Related Theorems
- Theorem 1 (Game 2: Brier Score calibration)
- Theorem 2 (Game 3: Nash Bargaining convergence)

### Related Paper Sections
- Section 3: The 3 Games (Theoretical Framework)
- Section 4: Detailed Architecture & Pipeline
- Section 4.1: Comparison to ECON (Related Work / Literature Review)

### Risk Level
- **Low**: Establishing file layout and constitution. The major downstream engineering risk is extracting calibrated logprobs from LLM APIs for Game 2 (Confidence Calibration).

### Next Steps
1. Create other Research OS tracking documents ([DECISIONS.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/DECISIONS.md), [TODO.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/TODO.md), [IDEAS.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/IDEAS.md), [EXPERIMENTS.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/EXPERIMENTS.md), [RESEARCH_COMPASS.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/RESEARCH_COMPASS.md)).
2. Formalize mathematical symbols in [NOTATION.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/NOTATION.md) and literature in [REFERENCES.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/REFERENCES.md).
3. Draft core prompt layouts for Proposer and Challenger agents.
