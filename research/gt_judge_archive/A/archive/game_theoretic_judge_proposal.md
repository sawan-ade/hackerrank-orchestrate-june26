# Research Proposal: Bayesian Peer-Adjudication: A Collusion-Resistant Mechanism for Multi-Agent Evaluators

**Author:** Sawan Ade  
**Affiliations:** Indian Institute of Science Education and Research (IISER), Bhopal & Indian Institute of Technology (IIT), Patna  
**Target Venue:** NeurIPS / ICLR / AAMAS  

---

## Abstract
Modern automated evaluation systems rely heavily on Large Language Models (LLMs) acting as single-shot judges (e.g., "LLM-as-a-judge"), aggregating static heuristic scores such as $\text{Score} = \alpha \text{Accuracy} + \beta \text{Reasoning}$. Such setups are fundamentally vulnerable to strategic manipulation, including hallucinated facts, overconfident assertions, and structural deception. While multi-agent debate (MAD) frameworks have been proposed to mitigate this, they assume cooperative agents and fail in the presence of **information asymmetry, strategic collusion, and moral hazard (verification laziness)**. 

This proposal introduces **Bayesian Peer-Adjudication (BPA)**, a game-theoretic mechanism that models the evaluation network (Retriever, Reasoner, Verifier, Critic) as players in a non-cooperative game. Instead of heuristic scoring, the final adjudication is the **equilibrium outcome** of seven interconnected subgames (Reasoning, Evidence, Calibration, Consensus, Cost, Robustness, and Safety). We prove that by structuring agent payoffs using **strictly proper scoring rules** and **peer prediction**, we can guarantee that truthful reporting and diligent auditing constitute a unique Bayesian Nash Equilibrium (BNE), even under severe token-cost constraints.

---

## 1. Introduction & Motivation
As LLMs and Vision-Language Models (VLMs) scale, they are increasingly deployed as autonomous evaluators—or "Judges"—adjudicating claims, auditing code, and grading complex reasoning chains. However, treating evaluation as a single-shot query or a weighted average of subjective criteria ignores the strategic nature of LLM outputs. 

In a multi-agent system:
- A **Retriever** and a **Reasoner** might collude to produce a highly plausible but factually incorrect response if their joint utility function penalizes token search cost more than errors.
- A **Verifier** might experience **moral hazard** (verification laziness), choosing to approve a reasoning step without verifying its claims because conducting a VLM audit or external search incurs high computational cost (tokens, latency).

To address these challenges, we must transition from **heuristic aggregation** to **mechanism design**. We propose a multi-agent evaluator where the judge does not decide the winner immediately. Instead, the final judgment is the equilibrium of a game played by strategic LLM agents.

---

## 2. Literature Review & A* Verification
Our proposed framework merges economic mechanism design with multi-agent reasoning, grounded in top-tier literature:

1. **Peer Prediction without Ground Truth**:
   * *Foundations*: Prelec (2004) (*Science*) introduced the **Bayesian Truth Serum (BTS)**, showing that honest reporting can be incentivized by rewarding agents whose reports are "more common than collectively predicted." Miller et al. (2005) (*Management Science*) proved that proper peer scoring rules can elicit truthful information under asymmetric information.
   * *LLM Application*: Recent publications at *NeurIPS 2024* and *ICLR 2025* apply peer prediction to evaluate LLM truthfulness under weak supervision, showing that mutual information maximization discourages models from generating sycophantic or deceptive responses.

2. **Belief-Driven Game Theory in LLM Debate**:
   * *State-of-the-Art*: *ICML 2025: "From Debate to Equilibrium: Belief-Driven Multi-Agent LLM Reasoning via Bayesian Nash Equilibrium" (ECON framework)* models LLM debates as incomplete-information games. ECON shows that rather than running endless, costly multi-round conversational debates, agents can maintain probability distributions (beliefs) about other agents' knowledge. Seeking a **Bayesian Nash Equilibrium (BNE)** saves 21.4% in tokens while improving planning accuracy by 11.2%.

3. **Scalable Oversight & Adversarial Adjudication**:
   * *Prior Work*: OpenAI's *Debate Game* (Irving et al., 2018) frames safety evaluation as a game where two agents debate, and a weaker judge adjudicates. They prove that competition between agents amplifies the visibility of logical and factual flaws, making verification easier for the judge.

---

## 3. The Bayesian Peer-Adjudication Game Model (BPAG)
We formalize the evaluation network as a game:
$$G = \langle N, \{\mathcal{A}_i\}, \{\mathcal{U}_i\}, \Theta, P \rangle$$

Where:
- $N = \{\text{Proposer}, \text{Opponent}, \text{Retriever}, \text{Verifier}, \text{Critic}\}$ are the players.
- $\mathcal{A}_i$ is the action space of player $i$ (e.g., submitting claims, searching databases, raising objections, abstaining).
- $\Theta = \{\theta_0, \theta_1\}$ is the state space representing the true quality of the reasoning (0 = Invalid, 1 = Valid).
- $P$ is the prior probability distribution over $\Theta$.

```
                      [Claimant / Proposer] 
                         (Private Type θ)
                               |
                        [Submit Signal]
                               |
                     [Bayesian Peer-Adjudication]
                      /        |         \
         [Reasoning Game] [Evidence Game] [Calibration Game]
                \              |         /
                 \             |        /
                [Consensus Bargaining Game]
                               |
                  [Equilibrium Solution (BNE)]
                               |
                 [Final Adjudication Verdict]
```

### The 7 Subgames: Strategic Formulations

#### Game 1: The Reasoning Game (Extensive-Form Debate)
Let two agents, Proposer ($P$) and Opponent ($O$), engage in an alternating-turn debate over a reasoning trace.
- **Strategies**: $s_P, s_O \in \{\text{Defend}, \text{Attack}, \text{Counterexample}, \text{Contradict}\}$.
- **Payoffs**: The utility of the Proposer decreases with the number of logically valid contradictions identified by the Opponent.
  $$\mathcal{U}_P(s_P, s_O) = \text{Consistency}(s_P) - \mathbb{I}(\text{Contradiction}(s_O))$$

#### Game 2: The Evidence Game (Auditing Game)
To verify factual claims, the Retriever submits claim-evidence pairs, and the Verifier decides whether to execute a costly audit.
- **Verifier Cost**: Incurs a cognitive/token cost $C_V > 0$.
- **Adversarial Payoffs**: If the Retriever submits a fabricated claim and the Verifier trusts, the Retriever gains $R_{\text{fraud}}$ and the system suffers loss $L$. If audited and caught, the Retriever incurs penalty $F$.
- We calculate the mixed-strategy Nash Equilibrium to define the **optimal inspection rate** $q^*$ which deters hallucination while minimizing token expenditure.

#### Game 3: The Confidence Calibration Game (Proper Scoring Rules)
Agents must report a probability estimate $\hat{p} \in [0, 1]$ representing their confidence in the answer.
- To prevent overconfident hallucination, the Judge scores the reported confidence using the **Brier Score** (a strictly proper scoring rule):
  $$\mathcal{U}_{\text{calibration}}(\hat{p}, y) = 1 - (y - \hat{p})^2$$
  where $y \in \{0, 1\}$ is the actual correctness of the answer.
- **Theorem**: An agent maximizes its expected utility if and only if it reports its true belief, i.e., $\hat{p} = \mathbb{E}[y]$.

#### Game 4: The Agreement / Consensus Game (Bargaining Game)
When agents (e.g., Retriever, Reasoner, Verifier) disagree, we resolve the deadlock by modeling their negotiation as a **Nash Bargaining Game**. The agents negotiate to maximize the Nash product:
  $$\max_{x \in \mathcal{S}} \prod_{i \in N} \left( \mathcal{U}_i(x) - d_i \right)$$
where $d_i$ is the disagreement point (the utility of falling back to a costly manual human audit).

#### Game 5: The Cost Game (Pareto Frontier)
We define the system utility as an optimization of accuracy versus inference cost:
  $$\mathcal{U}_{\text{system}} = \text{Accuracy}(\text{Equilibrium}) - \lambda \sum_{i \in N} \text{Tokens}(i)$$
This discourages agents from running infinitely long CoT chains unless the marginal utility in accuracy exceeds the marginal token cost.

#### Game 6: The Robustness Game (Adversarial Zero-Sum)
We model this as a zero-sum game between an **Attacker** (applying adversarial semantic perturbations to the query) and the **Multi-Agent Judge**. The system's utility is evaluated at the minimax point:
  $$\min_{\text{Perturbation}} \max_{\text{Judge}} \mathcal{U}_{\text{system}}$$

#### Game 7: The Safety Game (Infinite Barrier)
We model safety as a binary constraint multiplier $S \in \{0, 1\}$:
  $$\mathcal{U}_{\text{final}} = S \cdot \left( \sum \omega_j \mathcal{U}_j \right)$$
If any agent output triggers a policy violation, $S = 0$, reducing the final utility to zero regardless of logical strength.

---

## 4. Addressing Strategic Collusion & Moral Hazard
Our main theoretical contribution is introducing a mechanism to prevent **systemic collusion** (where agents agree on a false consensus to minimize token penalties) and **moral hazard** (where the Verifier skips audits to save tokens).

### 4.1 Peer-Adjudication Payoff Structure
To ensure incentive compatibility, we implement a **Correlated Agreement (CA)** mechanism:
1. The **Verifier** and an independent **Critic** are assigned to inspect the Proposer's reasoning trace. They do not communicate.
2. The Judge pays the Verifier based on their report $r_V \in \{\text{Accept}, \text{Reject}\}$ correlated with the Critic's report $r_C$:
   $$\text{Payoff}(r_V, r_C) = \begin{cases} 
   S(r_V) & \text{if } r_V = r_C \\
   0 & \text{if } r_V \neq r_C 
   \end{cases}$$
3. Under the CA mechanism, if the prior beliefs of the Verifier and Critic are correlated, the unique Nash Equilibrium that maximizes expected payoffs is for both agents to perform diligent, honest inspections and report their true observations.

---

## 5. Research Complexity & Open Challenges
To successfully execute this thesis, three major complexities must be resolved:

1. **Continuous-to-Discrete Mapping (High-Dimensional Strategy Spaces)**:
   * *Challenge*: LLM outputs are continuous strings of text. Translating natural language arguments into discrete actions (e.g., "Attack") is non-trivial.
   * *Research Direction*: We must use semantic parser models to construct an **Argumentation Graph** (Dung's abstract argumentation), mapping text nodes to attack/defeat relations.
2. **Equilibrium Computation in Incomplete Information Games**:
   * *Challenge*: Solving for a Bayesian Nash Equilibrium in games with high-dimensional beliefs is computationally expensive.
   * *Research Direction*: We will investigate the use of **fictitious play** and **Counterfactual Regret Minimization (CFR)** approximations, operating over abstract semantic strategies.
3. **Cognitive Cost Modeling**:
   * *Challenge*: Defining the cost of LLM "effort" ($C_V$).
   * *Research Direction*: We will parameterize the cost function as a function of prompt tokens and model parameter size (e.g., using GPT-4o carries a higher cost than GPT-4o-mini).

---

## 6. Research Roadmap & Proposed Schedule
1. **Month 1-2: Theoretical Formulation & Argument Parsing**
   - Formalize the Bayesian Peer-Adjudication game matrices.
   - Build a semantic parser using LangChain/LangGraph to map text arguments to a directed graph.
2. **Month 3-4: Subgame Simulation**
   - Implement simulations for the *Reasoning Game* and *Evidence Game* in Python.
   - Run experiments using simulated agents to evaluate equilibrium convergence.
3. **Month 5-6: Evaluation & Benchmarking**
   - Benchmark the Game-Theoretic Judge against standard LLM-as-a-judge baselines on benchmarks (e.g., MMLU-Pro, GSM8k, and HackerRank claims data).
   - Write and submit the paper to NeurIPS/ICML.
