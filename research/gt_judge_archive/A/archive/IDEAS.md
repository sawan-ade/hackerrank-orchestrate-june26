# PERMANENT RESEARCH NOTEBOOK: IDEAS.md

This notebook preserves all candidate and active research directions for the GT-Judge project. Deleted ideas are archived here, not removed, to ensure long-term scientific tracking.

---

## 1. Selected & Active Ideas

### [Idea-001] — 3-Game GT-Judge for Bias-Resistant LLM Evaluation

- **Status**: **Active (Selected for Paper)**
- **Target Venues**: AAMAS 2027, AAAI 2027, ACL 2027
- **Problem**: Pairwise LLM evaluation models suffer from position bias (20-40% flip rate), verbosity bias (0.5-1.5 point inflation), and sycophancy.
- **Motivation**: Existing remedies are mechanical (e.g., swapping prompt order) or rely on heuristics. We need an evaluation system where truthful and calibrated reporting naturally emerges as the optimal strategic equilibrium.
- **Related Work**: 
  - *ECON (ICML 2025)*: Multi-agent coordination for reasoning.
  - *TrustJudge (ICLR 2026)*: Analyzing judge inconsistencies.
  - *Peer Prediction without Ground Truth (Science 2004)*: Truth elicitation mechanics.
- **Novelty**: Applies game-theoretic mechanism design (extensive-form debate, Brier proper scoring, and Nash bargaining) directly to the multi-agent LLM-as-a-judge paradigm without requiring training or fine-tuning.
- **Mathematical Possibility**: 
  - Game 1 (Debate) is solved using backward induction for Subgame-Perfect Nash Equilibrium.
  - Game 2 (Calibration) uses Brier Score properness theorem to prove truth-telling.
  - Game 3 (Arbitration) is solved using the Nash Bargaining Solution.
- **Advantages**: Robust to position and style bias; provides detailed, auditable debate transcripts; zero training cost.
- **Weaknesses**: Significant API token overhead; high latency due to sequential game phases.
- **Open Questions**: How does token cost scale as candidate answer length increases? Can we design an early-stopping rule for Game 1 to save tokens when answer quality gap is large?

---

## 2. Archived & Rejected Ideas

### [Idea-002] — Claim Adjudication Inspection Game (Human-vs-AI)

- **Status**: **Archived (Not selected as primary paper)**
- **Archived Date**: 2026-07-15
- **Reason**: The human-vs-AI inspection game is a classic game-theoretic setup (e.g., auditing systems). Applying it to visual claim validation (e.g., insurance claim damage) is an interesting engineering application, but it lacks the core theoretical and agentic novelty required for top-tier AI research venues.
- **What We Repurposed**: The mixed-strategy inspection game matrix and payoff derivations are repurposed for the debate utilities in Game 1.

### [Idea-003] — 7-Subgame LLM Judge

- **Status**: **Archived (Not selected as primary paper)**
- **Archived Date**: 2026-07-15
- **Reason**: Overscoped. Attempting to model 7 games (Reasoning, Evidence, Calibration, Consensus, Cost, Robustness, Safety) in a single paper makes the mathematical formulations shallow and renders the joint equilibrium mathematically intractable.
- **What We Repurposed**: We selected the 3 most impactful subgames (Reasoning, Calibration, Consensus) and dropped the other 4. Safety and cost are retained as system metrics/constraints, not formal subgames.
