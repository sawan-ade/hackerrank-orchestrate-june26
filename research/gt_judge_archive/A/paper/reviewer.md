# REVIEWER SIMULATOR: reviewer.md

This document serves as an automated simulator for peer reviewers from top-tier AI conferences. Use this template to self-audit draft manuscripts before submission.

---

## 1. Conference Persona Guidelines

### NeurIPS / ICML / ICLR (Machine Learning Focus)
*   **Core Expectation**: Rigorous mathematical foundation, generalizable theorems, clear equilibrium proofs, and extensive benchmark results on diverse tasks.
*   **Key Critique Points**: 
    - "Is the equilibrium actually computable in polynomial time, or is it NP-hard?"
    - "The experiments only compare against standard API judges; they lack comparison with advanced multi-agent baselines like CollabEval or ECON."
    - "Does the theorem assume homogeneous agents or heterogeneous ones?"

### ACL / EMNLP (Natural Language Processing Focus)
*   **Core Expectation**: Understanding of linguistic nuance, alignment with human preferences, robustness against text formatting/verbosity, and scaling analysis across open vs. closed models.
*   **Key Critique Points**:
    - "How does the argumentation graph handle informal language or semantic ambiguity?"
    - "The paper claims to reduce verbosity bias, but lacks statistical tests showing correlation coefficient differences."
    - "Provide qualitative examples of the debate rounds showing what claims are successfully attacked."

### AAAI (Artificial Intelligence Focus)
*   **Core Expectation**: Practical problem solving, solid system implementation, multi-agent coordination, and a clear story bridging theory and application.
*   **Key Critique Points**:
    - "Is this framework limited to pairwise evaluation, or can it generalize to listwise evaluation?"
    - "What is the token cost overhead compared to single-agent evaluations? The practical trade-off is not fully explored."

---

## 2. Review Scoring Rubric

### 2.1 Technical Criteria
For each category, score from **1 (Poor)** to **5 (Outstanding)**:

1.  **Novelty (1-5)**: Does the paper introduce a genuinely new mechanism (e.g., proper scoring rules + Nash bargaining for judging), or is it an incremental application of existing work?
2.  **Mathematical Rigor (1-5)**: Are the assumptions clearly stated? Are the proofs correct and complete?
3.  **Experimental Quality (1-5)**: Are the baselines strong? Are human labels included for validation? Are confidence intervals reported?
4.  **Writing Clarity (1-5)**: Is the paper easy to read? Are equations and notation consistent with [NOTATION.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/NOTATION.md)?
5.  **Reproducibility (1-5)**: Are hyperparameters, prompt templates, and code implementation details provided?

### 2.2 Recommendation Outcomes
- **Strong Accept (Score: 8-10)**: Clear novelty, bulletproof proofs, comprehensive empirical results, and highly readable text.
- **Weak Accept (Score: 6-7)**: Good idea, solid experiments, but minor gaps in the theory or writing clarity.
- **Weak Reject (Score: 4-5)**: Gaps in baselines, missing mathematical assumptions, or questionable real-world token-cost viability.
- **Strong Reject (Score: 1-3)**: Incorrect proofs, incremental novelty, or lack of rigorous evaluation.

---

## 3. Reviewer Simulation Template

Use the following template to write a critique of a paper draft.

```markdown
# PEER REVIEW REPORT

**Target Venue**: [NeurIPS / ICML / ICLR / ACL / EMNLP / AAAI]
**Reviewer ID**: Reviewer #2 (Autonomous System Auditor)

---

## Summary of the Paper
[Provide a 3-sentence summary of the paper's goals, mechanism, and empirical findings.]

## Strengths
1. [Theoretical Strength, e.g., formalizing the evaluation pipeline as a 3-game system.]
2. [Empirical Strength, e.g., significant reduction of position bias on MT-Bench.]
3. [Clarity, e.g., high-quality figures and well-structured roadmap.]

## Weaknesses & Critical Questions
1. **Mathematical Assumption Gaps**:
   * *Question*: In Theorem [X], you assume signal independence. However, LLM evaluators often draw from similar pre-training distributions. What happens to the Brier score calibration under correlated prior beliefs?
2. **Computational Overhead / Cost**:
   * *Question*: The 3-stage game requires multiple rounds of debate and calibration. What is the average token cost per query compared to a single-shot GPT-4o judge? Provide a table showing the cost-performance frontier.
3. **Robustness to Strategy Space Space**:
   * *Question*: LLMs do not output pure strategies; they produce natural language strings. How does the system map a continuous, ambiguous sentence to a discrete action in the payoff matrix?
4. **Baseline Comparisons**:
   * *Question*: Why is the proposed system not compared against [specific state-of-the-art multi-agent judge baseline]?

## Evaluation Scores
*   **Soundness**: [1-4 (Poor, Fair, Good, Excellent)]
*   **Presentation**: [1-4]
*   **Contribution**: [1-4]
*   **Overall Recommendation**: [1-10 (Strong Reject to Strong Accept)]
*   **Confidence**: [1-5 (Low to Expert)]

## Detailed Comments & Typos
- [List specific line numbers with suggestions or typos.]
```
