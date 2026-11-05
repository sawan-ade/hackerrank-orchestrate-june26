# ASSIGNMENT 1: MATHEMATICAL FORMULATION OF GT-JUDGE SUBGAMES

- **Assignee**: Sawan Ade (PI)  
- **Assigned Date**: 2026-07-15  
- **Target Deadline**: 2026-07-22  
- **Status**: 🔴 **Active / Incomplete**  
- **Related Files**:  
  - [NOTATION.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/NOTATION.md)  
  - [TEMPLATES.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/TEMPLATES.md)  

---

## 1. Objective
Your task is to draft the formal mathematical equations and proof outlines for the **three subgames** of the GT-Judge pipeline. These formulations will be integrated directly into Section 3 of the academic paper manuscript and used as the blueprint for our Python game solver implementation in `src/games/`.

---

## 2. Detailed Task Breakdown

### Task 1.1: Game 1 (Reasoning Debate Game) Payoff Formulation
- [ ] Define the finite game tree for a $K = 3$ round debate between Proposer ($P$) and Challenger ($C$).
- [ ] Define how a natural language claim $c_t$ or attack $a_t$ translates into a numeric valuation. (e.g., Let $v(c_t) \in [0, 1]$ be the logical validity score assigned to claim $c_t$ by an independent Critic model).
- [ ] Formulate the exact utility functions:
  $$\mathcal{U}_P(s_P, s_C) = \sum_{t \text{ round of } P} v(c_t) - \sum_{t \text{ round of } C} \text{Severity}(a_t) - \lambda \cdot \text{Tokens}(P)$$
  $$\mathcal{U}_C(s_P, s_C) = \sum_{t \text{ round of } C} \text{Severity}(a_t) - \lambda \cdot \text{Tokens}(C)$$
- [ ] State the assumptions necessary for a Subgame-Perfect Nash Equilibrium (SPNE) to exist.

---

### Task 1.2: Game 2 (Confidence Calibration) Proper Scoring Proof
- [ ] Write out the Brier Score utility equation for evaluator $i$ reporting confidence $\hat{p}_i \in [0, 1]$ over the binary ground truth $y \in \{0, 1\}$:
  $$\mathcal{U}_{\text{cal}}(\hat{p}_i, y) = 1 - (y - \hat{p}_i)^2$$
- [ ] Write the expected utility calculation:
  $$\mathbb{E}[\mathcal{U}_{\text{cal}}(\hat{p}_i)] = P(y=1) [1 - (1 - \hat{p}_i)^2] + P(y=0) [1 - (0 - \hat{p}_i)^2]$$
- [ ] Take the first-order condition (FOC) with respect to $\hat{p}_i$ and prove that the expected utility is strictly maximized at $\hat{p}_i = P(y=1) = \mathbb{E}[y]$.
- [ ] Document this proof using the proof template in [TEMPLATES.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/TEMPLATES.md#L15-L31).

---

### Task 1.3: Game 3 (Consensus Arbitration) Bargaining Point Definition
- [ ] Formulate the threat point $d_i$ for each agent $i$.
  *Hint: If bargaining fails, we revert to human verification, which incurs cost $C_H$. Therefore, the disagreement point utility is $d_i = -C_H - \text{effort}_i$.*
- [ ] Define the Nash product optimization:
  $$v^* = \arg\max_{v} \prod_{i \in N} \left( \mathcal{U}_i(v) - d_i \right)$$
- [ ] Describe how the bargaining weights $w_i$ scale as a function of the agent's calibration score in Game 2.

---

## 3. Expected Deliverables
A new markdown file named `theory/formulation_draft.md` in the repository containing:
1.  Payoff matrices or game trees for Game 1.
2.  Latex equations for Game 2 utility maximization.
3.  Optimization setup for Game 3 bargaining.
