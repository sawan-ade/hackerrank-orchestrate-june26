# Final Research Idea Selection & Roadmap

**Prepared by:** Sawan Ade  
**Date:** July 14, 2026  
**Purpose:** Select the best paper idea from all candidates, archive rejected alternatives, and define a concrete research plan.

---

## Part I: All Candidate Ideas Reviewed

We have collected ideas from two directories:
- [Folder A](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/A) — 3 files
- [agents/Ideas](file:///c:/Users/Sawan/Desktop/agents/Ideas) — 3 files (including a PDF)

After thorough review, we identify **4 distinct ideas** across these files:

---

### Idea A: "Game-Theoretic Framework for Claim Adjudication"
**Source**: [agentic paper .md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/A/agentic%20paper%20.md)

| Aspect | Detail |
|:---|:---|
| **Core Concept** | Model the interaction between a *human claimant* and an *AI auditor* as an Inspection Game and Signaling Game. Derive optimal audit rates to deter insurance/warranty fraud. |
| **Players** | Human Claimant vs. AI Judge |
| **Game Types** | Inspection Game, Signaling Game |
| **Novelty** | Applies classical inspection game theory to a VLM-based claim verification pipeline |
| **Strength** | Clean math, well-defined payoff matrix, directly grounded in a working hackathon system |
| **Weakness** | The "game" is between a human and an AI — this is a known formulation in economics. Not novel enough for a top ML venue. The AI side is treated as a monolithic agent, not a multi-agent system. Reviewers at ICLR/ICML would see this as an *application* of textbook game theory, not a *contribution* to it. |

---

### Idea B: "7-Subgame Judge with Bayesian Peer-Adjudication"
**Source**: [game_theoretic_judge_proposal.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/A/game_theoretic_judge_proposal.md) + [presentation_slides.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/A/presentation_slides.md)

| Aspect | Detail |
|:---|:---|
| **Core Concept** | Replace single-shot LLM-as-a-judge with 7 interconnected subgames (Reasoning, Evidence, Calibration, Consensus, Cost, Robustness, Safety). Each criterion becomes a game with players, strategies, and equilibria. Introduce Correlated Agreement peer prediction to resist collusion. |
| **Players** | Proposer, Opponent, Retriever, Verifier, Critic |
| **Game Types** | Extensive-form debate, Inspection game, Proper scoring rules, Nash Bargaining, Zero-sum adversarial, Safety barrier |
| **Novelty** | Multi-subgame architecture is creative. Peer prediction for collusion resistance is genuinely novel in LLM-as-a-judge context. |
| **Strength** | Ambitious scope, strong theoretical narrative, addresses real failure modes (collusion, moral hazard, overconfidence) |
| **Weakness** | **Too broad.** 7 subgames is far too many for a single paper. No reviewer will accept a paper that claims to solve reasoning, evidence, calibration, consensus, cost, robustness, AND safety in one shot. The math for each game is shallow because the scope forces surface-level treatment. The equilibrium across 7 coupled subgames is intractable to compute or even define cleanly. |

---

### Idea C: "Mechanism Design for Trustworthy Multi-Agent Evaluation"
**Source**: [Research_Vision_Equilibrium_Based_LLM_as_a_Judge.md](file:///c:/Users/Sawan/Desktop/agents/Ideas/Research_Vision_Equilibrium_Based_LLM_as_a_Judge.md)

| Aspect | Detail |
|:---|:---|
| **Core Concept** | The goal is NOT to build a smarter judge. The goal is to design an evaluation mechanism where truthful evaluation is the rational strategy and manipulation is unprofitable. This is a mechanism design problem, not prompt engineering. |
| **Players** | Generator, Judge, Verifier, Critic, Reflection Agent, Appeal Agent |
| **Game Types** | General mechanism design framework |
| **Novelty** | The *framing* is the most mature and publishable of all ideas. It asks the right question: "Can we make manipulation irrational?" |
| **Strength** | Philosophically sharp. Clean research question. The "Golden Rule" (start from a real failure mode, then design a mechanism whose equilibrium removes it) is excellent. The experimental evaluation checklist (manipulation resistance, collusion resistance, verbosity bias, position bias, sycophancy, self-preference, reward hacking) is concrete and testable. |
| **Weakness** | It is a *vision document*, not a paper. No math, no formalization, no specific mechanism proposed. It needs to be fused with the mathematical machinery from Ideas A and B. |

---

### Idea D: My Addition — "Incentive-Compatible Peer Evaluation via Information Elicitation Without Verification (IEWV)"
**Source**: My own synthesis, inspired by the gap between Ideas B and C, and grounded in the following A* papers discovered in your ICLR 2026 / ICML 2026 collections:

**Key A* papers from your saved conference lists:**
- *ICLR 2026*: "Truthfulness Despite Weak Supervision: Evaluating and Training LLMs Using Peer Prediction"
- *ICLR 2026*: "Incentivizing Agentic Reasoning in LLM-as-a-Judge via Tool-Integrated Reinforcement Learning" (J1)
- *ICLR 2026*: "Incentive-Aligned Multi-Source LLM Summaries"
- *ICLR 2026*: "TrustJudge: Inconsistencies of LLM-as-a-Judge and How to Alleviate Them"
- *ICML 2026*: "Dependence-Aware Label Aggregation for LLM-as-a-Judge via Ising Models"
- *ICML 2026*: "FormalJudge: A Neuro-Symbolic Paradigm for Agentic Oversight"
- *ICML 2026*: "Betting on Equilibrium: Monitoring Strategic Behavior in Multi-Agent Systems"
- *ICML 2025*: "From Debate to Equilibrium (ECON)"

| Aspect | Detail |
|:---|:---|
| **Core Concept** | Design a multi-agent evaluator where agents are paid based on *mutual information* with independent peers (peer prediction), not by matching a ground-truth label. This removes the need for a "correct answer" during evaluation and makes collusion and lazy verification provably suboptimal. |
| **Players** | Generator A, Generator B, Verifier, Independent Critic |
| **Game Types** | Bayesian information elicitation game (single focused game, not 7) |
| **Novelty** | Bridges the gap: peer prediction has been applied to *training* LLMs (ICLR 2026) but NOT to *multi-agent evaluation/judging*. The key insight is that in a multi-agent judge, you can use one agent's evaluation as a "peer report" for another, creating incentive compatibility without ground truth. |

---

## Part II: Comparative Verdict

| Criterion | Idea A (Claim Adj.) | Idea B (7-Subgame) | Idea C (Mechanism Vision) | **Idea D (Peer Eval.)** |
|:---|:---:|:---:|:---:|:---:|
| **Novelty** | Low (textbook game theory) | Medium (scope too broad dilutes novelty) | High (right question) | **High** (novel bridge) |
| **Feasibility (6 months)** | High | Low (7 games intractable) | Low (no math yet) | **High** (1 focused game) |
| **Publishability (ICLR/NeurIPS)** | Low | Low (overscoped) | Medium (vision only) | **High** |
| **Mathematical Depth** | Medium | Shallow (spread thin) | None | **Deep** (focused) |
| **Experimental Testability** | Medium | Low | High (good checklist) | **High** |
| **Reviewers Would Say** | "Known formulation" | "Too many claims" | "Where's the paper?" | **"Clean contribution"** |

---

## Part III: THE BEST IDEA — Selected for Paper

# ★ Incentive-Compatible Multi-Agent LLM Evaluation via Peer Prediction

### Elevator Pitch (1 sentence)
> Design a multi-agent LLM evaluation mechanism where honest, diligent judging is the unique Nash Equilibrium—achieved by paying evaluator agents based on agreement with independent peers rather than matching a ground-truth label.

### Why This Wins

1. **Focused**: One clean mechanism, one clean game, one clean theorem. Not 7 subgames.
2. **Novel Gap in Literature**: Peer prediction has been used to *train* LLMs (ICLR 2026: "Truthfulness Despite Weak Supervision") but has NOT been applied to *multi-agent judging pipelines*. This is a clear, defensible gap.
3. **Addresses Real Failure Modes**: Directly targets the failures identified in Idea C's vision document:
   - **Sycophancy**: Agents that flatter the generator are penalized because an independent peer won't produce the same sycophantic evaluation.
   - **Position Bias**: Random assignment of generator outputs to evaluators breaks positional correlation.
   - **Collusion**: Agents cannot communicate, so collusion requires coordinating on a focal point—which peer prediction mechanisms are designed to make suboptimal.
   - **Verbosity Bias**: Rewarding mutual information, not surface agreement, means long verbose answers don't get free points.
4. **Builds on Idea C's Philosophy**: "The mechanism is the contribution. The equilibrium is the proof."
5. **Mathematically Clean**: Uses well-understood machinery (Bayesian Truth Serum, Correlated Agreement, Brier Score) applied to a new domain.
6. **Takes the Best from Each Rejected Idea**:
   - From Idea A: The inspection game payoff matrix structure.
   - From Idea B: The Correlated Agreement mechanism and the confidence calibration game.
   - From Idea C: The philosophical framing and the experimental checklist.

### Proposed Paper Structure

```
1. Introduction & Motivation
   - Failure modes of LLM-as-a-judge (position bias, sycophancy, verbosity bias, reward hacking)
   - Why "building a smarter judge" is the wrong question
   - Our question: "Can we design a mechanism where manipulation is irrational?"

2. Related Work
   - LLM-as-a-Judge: MT-Bench, Chatbot Arena, AlpacaEval
   - Multi-Agent Debate: ECON (ICML 2025), MAD
   - Peer Prediction: Prelec (2004), Miller et al. (2005), ICLR 2026
   - Mechanism Design for LLMs: Incentive-Aligned Summaries (ICLR 2026)

3. Problem Formulation
   - Define the evaluation game formally
   - Players: Generator A, Generator B, Evaluator 1, Evaluator 2 (independent)
   - Types: Each evaluator has a private signal about quality
   - Actions: Report a quality score
   - Information structure: Incomplete information (no ground truth)

4. The Peer-Predictive Evaluation Mechanism (PPEM)
   - Mechanism description (who evaluates what, how payments work)
   - Theorem 1: Truthful evaluation is a Bayesian Nash Equilibrium
   - Theorem 2: The mechanism is collusion-resistant under independent priors
   - Corollary: Sycophantic and lazy strategies are strictly dominated

5. Experiments
   - Baselines: Single LLM judge, majority voting, vanilla multi-agent debate
   - Our method: PPEM
   - Metrics: Agreement with human labels, resistance to adversarial manipulation,
              position bias measurement, verbosity correlation, sycophancy detection
   - Benchmarks: MT-Bench, AlpacaEval, RewardBench

6. Analysis & Discussion
   - Ablation: What happens when peer correlation breaks?
   - Cost analysis: Token overhead vs. accuracy gain
   - Limitations: Requires ≥2 independent evaluators

7. Conclusion
```

### Research Complexity Assessment

| Component | Difficulty | What Makes It Hard | How to Tackle It |
|:---|:---:|:---|:---|
| **Formal Game Formulation** | 🟡 Medium | Defining the type space and signal distributions for LLM evaluators | Start with binary quality signals ($\theta \in \{0,1\}$), extend to continuous later |
| **Proving Equilibrium** | 🟢 Approachable | BTS/CA proofs are well-established; the novelty is in the *application* domain, not in inventing new math | Adapt Prelec (2004) proof structure to the LLM context |
| **Collusion Resistance Proof** | 🟡 Medium | Must show that coordinating on a "collusive focal point" yields lower expected utility | Use the standard result that under independent priors, truth-telling strictly dominates in CA mechanisms |
| **Mapping LLM Outputs to Signals** | 🔴 Hard | LLMs don't output clean probability distributions; you need to extract calibrated confidence scores | Use logprob extraction or calibrated sampling. This is the main engineering challenge. |
| **Experimental Setup** | 🟡 Medium | Need to construct adversarial scenarios (sycophantic evaluators, lazy evaluators, colluding evaluators) | Use prompt injection to create "corrupted" evaluator agents, then measure PPEM's resistance |
| **Benchmarking** | 🟢 Approachable | MT-Bench and AlpacaEval have standard human labels | Compare agreement rates and bias measurements |

### Key Papers to Read (Ordered by Priority)

1. **[MUST READ]** "Truthfulness Despite Weak Supervision: Evaluating and Training LLMs Using Peer Prediction" — *ICLR 2026*
2. **[MUST READ]** "From Debate to Equilibrium: Belief-Driven Multi-Agent LLM Reasoning via Bayesian Nash Equilibrium (ECON)" — *ICML 2025*
3. **[MUST READ]** "Incentive-Aligned Multi-Source LLM Summaries" — *ICLR 2026*
4. **[READ]** "TrustJudge: Inconsistencies of LLM-as-a-Judge and How to Alleviate Them" — *ICLR 2026*
5. **[READ]** "J1: Incentivizing Agentic Reasoning in LLM-as-a-Judge via Tool-Integrated RL" — *ICLR 2026*
6. **[READ]** "Dependence-Aware Label Aggregation for LLM-as-a-Judge via Ising Models" — *ICML 2026*
7. **[READ]** "Betting on Equilibrium: Monitoring Strategic Behavior in Multi-Agent Systems" — *ICML 2026*
8. **[READ]** "FormalJudge: A Neuro-Symbolic Paradigm for Agentic Oversight" — *ICML 2026*
9. **[BACKGROUND]** Prelec (2004), "A Bayesian Truth Serum for Qualitative Data" — *Science*
10. **[BACKGROUND]** Miller et al. (2005), "Eliciting Informative Feedback" — *Management Science*
11. **[BACKGROUND]** Irving et al. (2018), "AI Safety via Debate" — *OpenAI*

### Research Roadmap

```
Phase 1: Deep Reading (Week 1-2)
├── Read papers #1-#3 above in full
├── Extract: What mechanism did they use? What did they prove? What's their limitation?
└── Write: 1-page summary of the gap our paper fills

Phase 2: Formalization (Week 3-4)
├── Define the formal game G = ⟨N, A, U, Θ, P⟩
├── Write Theorem 1 (truthful equilibrium) and sketch proof
├── Write Theorem 2 (collusion resistance) and sketch proof
└── Present draft theorems to Prof for feedback

Phase 3: Experimental Design (Week 5-6)
├── Design adversarial evaluator prompts (sycophantic, lazy, colluding)
├── Implement PPEM using LangGraph or similar framework
├── Run on MT-Bench and AlpacaEval
└── Measure: agreement with human labels, bias metrics

Phase 4: Writing & Iteration (Week 7-8)
├── Write full paper draft
├── Run ablation experiments
├── Get feedback from Prof and PhD supervisor
└── Target submission: NeurIPS 2027 or ICLR 2027
```

---

## Part IV: Rejected Ideas (Archived, Not Discarded)

These ideas are NOT discarded. They contain valuable components that feed into the selected idea.

### Rejected Idea A: "Game-Theoretic Framework for Claim Adjudication"
**Status**: ❌ Not selected as primary paper
**Reason**: The human-vs-AI inspection game is a well-known formulation in economics. Applying it to VLM-based claim verification is an interesting *application paper* but lacks the theoretical novelty required for a top ML venue.
**What We Keep**: The payoff matrix structure and the mixed-strategy Nash equilibrium derivation. These are used as pedagogical building blocks in the new paper's Section 3.

### Rejected Idea B: "7-Subgame Judge with Bayesian Peer-Adjudication"
**Status**: ❌ Not selected as primary paper
**Reason**: 7 subgames is too ambitious for one paper. Reviewers will say "too many claims, insufficient depth on each." The equilibrium across 7 coupled games is intractable.
**What We Keep**: The Correlated Agreement mechanism (Section 4.1) and the confidence calibration via Brier Score (Game 3). Both are directly integrated into the selected idea's PPEM mechanism.

### Rejected Idea C: "Mechanism Design Vision Document"
**Status**: ❌ Not selected as primary paper (it's a vision, not a paper)
**Reason**: No formalization, no theorems, no experiments. It is a research philosophy document, not a publishable paper.
**What We Keep**: EVERYTHING. The philosophical framing ("the mechanism is the contribution"), the research question ("can we make manipulation irrational?"), the experimental checklist (manipulation resistance, collusion resistance, all 7 bias types), and the "Golden Rule" (start from a real failure mode). These form the *backbone* of the selected paper's motivation and evaluation.

---

## Summary (Updated July 14, 2026)

> [!IMPORTANT]
> **Decision**: After discussion with the user, **Idea B (scoped down from 7 to 3 games)** is selected as the primary paper. This aligns with the professor's research interests in multi-agent systems and game theory. The full scoped-down plan is in [SELECTED_PAPER.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/A/SELECTED_PAPER.md).

| | Status | Role in Final Paper |
|:---|:---:|:---|
| Idea A (Claim Adjudication) | ❌ Archived | Payoff matrix structure reused in Game 1 |
| **Idea B (3-Game GT-Judge)** | **✅ SELECTED** | **The paper — scoped to 3 games: Reasoning Debate, Confidence Calibration, Consensus Arbitration** |
| Idea C (Mechanism Vision) | ❌ Archived | Philosophy + experimental checklist reused |
| Idea D (Peer-Predictive Eval.) | ❌ Archived | Peer prediction insight incorporated into Game 2's cross-validation |
