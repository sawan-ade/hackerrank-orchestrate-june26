# Presentation: Game-Theoretic Multi-Agent Judge for Bias-Resistant LLM Evaluation

**Speaker:** Sawan Ade  
**Supervisors:** Dr. Rahul Mishra (IIT Patna), Ashutosh Kumar Sinha (IISER Bhopal)  
**Research Area:** Autonomous Multi-Agent Systems & Algorithmic Game Theory  

---

## Slide 1: LLM-as-a-Judge & The Status Quo

### The Pairwise Evaluation Paradigm
```
           [Question] 
               │
          ┌────┴────┐
          │         │
      [Answer A] [Answer B]
          │         │
          └────┬────┘
               │
          [LLM Judge]  <-- "Which answer is better?" (Single-shot)
               │
           [Winner]
```

### Critical Flaws in Current Judges
1. **Position Bias**: Preference for the first/second position. Flips winners in **20–40%** of close cases.
2. **Verbosity Bias**: Systematically inflates scores of longer, redundant answers by **0.5 to 1.5 points**.
3. **Sycophancy (Agreeableness)**: Mirrors user biases or incorrect assumptions instead of grading objectively.
4. **Heuristic Aggregation**: Relies on arbitrary formulas like:
   $$\text{Score} = 0.4 \times \text{Accuracy} + 0.3 \times \text{Reasoning} + 0.3 \times \text{Style}$$

### Speaker Notes
```text
[Timing: 0.5 minutes]
[Key point: Current LLM-as-a-judge frameworks suffer from three severe cognitive biases: position bias, verbosity bias, and sycophancy, which undermine their reliability.]
[Transition: To resolve these systemic biases, we need to move beyond simple prompts and look at the strategic incentives of the evaluation agents themselves.]
```

---

## Slide 2: The Core Concept: The GT-Judge

Instead of treating evaluation as a single-shot heuristic or a simple vote, we model it as the **equilibrium outcome of three tightly coupled strategic games**:

```
                          [Question + Answers A & B]
                                      │
                              ┌───────┴───────┐
                              │               │
                       [Evaluator 1]   [Evaluator 2]
                              │               │
                              └───────┬───────┘
                                      │
                      ┌───────────────┼───────────────┐
                      │               │               │
               [Debate Game]   [Calibration]   [Arbitration]
               (Extensive)      (Brier Score)    (Bargaining)
                      │               │               │
                      └───────────────┼───────────────┘
                                      │
                                      ▼
                             [Unified Equilibrium]
                                      │
                                      ▼
                               [Final Verdict]
```
- **The contribution is the mechanism.**
- **The proof is the convergence to a unique equilibrium.**

### Speaker Notes
```text
[Timing: 0.5 minutes]
[Key point: GT-Judge replaces single-shot heuristic scoring with the equilibrium outcome of a three-stage strategic game coupling reasoning debate, confidence calibration, and consensus bargaining.]
[Transition: Let's look closer at the first stage: the Reasoning Debate Game.]
```

---

## Slide 3: Game 1: The Reasoning Debate Game

### Extensive-Form Interaction
Two evaluator agents, Proposer ($P$) and Challenger ($C$), debate the quality of a candidate answer.
- **Roles**: Symmetrically swapped across Answer A and Answer B to eliminate position bias.
- **Actions**: $\mathcal{A} = \{\text{Defend}, \text{Attack}, \text{Counterexample}, \text{Concede}, \text{Clarify}\}$.
- **Payoff Formulations**:
  $$\mathcal{U}_P = \text{ValidClaims}(P) - \text{SuccessfulAttacks}(C) - \lambda \cdot \text{Tokens}(P)$$
  $$\mathcal{U}_C = \text{SuccessfulAttacks}(C) - \text{RefutedAttacks}(P) - \lambda \cdot \text{Tokens}(C)$$
- **Equilibrium**: Solving via backward induction shows that:
  - $P$ only defends structurally sound claims.
  - $C$ only attacks genuine flaws (cheap talk/redundant verbosity yields negative payoff).

### Speaker Notes
```text
[Timing: 1.0 minutes]
[Key point: The Reasoning Debate is an extensive-form game where a Proposer makes claims and the Challenger is paid to find and attack weaknesses, penalized by a token cost lambda to discourage verbosity.]
[Transition: Once the debate concludes, the evaluators must report their confidence, which brings us to Game 2.]
```

---

## Slide 4: Game 2: The Confidence Calibration Game

### Proper Scoring Rules
Following the debate, each evaluator agent must report a probability estimate $\hat{p} \in [0,1]$ representing their confidence that Answer A is superior.
- **Goal**: Prevent overconfident hallucinations and enforce self-knowledge.
- **Mechanism**: The judge scores confidence using the **Brier Score**:
  $$\mathcal{U}_{\text{cal}}(\hat{p}, y) = 1 - (y - \hat{p})^2$$
  where $y \in \{0, 1\}$ represents the eventual ground-truth correctness.
- **Consensus Proxy**: In deployment, the unknown ground truth $y$ is replaced by the consensus proxy $\tilde{y}$ derived from the bargaining verdict. Proper incentives are preserved under the non-dictatorship condition.

### Speaker Notes
```text
[Timing: 1.0 minutes]
[Key point: The Confidence Calibration Game uses the Brier reward rule to ensure evaluators report their true belief, using a consensus proxy to preserve proper incentives in deployment mode.]
[Transition: When these calibrated evaluators disagree, we arbitrate their dispute in the third stage.]
```

---

## Slide 5: Game 3: The Consensus Arbitration Game

### Nash Bargaining Resolution
When evaluators disagree on the final verdict, we resolve the deadlock using negotiation rather than simple majority voting.
- **Bargaining Power**: Proportional to the agent's performance in the debate game and their calibrated confidence.
- **Disagreement Point ($d_i$)**: The system utility of falling back to a costly manual human audit. Both agents suffer a penalty for failing to coordinate.
- **Optimization**:
  $$\max_{v} \prod_{i \in N} \left( \mathcal{U}_i(v) - d_i \right)^{w_i}$$
- **Impact**:
  - Leverages intensity of preferences (an agent with high calibrated confidence carries more weight).
  - Forces agents to find a consensus to avoid the costly disagreement penalty.

### Speaker Notes
```text
[Timing: 1.0 minutes]
[Key point: Disputes are solved using the Nash Bargaining Solution, weighting each evaluator's bargaining power by their debate performance and calibrated confidence to prevent tie deadlocks.]
[Transition: Let's compare our approach to prior work in the equilibrium space, specifically ECON.]
```

---

## Slide 6: How We Differ from ECON (ICML 2025)

**ECON** (*"From Debate to Equilibrium"*, ICML 2025) is the closest baseline. We build directly on its theoretical spirit but shift the paradigm:

| Dimension | ECON (ICML 2025) | GT-Judge (Ours) |
|:---|:---|:---|
| **Objective** | Improve *reasoning* (generate answer) | Improve *evaluation* (judge answers) |
| **Agent Role** | Answer generators | Answer evaluators / critics |
| **Game Style** | Cooperative Bayesian game | Adversarial debate + Bargaining |
| **Training** | Requires RL training (Q-learning) | **Training-free** (incentive prompts) |
| **Communication** | Implicit (belief updates) | Explicit (structured debate rounds) |
| **Target Biases** | None (focused on planning accuracy) | Position bias, verbosity, sycophancy |

### Speaker Notes
```text
[Timing: 0.5 minutes]
[Key point: Unlike ECON which focuses on cooperative reasoning accuracy using reinforcement learning, GT-Judge is a training-free adversarial framework targeting evaluation biases.]
[Transition: Let's examine our evaluation targets and empirical results.]
```

---

## Slide 7: Evaluation Targets \& Empirical Results

### Primary Metrics
- **Position Bias Reduction**: Measure the drop in "verdict flips" when answer order is swapped (targeting $<10\%$, down from standard $20-40\%$).
- **Verbosity Resistance**: Correlation coefficient between answer token length and judge score (targeting near-zero correlation).
- **Human Alignment**: Agreement rate (Cohen's Kappa) with human annotators on benchmark preference datasets.

### Empirical Validation (Mock Mode)
- **100% Accuracy (5/5)**: Verdicts aligned with human preference labels.
- **0.0% Position Flip Rate**: Confirmed perfect position invariance.
- **0.984 Mean Brier Reward**: Confirmed high evaluator confidence calibration.

### Speaker Notes
```text
[Timing: 1.0 minutes]
[Key point: GT-Judge was validated on a multi-domain pairwise benchmark, achieving 100% accuracy, 0.0% position flips, and a high 0.984 calibration reward in mock evaluation mode.]
[Transition: Let's discuss the key implementation challenges we solved during development.]
```

---

## Slide 8: System Implementation \& Engineering Solutions

1. **Mapping Text to Strategy Spaces**:
   - *Challenge*: LLMs output natural language text, not clean discrete actions.
   - *Solution*: Enforce strict format-mapping tags (`[ACTION: attack]`) via prompts, defaulting to clarifying/conceding moves under compliance failures.
2. **Calibrated Confidence Elicitation**:
   - *Challenge*: Proprietary logprobs are not universally available across APIs.
   - *Solution*: Extract format-constrained numerical confidence values coupled with Brier proper scoring and position-counterbalanced order shuffling.
3. **Equilibrium Computation \& Latency**:
   - *Challenge*: Sequential API calls introduce latency.
   - *Solution*: Bound debate depth ($K \le 3$), run independent debate rounds in parallel, and cache deterministic temperature-zero validity assessments.

### Speaker Notes
```text
[Timing: 1.0 minutes]
[Key point: We successfully implemented format-constrained elicitation prompts, parallel thread pools for LLM calls, and deterministic caching to minimize latency while preserving strategic invariants.]
[Transition: Finally, let's look at our project status and remaining roadmap.]
```

---

## Slide 9: Project Status \& Research Roadmap

### Completed Milestones
- [x] Formulate Extensive-Form Debate, Calibration, and Bargaining games.
- [x] Implement the 3-stage modular python pipeline.
- [x] Verify API robustness with rate-limiting exponential backoffs.
- [x] Validate benchmark accuracy and position invariance (mock mode).
- [x] Complete the academic LaTeX manuscript draft (`paper.tex`).

### Future Roadmap
- [ ] Run evaluations with live API keys on RewardBench and AlpacaEval 2.0.
- [ ] Investigate generalization of the bargaining game to listwise ranking.

### Speaker Notes
```text
[Timing: 0.5 minutes]
[Key point: All core code implementations, unit tests, and the initial LaTeX paper manuscript have been successfully completed, paving the way for live API benchmarking.]
[Transition: Thank you, and I look forward to your questions.]
```
