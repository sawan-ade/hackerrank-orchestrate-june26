# ★ SELECTED PAPER: Game-Theoretic Multi-Agent Judge for Bias-Resistant LLM Evaluation

**Author:** Sawan Ade  
**Affiliations:** IISER Bhopal & IIT Patna  
**Supervisors:** Dr. Rahul Mishra (IIT Patna), Ashutosh Kumar Sinha (IISER Bhopal)  
**Target Venues:** AAMAS 2027 / AAAI 2027 / ACL 2027 / EMNLP 2027  

---

## 1. The Idea in One Paragraph

Current LLM-as-a-judge systems suffer from well-documented biases: **position bias** (favoring the first answer ~20-40% of the time), **verbosity bias** (rewarding longer but redundant answers by 0.5-1.5 points on a 5-point scale), and **sycophancy** (agreeing with user opinions rather than evaluating objectively). We propose a **Game-Theoretic Multi-Agent Judge (GT-Judge)** that replaces single-shot heuristic scoring with a focused pipeline of **3 tightly coupled strategic games**: a **Reasoning Debate Game** (extensive-form), a **Confidence Calibration Game** (proper scoring rules), and a **Consensus Arbitration Game** (Nash bargaining). Instead of computing a weighted sum of subjective criteria, the final verdict is the **equilibrium outcome** of the multi-agent system, where each agent's strategy must survive adversarial challenge. We show empirically that this reduces position bias, verbosity bias, and sycophancy compared to single-judge and vanilla multi-agent debate baselines.

---

## 2. Why This Scope Works (Lesson from Idea B's Weakness)

The original Idea B proposed 7 subgames. That was too broad — reviewers would reject it as "overscoped." We keep the **3 most impactful games** and drop the others:

| Game | Status | Reason |
|:---|:---:|:---|
| Game 1: Reasoning Game | ✅ **KEEP** | Core contribution — this is where the multi-agent debate happens with game-theoretic structure |
| Game 2: Evidence Game | ❌ Drop | Overlaps heavily with the Reasoning Game; merge evidence checking into Game 1's attack/defend moves |
| Game 3: Confidence Calibration | ✅ **KEEP** | Directly addresses overconfidence/sycophancy; Brier Score is clean and provable |
| Game 4: Consensus Game | ✅ **KEEP** | Necessary to resolve disagreements between agents; Nash Bargaining is well-understood |
| Game 5: Cost Game | ❌ Drop | Important but is an *engineering optimization*, not a *research contribution*. Mention in experiments as token-cost analysis. |
| Game 6: Robustness Game | ❌ Drop | Can be an ablation experiment (test GT-Judge under adversarial rephrasings) rather than a formal game |
| Game 7: Safety Game | ❌ Drop | Binary constraint, not a game. Implement as a post-processing filter, not a theoretical contribution. |

**Result**: 3 games, each with full mathematical treatment, clear payoffs, and provable properties.

---

## 3. The 3 Games — Detailed Design

### Game 1: Reasoning Debate Game (Extensive-Form)

**What it does**: Two evaluator agents (Proposer P and Challenger C) engage in a structured multi-round debate about the quality of a candidate answer.

**Why it matters**: Unlike vanilla multi-agent debate (which is just "discuss and vote"), this game has formal moves, payoffs, and an equilibrium. The Challenger is incentivized to find real flaws, not to agree.

```
Round 1:  P claims "Answer A is better because [reasoning]"
Round 2:  C attacks with "But A's reasoning fails because [counterexample]"
Round 3:  P defends or concedes specific points
...
Terminal: Judge aggregates logical outcomes
```

**Formal Definition**:
- **Players**: $N = \{P, C\}$ (Proposer, Challenger)
- **Actions**: $\mathcal{A} = \{\text{Defend}, \text{Attack}, \text{Counterexample}, \text{Concede}, \text{Clarify}\}$
- **Payoff for P**:
  $$\mathcal{U}_P = \text{ValidClaims}(P) - \text{SuccessfulAttacks}(C) - \lambda \cdot \text{Tokens}(P)$$
- **Payoff for C**:
  $$\mathcal{U}_C = \text{SuccessfulAttacks}(C) - \text{RefutedAttacks}(P) - \lambda \cdot \text{Tokens}(C)$$
- **Equilibrium**: Subgame-perfect equilibrium via backward induction. P defends only valid claims. C attacks only genuine flaws. The equilibrium filters out sycophantic agreement and surface-level verbosity.

**Anti-bias Properties**:
- **Kills sycophancy**: C is *rewarded* for finding flaws, not for agreeing
- **Kills verbosity bias**: Extra length that doesn't survive C's attacks adds zero utility
- **Kills position bias**: Both answers go through the same debate process with role randomization

---

### Game 2: Confidence Calibration Game (Proper Scoring Rules)

**What it does**: After the debate, each evaluator agent reports a probability estimate $\hat{p} \in [0,1]$ expressing confidence in their verdict.

**Why it matters**: Current LLM judges are notoriously overconfident. A model says "Answer A is clearly better" with implicit 99% confidence even when the answers are nearly identical. This game punishes overconfidence and rewards honest uncertainty.

**Formal Definition**:
- **Player**: Each evaluator agent $i$
- **Action**: Report confidence $\hat{p}_i \in [0, 1]$
- **Scoring Rule** (Brier Score):
  $$\mathcal{U}_{\text{cal}}(\hat{p}_i, y) = 1 - (\hat{p}_i - y)^2$$
  where $y \in \{0, 1\}$ is the ground-truth outcome (determined by human labels on a calibration set, or by the consensus of the debate).
- **Theorem** (well-known): The Brier Score is a *strictly proper scoring rule*. An agent maximizes expected utility **if and only if** it reports its true belief:
  $$\hat{p}_i^* = \mathbb{E}[y \mid \text{agent } i\text{'s information}]$$

**Anti-bias Properties**:
- **Kills sycophancy**: Agents that blindly agree (high confidence, often wrong) are severely penalized
- **Encourages "I'm not sure"**: The optimal strategy when genuinely uncertain is to report $\hat{p} \approx 0.5$

---

### Game 3: Consensus Arbitration Game (Nash Bargaining)

**What it does**: When evaluator agents disagree on the verdict (which happens frequently), we resolve the dispute through a bargaining mechanism rather than simple majority voting.

**Why it matters**: Majority voting ignores the *strength* of each agent's position. An agent with strong evidence and high calibrated confidence should carry more weight than one that barely survived the debate.

**Formal Definition**:
- **Players**: All evaluator agents $N = \{1, 2, \ldots, n\}$
- **Actions**: Each proposes a verdict $v_i \in \{\text{A wins}, \text{B wins}, \text{Tie}\}$
- **Disagreement Point** ($d_i$): If no consensus is reached, fall back to expensive human review. Each agent's utility at $d_i$ is low (they "wasted" their reasoning effort).
- **Nash Bargaining Solution**:
  $$v^* = \arg\max_{v} \prod_{i \in N} \left( \mathcal{U}_i(v) - d_i \right)$$
  where $\mathcal{U}_i(v)$ incorporates agent $i$'s debate score and calibrated confidence.

**Anti-bias Properties**:
- **Kills position bias**: Agents with stronger debate performance (regardless of which answer they support) carry more bargaining power
- **Prevents lazy consensus**: The disagreement point penalty ensures agents don't just default to "agree with whatever" — they are incentivized to bring genuine evidence into the negotiation

---

## 3.1 Who Debates Whom? (Clarification)

A common confusion: the two debating agents are **NOT** the ones who generated the answers. There are **two separate layers**:

### Layer 1: Generators (External — NOT part of our system)
These are the LLMs being evaluated (e.g., GPT-4o, Claude 3.5, Gemini). They each produce an answer to a question. We receive Answer A and Answer B as **inputs**. We do not control or modify them.

### Layer 2: GT-Judge Evaluators (Our system)
These are the LLM agents we deploy as evaluators. They read both answers and engage in a structured debate about which is better.

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 1: GENERATORS (already exist, not our work)      │
│                                                         │
│   [Model X] ──→ Answer A    [Model Y] ──→ Answer B     │
│                                                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼ (both answers passed as input)
┌─────────────────────────────────────────────────────────┐
│  LAYER 2: GT-JUDGE (this is what we build)              │
│                                                         │
│  ┌──────────────────┐    ┌──────────────────┐           │
│  │ Evaluator 1      │    │ Evaluator 2      │           │
│  │ (Proposer)       │◄──►│ (Challenger)     │           │
│  │ "A is better     │    │ "No, A fails     │           │
│  │  because..."     │    │  because..."     │           │
│  └──────────────────┘    └──────────────────┘           │
│            │                      │                     │
│            └──────┬───────────────┘                     │
│                   ▼                                     │
│         [GAME 1: Debate]                                │
│                   ▼                                     │
│         [GAME 2: Confidence]                            │
│                   ▼                                     │
│         [GAME 3: Consensus]                             │
│                   ▼                                     │
│          Final Verdict                                  │
│     (Equilibrium Outcome)                               │
└─────────────────────────────────────────────────────────┘
```

### Why Not a Single Evaluator?

| Single LLM Judge | Our GT-Judge (2 evaluators) |
|:---|:---|
| "A is better because it's longer and detailed" | Challenger: "A's extra detail repeats the same point 3 times — no new info" |
| Says "A wins" but flips to "B wins" when order is swapped (position bias) | Both answers go through the same debate; order doesn't affect debate structure |
| Agrees with everything (sycophancy) | Challenger is *paid* to find flaws — sycophancy is strictly dominated |

### Can We Use More Than 2 Evaluators?
Yes. More evaluators = more robust consensus in Game 3 (Nash Bargaining), but also higher token cost. We start with **2 evaluators** (minimum for debate) and run ablations with 3 and 4 to measure the accuracy vs. cost tradeoff.

---

## 4. Detailed Architecture & Pipeline

The GT-Judge runs as a **3-stage sequential pipeline** for each evaluation instance:

```
╔══════════════════════════════════════════════════════════════════╗
║                    GT-JUDGE FULL PIPELINE                       ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  INPUT: Question Q, Answer A, Answer B                          ║
║                                                                  ║
║  ┌─── STAGE 1: REASONING DEBATE (Game 1) ──────────────────┐    ║
║  │                                                          │    ║
║  │  Round 1: Role Assignment                                │    ║
║  │  ┌────────────────┐     ┌────────────────┐               │    ║
║  │  │ Evaluator 1    │     │ Evaluator 2    │               │    ║
║  │  │ PROPOSER for A │     │ CHALLENGER     │               │    ║
║  │  │ "A wins b/c…"  │────►│ "A fails b/c…" │               │    ║
║  │  │                │◄────│                │               │    ║
║  │  └────────────────┘     └────────────────┘               │    ║
║  │  Round 2: Role Swap                                      │    ║
║  │  ┌────────────────┐     ┌────────────────┐               │    ║
║  │  │ Evaluator 1    │     │ Evaluator 2    │               │    ║
║  │  │ PROPOSER for B │     │ CHALLENGER     │               │    ║
║  │  │ "B wins b/c…"  │────►│ "B fails b/c…" │               │    ║
║  │  │                │◄────│                │               │    ║
║  │  └────────────────┘     └────────────────┘               │    ║
║  │                                                          │    ║
║  │  Output: Debate transcript + per-agent claim scores      │    ║
║  └──────────────────────────────────────────────────────────┘    ║
║                              │                                   ║
║                              ▼                                   ║
║  ┌─── STAGE 2: CONFIDENCE CALIBRATION (Game 2) ────────────┐    ║
║  │                                                          │    ║
║  │  Each evaluator reports:                                 │    ║
║  │    p̂₁ ∈ [0,1] — "My confidence that A wins"             │    ║
║  │    p̂₂ ∈ [0,1] — "My confidence that A wins"             │    ║
║  │                                                          │    ║
║  │  Scored via Brier Score:                                 │    ║
║  │    U_cal(p̂, y) = 1 - (p̂ - y)²                           │    ║
║  │                                                          │    ║
║  │  Overconfident agents are penalized.                     │    ║
║  │  Underconfident agents lose less.                        │    ║
║  │                                                          │    ║
║  │  Output: Calibrated confidence scores per evaluator      │    ║
║  └──────────────────────────────────────────────────────────┘    ║
║                              │                                   ║
║                              ▼                                   ║
║  ┌─── STAGE 3: CONSENSUS ARBITRATION (Game 3) ─────────────┐    ║
║  │                                                          │    ║
║  │  IF evaluators agree → output verdict directly           │    ║
║  │                                                          │    ║
║  │  IF evaluators disagree →                                │    ║
║  │    Nash Bargaining Solution:                             │    ║
║  │    v* = argmax ∏(Uᵢ(v) - dᵢ)                            │    ║
║  │                                                          │    ║
║  │    Bargaining power = f(debate_score, confidence)        │    ║
║  │    Disagreement point = cost of human review             │    ║
║  │                                                          │    ║
║  │  Output: Final verdict (A wins / B wins / Tie)           │    ║
║  └──────────────────────────────────────────────────────────┘    ║
║                              │                                   ║
║                              ▼                                   ║
║  OUTPUT: Verdict + Justification + Confidence Score              ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

### Key Design Decisions

1. **Both answers are debated symmetrically**: Evaluator 1 first proposes for Answer A, then proposes for Answer B. This eliminates position bias by construction.
2. **Role swap is mandatory**: If an agent only sees one side, it can develop confirmation bias. Forcing it to argue both sides produces more balanced evaluations.
3. **Confidence is reported AFTER the debate**: This ensures confidence reflects the post-debate state, not a pre-debate snap judgment.
4. **Nash Bargaining uses debate-weighted power**: An agent that had more surviving claims in the debate carries more weight in the bargaining stage — not equal voting.

---

## 4.1 How GT-Judge Differs from ECON (ICML 2025)

**ECON** (*"From Debate to Equilibrium: Belief-Driven Multi-Agent LLM Reasoning via Bayesian Nash Equilibrium"*, ICML 2025) is our closest prior work. After reading their GitHub repo and paper, here is a precise comparison:

### What ECON Does
- **Goal**: Improve LLM *reasoning accuracy* (solving math problems, planning tasks).
- **Agents**: Multiple *executor* LLMs coordinate to produce one answer to a question.
- **Key Mechanism**: A **Coordinator LLM** generates strategies (≤50 tokens), and executor agents update their **beliefs** about other agents' strategies without direct message exchange. They seek a **Bayesian Nash Equilibrium (BNE)** via hierarchical reinforcement learning.
- **Architecture**: Two-stage — (1) Individual belief formation, (2) BNE coordination with convergence detection.
- **Reward**: Three components — Task-Specific (correctness), Action Likelihood (cosine similarity to coordinator commitment), Collaborative Contribution (fidelity + novelty).
- **Training**: Uses RL (Q-learning with soft target updates, τ=0.01) to learn dynamic reward weights (α-logits).
- **Results**: 11.2% accuracy improvement, 21.4% token reduction vs. traditional multi-agent debate.

### What GT-Judge Does Differently

| Dimension | ECON | GT-Judge (Ours) |
|:---|:---|:---|
| **Goal** | Better *reasoning* (produce the right answer) | Better *evaluation/judging* (decide which answer is better) |
| **Agents are** | Answer generators (produce solutions) | Answer evaluators (judge other models' solutions) |
| **Core game** | Bayesian game with belief coordination | Extensive-form debate + proper scoring + bargaining |
| **Training** | Requires RL training (Q-learning) | **Training-free** — uses prompting + game structure |
| **Communication** | Implicit (belief updates, no direct messages) | Explicit (structured debate rounds with formal moves) |
| **Equilibrium** | BNE over belief distributions | Subgame-perfect equilibrium via backward induction |
| **Confidence** | Not modeled | Explicitly modeled via Brier Score (Game 2) |
| **Target biases** | Not addressed (reasoning-focused) | Position bias, verbosity bias, sycophancy |
| **Key contribution** | Coordination efficiency (fewer tokens) | Evaluation robustness (fewer biases) |

### The Key Insight: ECON for Reasoning → GT-Judge for Judging

ECON proves that seeking equilibrium outperforms heuristic debate for *reasoning*. We take this insight and apply it to a **different domain**: LLM *evaluation*. This is not just a re-application — the game structure is fundamentally different:

- In ECON, agents cooperate to find the right answer → **cooperative game**.
- In GT-Judge, evaluators challenge each other's claims → **adversarial game with formal payoffs**.
- ECON has no notion of "bias" — it optimizes correctness. GT-Judge specifically targets the **well-documented biases** (position, verbosity, sycophancy) that plague LLM-as-a-judge systems.
- ECON requires RL training. GT-Judge is **training-free** — the game structure itself enforces good behavior through incentive design.

---

## 5. Improvement Area: Where We Show Empirical Gains

Based on the latest literature review, we target **3 concrete, measurable improvements**:

| Metric | Current SOTA Problem | Our Target Improvement |
|:---|:---|:---|
| **Position Bias** | Single judges flip winner in 20-40% of cases when answer order is swapped | GT-Judge reduces flip rate to <10% because debate structure forces evaluation of content, not position |
| **Verbosity Bias** | Judges give 0.5-1.5 extra points to longer answers on a 5-point scale | GT-Judge eliminates verbosity advantage because extra length that doesn't survive debate attacks yields zero utility |
| **Agreement with Human Labels** | Single LLM judges achieve ~75-85% agreement with human preferences | GT-Judge achieves >85% by filtering out sycophantic and positional noise through adversarial debate |

### Benchmarks to Use
1. **MT-Bench** — Standard pairwise comparison benchmark with human labels
2. **AlpacaEval 2.0** — Length-controlled evaluation (directly tests verbosity resistance)
3. **RewardBench** — Measures judge accuracy across safety, reasoning, and chat categories

### Baselines to Compare Against
1. Single LLM judge (GPT-4o, Claude 3.5)
2. Multi-agent debate (vanilla MAD without game-theoretic structure)
3. Majority voting (3 independent judges)
4. CollabEval (collaborative multi-agent framework, Amazon 2025)

---

## 6. What Makes This Publishable at a Good Venue

| Venue Requirement | How We Satisfy It |
|:---|:---|
| **Novelty** | Game-theoretic structure (formal payoffs, equilibrium) applied to multi-agent *judging* (not just reasoning/debate). No existing paper does this — ECON (ICML 2025) does equilibrium for *reasoning*, not *evaluation*. |
| **Theoretical Contribution** | Theorems on subgame-perfect equilibrium in the debate game + properness of the scoring rule + existence of Nash bargaining solution |
| **Empirical Results** | Measurable bias reduction on 3 standard benchmarks against 4 baselines |
| **Alignment with Prof's Interests** | Multi-agent systems + Game theory = exact match |
| **Manageable Scope** | 3 games (not 7), each with clean math and clear experiments |

### Best-Fit Venues (Ranked)
1. **AAMAS 2027** (Autonomous Agents and Multi-Agent Systems) — Perfect fit for multi-agent game theory
2. **AAAI 2027** — Strong track on game theory + AI, recent papers on LLM evaluation
3. **ACL/EMNLP 2027** — NLP venues now accept LLM-as-a-judge papers (see ICLR 2026 accepted list)
4. **NeurIPS 2027 / ICLR 2027** — Stretch goal, would need very strong empirical results

---

## 7. Research Complexity Breakdown

| Component | Difficulty | Notes |
|:---|:---:|:---|
| **Formalizing 3 games** | 🟢 Approachable | The math for each game (extensive-form, Brier score, Nash bargaining) is well-established. The novelty is in the *application* and *coupling*. |
| **Implementing the debate** | 🟡 Medium | Need to design prompts that force agents into structured debate roles (Proposer/Challenger) with specific move types. LangGraph can handle the state management. |
| **Extracting calibrated confidence** | 🟡 Medium | LLMs don't natively output probabilities. Options: (a) use logprobs, (b) prompt the agent to output a numeric confidence, (c) use temperature sampling. This is the main engineering challenge. |
| **Running benchmarks** | 🟢 Approachable | MT-Bench, AlpacaEval, RewardBench all have public datasets and evaluation scripts. |
| **Writing proofs** | 🟡 Medium | The proofs themselves are adaptations of known results (backward induction, properness of Brier, Nash bargaining existence). The challenge is writing them cleanly for the specific LLM context. |
| **Measuring bias reduction** | 🟢 Approachable | Position bias = swap answers and measure flip rate. Verbosity bias = correlate score with length. Both are standard metrics. |

---

## 8. Research Roadmap

```
Phase 1: Formalization (Week 1-3)
├── Write formal game definitions for Games 1, 2, 3
├── Sketch proof of subgame-perfect equilibrium for Game 1
├── Write properness proof for Game 2 (adapt standard Brier result)
├── Write existence proof for Game 3 (adapt Nash bargaining theorem)
└── Present to Prof for feedback on formalization

Phase 2: Implementation (Week 4-6)
├── Build GT-Judge using LangGraph (state machine with debate rounds)
├── Implement Proposer and Challenger prompt templates
├── Implement confidence extraction (logprobs or prompted numeric)
├── Implement Nash bargaining aggregation
└── Test on 10-20 MT-Bench examples manually

Phase 3: Experiments (Week 7-9)
├── Run GT-Judge on full MT-Bench, AlpacaEval 2.0, RewardBench
├── Run all 4 baselines on same benchmarks
├── Measure: position bias flip rate, verbosity correlation, human agreement
├── Run ablations: (a) debate only, (b) calibration only, (c) full GT-Judge
└── Compute token cost overhead vs. accuracy gain

Phase 4: Writing (Week 10-12)
├── Write full paper (8 pages + appendix)
├── Create figures: architecture diagram, bias reduction charts, ablation table
├── Get feedback from Prof and PhD supervisor
└── Submit to AAMAS or AAAI
```

---

## 9. Key Papers to Read First

| Priority | Paper | Venue | Why |
|:---|:---|:---|:---|
| 🔴 MUST | "From Debate to Equilibrium (ECON)" | ICML 2025 | Closest prior work — BNE for LLM reasoning. We extend to *judging*. |
| 🔴 MUST | "TrustJudge: Inconsistencies of LLM-as-a-Judge" | ICLR 2026 | Documents the specific biases we target |
| 🔴 MUST | "J1: Incentivizing Agentic Reasoning in LLM-as-a-Judge via RL" | ICLR 2026 | Uses RL to improve judges — we use game theory instead |
| 🟡 READ | "Betting on Equilibrium: Monitoring Strategic Behavior in MAS" | ICML 2026 | Game-theoretic monitoring of agent behavior |
| 🟡 READ | "CollabEval" | Amazon Science 2025 | Multi-agent collaborative evaluation — our main empirical baseline |
| 🟡 READ | "ConfMAD" | ACL 2025 | Confidence-aware multi-agent debate — directly related to our Game 2 |
| 🟢 SKIM | "Dependence-Aware Label Aggregation via Ising Models" | ICML 2026 | Alternative approach to multi-judge aggregation |
| 🟢 SKIM | "FormalJudge: Neuro-Symbolic Agentic Oversight" | ICML 2026 | Different paradigm (neuro-symbolic vs game-theoretic) for comparison |

---

## 10. Relationship to Rejected Ideas

This selected idea takes the **best elements** from all previous ideas:

| Source | What We Reuse |
|:---|:---|
| **Idea A** (Claim Adjudication) | The payoff matrix structure and mixed-strategy equilibrium derivation → adapted for Game 1's debate payoffs |
| **Idea B** (7-Subgame Judge) | The Reasoning Game, Confidence Calibration, and Consensus Game are directly inherited. The Correlated Agreement mechanism → simplified into the Nash Bargaining in Game 3 |
| **Idea C** (Mechanism Design Vision) | The philosophical framing ("make manipulation irrational"), the experimental evaluation checklist, and the Golden Rule |
| **Idea D** (Peer Prediction) | The peer prediction insight → incorporated into how we validate Game 2's confidence scores (agents' scores are cross-checked) |
