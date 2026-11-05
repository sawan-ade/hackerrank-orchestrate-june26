# SCIENTIFIC DECISION LOG: DECISIONS.md

This document tracks all design and mathematical decisions made during the lifecycle of the GT-Judge project.

---

## [Decision 001] — Narrowing Scope from 7 Subgames to 3

- **Date**: 2026-07-15
- **Author**: Sawan Ade (PI) & AI Research Assistant
- **Status**: Approved

### The Problem
The initial proposal for the Game-Theoretic Judge outlined 7 distinct subgames (Reasoning, Evidence, Calibration, Consensus, Cost, Robustness, Safety) to run in sequence for evaluating an LLM output. 
- **Reviewer Critique Projection**: A paper claiming to solve all 7 aspects would be rejected as overscoped, shallow, and mathematically intractable.
- **Compute Overhead**: Running 7 LLM-based games sequentially would lead to massive token consumption and high latency, rendering the system practically useless.

### Options Considered

1.  **Option A (Full 7 Games)**: Keep the complete pipeline. Explain each game briefly and run simple prompt heuristics for payoffs.
2.  **Option B (2-Game Focus)**: Focus only on *Reasoning Debate* and *Consensus Arbitration*. Ignore calibration and safety.
3.  **Option C (3-Game Unified GT-Judge - SELECTED)**: Focus on a tightly coupled pipeline of 3 games:
    - *Reasoning Debate* (extensive-form game representing claims, attacks, counterexamples)
    - *Confidence Calibration* (scoring reported probability using proper scoring rules to penalize overconfidence)
    - *Consensus Arbitration* (solving disagreements via Nash Bargaining weighted by debate score and confidence)

### Reasoning & Evidence
- **Option C** provides the perfect balance of theoretical novelty and tractability.
- **Brier Score calibration** directly addresses the well-documented "overconfidence bias" in LLM judges.
- **Nash Bargaining** represents a significant advance over simple majority voting or average scores, which ignore the intensity of agent preferences.
- This creates a cohesive narrative: "Evaluate through debate (Game 1), measure belief strength (Game 2), and negotiate a consensus (Game 3)."

### Trade-offs
- **Cons**: We drop safety and cost modeling from the core theoretical contributions.
- **Pros**: The paper gains mathematical clarity. We can write explicit theorems for each of the 3 games and prove their properties.

### Rejected Alternatives
- Option A was rejected due to lack of depth.
- Option B was rejected because ignoring confidence calibration leaves the system vulnerable to overconfident hallucinations, which is a major failure mode of LLM judges.

### Future Implications & File Links
- Implementation code in `src/games/` will build exactly 3 game loops.
- Theoretical formulation in [SELECTED_PAPER.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/A/SELECTED_PAPER.md#L34-L104) maps exactly to these 3 games.
