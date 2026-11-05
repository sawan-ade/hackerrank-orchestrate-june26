# RESEARCH NORTH STAR: RESEARCH_COMPASS.md

This document serves as the permanent strategic anchor for the repository. All contributions, design decisions, and papers must align with the vision set here.

---

## 1. Why This Project Exists

Evaluation is the bottleneck of AI development. As LLMs scale to complex, agentic tasks, standard reference-based metrics (ROUGE, BLEU) fail completely. Humans are too slow and expensive to evaluate large-scale outputs. Consequently, the industry has turned to **LLM-as-a-Judge**.
However, LLM judges suffer from systemic, human-like biases (position bias, length bias, sycophancy) and security flaws (jailbreaks, preference contamination). 
This project exists to **formalize automated evaluation using game theory**, converting LLM evaluation from a prompt-engineering hack into a mathematically proven science.

---

## 2. What Problem We Are Solving

We solve the **strategic manipulation and bias in automated evaluators**.
In any system where models or humans are graded by an automated LLM judge:
1.  **Exaggeration/Fraud**: Generators are incentivized to produce highly verbose, pleasing, but logically hollow answers (reward hacking).
2.  **Verifier Laziness (Moral Hazard)**: Evaluator agents face computational and token costs to audit long reasoning paths, leading them to default to lazy acceptance.
3.  **Position & Style Arbitrariness**: A judge's decision fluctuates based on layout details rather than semantic quality.

By framing evaluation as a non-cooperative game with formal incentives, we guarantee that **honesty and calibration constitute the unique Nash Equilibrium**.

---

## 3. What Makes Us Different

| Dimension | Standard LLM-as-a-Judge | Our GT-Judge |
|:---|:---|:---|
| **Core Paradigm** | Prompt Engineering / Subjective Rubrics | Game-Theoretic Mechanism Design |
| **Outcomes** | Point scoring (uncalibrated) | Nash Equilibrium (provable stability) |
| **Disagreement Solution** | Majority voting or averaging | Nash Bargaining Resolution |
| **Overconfidence Fix** | None (highly overconfident) | Strictly Proper Scoring Rules (Brier Score) |
| **Audit Verification** | Assume perfect verification | Mixed-strategy auditing game thresholds |

---

## 4. Key Competitors & Baseline Literature

1.  **ECON: "From Debate to Equilibrium" (ICML 2025)**:
    - *Their focus*: Cooperative multi-agent coordination to solve math problems.
    - *Our difference*: Adversarial evaluation to judge quality and eliminate bias.
2.  **CollabEval (Amazon Science 2025)**:
    - *Their focus*: Collaborative chat discussion for consensus.
    - *Our difference*: Game-theoretic payoffs and formal bargaining theory instead of unstructured conversation.
3.  **J1: "Incentivizing Thinking in LLM-as-a-Judge via RL" (ICLR 2026)**:
    - *Their focus*: Using RL training to make judges think longer.
    - *Our difference*: Training-free mechanism design where prompts + game rules enforce calibration.

---

## 5. Definition of Success

Our target is to establish a framework that meets the following criteria:
1.  **A* Publication**: Acceptances at AAAI 2027, AAMAS 2027, or ACL/EMNLP 2027.
2.  **Position Bias Elimination**: GT-Judge reduces the position flip rate to **$<8\%$** (down from $20-40\%$).
3.  **Verbosity Neutrality**: Pearson correlation between answer length and judge scores is **$<0.15$** (down from $>0.6$).
4.  **High Human Alignment**: Agreement with human gold labels exceeds **$86\%$** on standard preference datasets.

---

## 6. Immutable Core (What Must Never Be Changed)

-   **Payoffs Over Prompts**: The final verdict must always be derived from mathematical payoffs and equilibria, never from a single prompt asking "Who wins?".
-   **Calibration is Mandatory**: Evaluators must always undergo calibration scoring (proper scoring rules) to prevent uncalibrated assertions.
-   **Adversarial Debate Structure**: Evaluation must involve an active challenger agent whose reward increases by finding valid flaws. Single-agent evaluations are prohibited.
