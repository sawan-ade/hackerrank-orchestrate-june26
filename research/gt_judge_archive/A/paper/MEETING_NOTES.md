# SUPERVISOR & COLLABORATION MEETING LOG: MEETING_NOTES.md

This registry records all research group meetings, feedback sessions, and decisions alignment with Dr. Rahul Mishra and Ashutosh Kumar Sinha.

---

## Meeting [2026-07-15] — Launching the Scoped-Down GT-Judge Framework

- **Date**: 2026-07-15
- **Participants**: Sawan Ade (PI), AI Research Assistant
- **Objective**: Align on selection of research idea and repository constitution.

### Discussions
- **Theoretical Scope**: Reviewed Idea B (7 subgames). Agreed that the original layout was too complex and lacked mathematical depth for each subgame.
- **The Scoped Solution**: Agreed to narrow the scope down to **3 core games** (Reasoning Debate Game, Confidence Calibration Game, Consensus Arbitration Game).
- **Novelty Alignment**: Discussed how this differs from ECON (ICML 2025). Confirmed that applying game-theoretic coordination to LLM *evaluation* (biases) rather than *reasoning generation* is a highly defensible gap for A* venues.

### Scientific Decisions
- Approved the transition to the 3-Game GT-Judge pipeline.
- Established the **Research OS** constitution and guidelines to protect files from silent changes.

### Action Items & Follow-ups
- [ ] **Action 001** (Sawan Ade): Write mathematical formulation of the extensive-form debate payoffs (due: 2026-07-22).
- [ ] **Action 002** (Sawan Ade): Set up MT-Bench data structures in `datasets/` (due: 2026-07-25).
- [ ] **Action 003** (AI Research Assistant): Draft prompt engineering templates for Proposer and Challenger agent roles (due: 2026-07-20).
