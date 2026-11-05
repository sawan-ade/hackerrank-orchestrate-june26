# ACADEMIC TEMPLATES: TEMPLATES.md

This document serves as the repository's template library. Use these blocks to maintain formatting consistency across documents, code, and papers.

---

## 1. Theorem Template

```markdown
### Theorem [Number] [Theorem Title]
**Assumptions**: Let the following conditions hold:
1. $C_1$: [State assumption 1, e.g., finite action space]
2. $C_2$: [State assumption 2, e.g., symmetric information distribution]
**Claim**:
[State the exact mathematical claim, e.g., "Truthful evaluation is the unique Bayesian Nash Equilibrium."]
```

---

## 2. Proof Template

```markdown
### Proof of Theorem [Number]
**Proof Structure**: [Direct proof / Contradiction / Mathematical induction / Construction]

**Step 1: Setting up expectation values**
Write down the expected utility equation under strategy $s_i$:
$$\mathbb{E}[\mathcal{U}_i(s_i)] = \sum_{\theta \in \Theta} P(\theta) \mathcal{U}_i(s_i, \theta)$$

**Step 2: Taking the derivative / maximizing**
Find the first-order condition (FOC) or show dominant strategy:
$$\frac{\partial \mathbb{E}[\mathcal{U}_i]}{\partial \hat{p}_i} = 0 \implies \hat{p}_i = \mathbb{E}[\theta]$$

**Step 3: Uniqueness**
Prove that any deviation $s_i' \neq s_i^*$ yields strictly less utility:
$$\mathbb{E}[\mathcal{U}_i(s_i^*)] - \mathbb{E}[\mathcal{U}_i(s_i')] > 0$$
Thus, $s_i^*$ is the unique Nash Equilibrium. $\blacksquare$
```

---

## 3. Algorithm Template

```markdown
### Algorithm [Number]: [Algorithm Name]

**Input**:
- $Q$: Question text.
- $A, B$: Candidate answers.
- $K$: Maximum debate rounds.

**Output**:
- $v^* \in \{A, B, \text{Tie}\}$: Final consensus verdict.

**Procedure**:
1. Initialize debate state: $S_0 \leftarrow \{Q, A, B\}$.
2. **For** $t = 1$ to $K$ **do**:
   a. Proposer generates claim $c_t \leftarrow \text{LLM}(S_{t-1}, \text{role}=\text{Proposer})$.
   b. Challenger generates attack $a_t \leftarrow \text{LLM}(S_{t-1} \cup \{c_t\}, \text{role}=\text{Challenger})$.
   c. Update state: $S_t \leftarrow S_{t-1} \cup \{c_t, a_t\}$.
3. Compute debate scores based on surviving claims.
4. Extract calibrated confidence metrics $\hat{p}_1, \hat{p}_2$.
5. Solve Nash Bargaining:
   $$v^* \leftarrow \arg\max_v \prod (U_i(v) - d_i)$$
6. **Return** $v^*$.
```

---

## 4. Experiment Template

```markdown
### [EXP-ID] — [Experiment Name]
- **Objective**: [1 sentence goal]
- **Hypothesis**: [If X is changed, then Y will improve because...]
- **Datasets**: [Name and size of the dataset]
- **Models**: [Evaluator backend models used]
- **Baselines**: [Baselines for comparison]
- **Hyperparameters**: [Temperature, max tokens, system prompt seed]
- **Metrics**: [Definition of metrics used]
- **Expected Outcome**: [Predicted results]
- **Observed Outcome**: [Actual numbers, tables, or charts]
- **Discussion**: [Explanation of the gap between expected and observed results]
- **Failure Analysis**: [Detail why runs failed or where anomalies occurred]
- **Code Link**: [Link to the execution script]
```

---

## 5. Paper Review Template

Use the review format defined in [reviewer.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/reviewer.md#L30-L58).
