# LITERATURE INDEX: REFERENCES.md

This registry tracks the core reference papers that ground the GT-Judge framework. Every reference lists the summary, strengths, weaknesses, research gaps, and our explicit differences.

---

## 1. Core Reference Papers

### [Ref-001] — From Debate to Equilibrium: Belief-Driven Multi-Agent LLM Reasoning via Bayesian Nash Equilibrium (ECON)
- **Citation**: Yi Xie, Zhanke Zhou, Chentao Cao, Qiyu Niu, Liang Liu, and Bo Han. *International Conference on Machine Learning (ICML 2025)*.
- **Summary**: Introduces the ECON framework, which models multi-agent LLM reasoning as an incomplete-information game. It uses a hierarchy of a Coordinator LLM generating compact strategies and Executor LLMs updating local beliefs, seeking a Bayesian Nash Equilibrium (BNE) via reinforcement learning to avoid message-passing token overhead.
- **Strengths**: Solid theoretical framing of LLM coordination; proves BNE convergence; reduces communication token cost by $21.4\%$; achieves strong improvements on SVAMP and MATH.
- **Weaknesses**: Requires active RL Q-learning training to optimize reward weights (alpha logits); assumes a cooperative multi-agent environment; is not designed to detect or mitigate evaluator biases.
- **Research Gap**: Multi-agent game theory has not been applied to adversarial *evaluation* (LLM-as-a-Judge) where the primary challenge is not correctness but bias mitigation (position, length, sycophancy).
- **How GT-Judge Differs**:
  - GT-Judge is **training-free** (zero RL overhead); it operates purely on prompt incentives and game structures.
  - The game is **adversarial** (Proposer vs. Challenger) rather than cooperative.
  - We explicitly target and evaluate the reduction of position bias, verbosity bias, and sycophancy.

---

### [Ref-002] — Truthfulness Despite Weak Supervision: Evaluating and Training LLMs Using Peer Prediction
- **Citation**: Anonymous. *International Conference on Learning Representations (ICLR 2026)*.
- **Summary**: Proposes a peer prediction mechanism to evaluate and train LLMs under weak supervision without relying on ground-truth labels. The payoff function maximizes the mutual information between the outputs of peer agents to incentivize truthful answers.
- **Strengths**: Grounded in classic mechanism design (Bayesian Truth Serum); does not require gold-standard labels to evaluate model truthfulness; mathematically proves truthfulness is the unique Nash Equilibrium.
- **Weaknesses**: Focuses on evaluation at the *training/fine-tuning* level; does not detail how to build an active, multi-agent judging pipeline for complex reasoning tasks.
- **Research Gap**: Using peer prediction to audit the reasoning chains of competitive models in an online, interactive multi-agent debate setting.
- **How GT-Judge Differs**:
  - We use peer calibration (proper scoring rules) online *during the evaluation process* to score evaluator confidence.
  - We integrate peer prediction concepts into a larger pipeline containing active debate and bargaining phases.

---

### [Ref-003] — TrustJudge: Inconsistencies of LLM-as-a-Judge and How to Alleviate Them
- **Citation**: Anonymous. *International Conference on Learning Representations (ICLR 2026)*.
- **Summary**: Systematically identifies and catalogs inconsistencies in LLM-as-a-judge evaluations, highlighting vulnerabilities to style bias, position bias, and self-preference.
- **Strengths**: Excellent empirical analysis of current judge failure modes; establishes a solid baseline for measuring judge alignment.
- **Weaknesses**: Offers mechanical heuristics (shuffling prompts, verbalizer engineering) rather than a unified theoretical mechanism to solve the underlying incentive problems.
- **Research Gap**: Lacks a game-theoretic or multi-agent solution targeting the root cause of these biases.
- **How GT-Judge Differs**:
  - We replace mechanical prompt heuristics with a game-theoretic architecture where these biases are neutralized by design (e.g., Challenger agents are rewarded for highlighting verbosity, role swaps neutralize position bias).
