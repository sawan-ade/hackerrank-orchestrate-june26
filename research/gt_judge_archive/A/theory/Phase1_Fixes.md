# GT-Judge Phase 1: Fixes & Addenda

**Document**: Corrections and extensions to [GT-Judge_Phase1_Formalization.pdf](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/A/GT-Judge_Phase1_Formalization.pdf)  
**Author**: Sawan Ade  
**Date**: 2026-07-16  

---

## Fix 1: Text-to-Action Mapping (Game 1, Section 2.1)

### Problem
The action space $\mathcal{A}(h) = \{\text{claim}, \text{defend}, \text{clarify}, \text{attack}, \text{counterexample}, \text{concede}\}$ assumes discrete moves, but LLMs output continuous natural language strings. The formal game requires a bridge between the two.

### Fix: Add Assumption (A5) and Definition 7

Insert after Definition 1:

**Assumption (A5) — Action Classification.** There exists a deterministic classification function $\phi$ that maps each LLM output to a discrete action:

$$\phi: \mathcal{T} \to \mathcal{A}(h)$$

where $\mathcal{T}$ is the space of all possible text outputs.

**Definition 7 (Action Classifier).** The classification function $\phi$ is implemented via structured prompting with constrained output format. Each evaluator agent is required to preface its response with an explicit action tag:

$$\text{Output format: } \texttt{[ACTION: attack]} \; \text{followed by natural language justification}$$

The action tag is parsed deterministically. The justification text is used only for downstream validity assessment. This design choice ensures:

1. **Determinism**: $\phi$ is not a learned classifier — it is a format constraint enforced by the prompt template. The LLM *self-declares* its action.
2. **Completeness**: If the LLM fails to produce a valid tag, the system defaults to the weakest action (Proposer → clarify, Challenger → concede) and applies a penalty $\epsilon > 0$ to the agent's utility.

**Remark.** This is a standard approach in agentic LLM systems (tool-calling, function-calling). The assumption is that a sufficiently capable LLM (GPT-4o class) follows structured output instructions with >99% compliance. We verify this empirically in Phase 3.

---

## Fix 2: Endogenous Validity Score (Game 1, Section 2.2)

### Problem
Definition 2 defines $v(c) \in \{0, \delta, 1\}$ but never specifies who assigns this score. An external oracle is unrealistic; the validity must emerge from the game itself.

### Fix: Replace Definition 2 with Endogenous Validity

**Definition 2' (Endogenous Claim Validity).** The validity of claim $c$ made by the Proposer is determined by the outcome of the Challenger's interaction with that claim over the course of the debate:

$$v(c) = \begin{cases}
1 & \text{if no attack targets } c \text{ during the debate} \\
1 - \text{sev}(a^*, c) & \text{if attack } a^* \text{ targets } c \text{ and Proposer does not successfully defend} \\
v_0(c) & \text{if attack } a^* \text{ targets } c \text{ and Proposer successfully defends}
\end{cases}$$

where $v_0(c) \in [\delta, 1]$ is the pre-attack validity (initialized to 1 for new claims), and $\text{sev}(a^*, c)$ is defined by Definition 3.

**Key property**: Validity is *endogenous* — it is determined by the game dynamics, not by an external judge. An unchallenged claim retains full validity. A challenged-and-defended claim retains reduced validity $v_0(c)$. A challenged-and-undefended claim has validity $1 - \text{sev}(a^*, c)$.

**Remark.** This creates a well-defined recursive structure: the Challenger chooses which claims to attack, and the attack's success determines the validity score that feeds into the Proposer's utility. There is no circular dependency because:
- The Challenger's decision to attack depends on the *expected* severity of their attack, not on $v(c)$ itself.
- The Proposer's utility is computed at terminal histories $z \in Z$, after all attacks have resolved.

---

## Fix 3: Theorem 1 Proof — Tie-Breaking and Uniqueness

### Problem
The proof claims uniqueness of the SPNE but does not handle the boundary case $v(c) = \lambda \cdot |\text{tokens}(\text{defense})|$.

### Fix: Add tie-breaking rule and strengthen the uniqueness argument

**Assumption (A6) — Strict Tie-Breaking.** In the case of indifference, i.e., when $v(c) = \lambda \cdot |\text{tokens}(\text{defense})|$ for the Proposer or $\text{sev}(a^*, c) = \lambda \cdot |\text{tokens}(\text{attack})|$ for the Challenger, the player chooses the *passive* action (Proposer abandons, Challenger concedes).

**Justification:** This is the standard convention in extensive-form games with lexicographic preferences over (utility, effort). When the marginal utility of an action is exactly zero, the player prefers to save the effort (tokens).

Replace Equations (6)–(7) in Theorem 1 with:

$$\sigma_P^*(h) = \begin{cases}
\text{defend } c & \text{if } v(c) > \lambda \cdot \mathbb{E}[|\text{tokens}(\text{defense})|] \\
\text{abandon } c & \text{if } v(c) \leq \lambda \cdot \mathbb{E}[|\text{tokens}(\text{defense})|]
\end{cases} \tag{6'}$$

$$\sigma_C^*(h) = \begin{cases}
\text{attack } c & \text{if } \text{sev}(a^*, c) > \lambda \cdot \mathbb{E}[|\text{tokens}(\text{attack})|] \\
\text{concede} & \text{if } \text{sev}(a^*, c) \leq \lambda \cdot \mathbb{E}[|\text{tokens}(\text{attack})|]
\end{cases} \tag{7'}$$

Note the change from $>$ to $\leq$ in the abandon/concede condition (strict inequality for action, weak inequality for passivity). This ensures the strategy is **uniquely determined** at every information set, including the boundary.

**Insert into the proof** (after the Inductive Step paragraph):

> **Uniqueness at boundary:** Assumption (A6) resolves all tie-breaking cases. Combined with Assumptions (A1)–(A4), every information set in the game tree has a *unique* optimal action. By Zermelo's theorem (for finite, perfect-information games), backward induction therefore yields a unique SPNE. $\square$

---

## Fix 4: Ground Truth $y$ in Game 2 — Consensus Proxy

### Problem
The Brier score $U_{\text{cal}}(\hat{p}_i, y) = 1 - (y - \hat{p}_i)^2$ requires ground truth $y \in \{0,1\}$. In the LLM-as-a-judge setting, ground truth is unavailable at evaluation time.

### Fix: Define two operating modes with a Consensus Proxy mechanism

Insert after Section 3.2:

**Section 3.2.1 — Ground Truth Resolution**

The scoring rule requires a reference signal $y$. We define two operating modes:

**Mode 1: Benchmark Evaluation (ground truth available).**  
When evaluating on labeled datasets (MT-Bench, AlpacaEval, RewardBench), we use the human preference label as $y$. This mode is used for measuring calibration quality and benchmarking.

**Mode 2: Deployment (ground truth unavailable).**  
In deployment, we replace $y$ with a **consensus proxy** $\tilde{y}$ derived from the final bargaining outcome:

$$\tilde{y} = \begin{cases}
1 & \text{if } v^* = \text{``A wins''} \\
0 & \text{if } v^* = \text{``B wins''} \\
0.5 & \text{if } v^* = \text{``Tie''}
\end{cases} \tag{10'}$$

The modified scoring rule becomes:

$$U_{\text{cal}}^{\text{deploy}}(\hat{p}_i, \tilde{y}) = 1 - (\tilde{y} - \hat{p}_i)^2 \tag{10''}$$

**Proposition 5 (Incentive Preservation under Consensus Proxy).** Under the consensus proxy $\tilde{y}$, the evaluator's optimal strategy remains to report their true posterior belief $q_i = P(v^* = \text{``A wins''} \mid s_i)$, provided the following condition holds:

**(C1) No single agent controls the consensus.** The bargaining outcome $v^*$ depends on the weighted contributions of all agents (Eq. 24), so no individual agent can unilaterally set $\tilde{y}$ to match their own report $\hat{p}_i$.

**Proof sketch.** Suppose agent $i$ deviates by reporting $\hat{p}_i \neq q_i$. Under (C1), the consensus outcome $v^*$ (and hence $\tilde{y}$) is determined by the *joint* bargaining of all agents weighted by debate scores. Agent $i$'s report $\hat{p}_i$ influences their bargaining weight $w_i$ but does not unilaterally determine $v^*$. The agent still faces the same proper scoring incentive: report $\hat{p}_i = q_i$ to minimize their expected Brier penalty relative to the outcome $\tilde{y}$ they cannot fully control.

This is analogous to peer prediction mechanisms where the reference answer is the group consensus rather than an external ground truth (cf. Bayesian Truth Serum, Prelec 2004). $\square$

**Remark.** Condition (C1) holds naturally when $n \geq 2$ evaluators participate, since the Nash Bargaining Solution aggregates weighted inputs from all agents. In the degenerate case $n = 1$, the agent could trivially report $\hat{p}_i = 1$ and force $\tilde{y} = 1$. This is why GT-Judge requires at least 2 evaluators.

---

## Fix 5: Position Invariance — Full Formalization

### Problem
Proposition 1 is currently a proof sketch. It must be formalized.

### Fix: Replace Proposition 1 with a complete statement and proof

**Proposition 1' (Position Invariance).** Let $\pi = (Q, A, B)$ be an evaluation instance and $\pi' = (Q, B, A)$ be the order-swapped instance. Under the following conditions:

**(P1) Symmetric debate protocol**: Both answers undergo the Proposer-Challenger debate. In the first round, Evaluator 1 proposes for $A$ and Evaluator 2 challenges. In the second round, Evaluator 1 proposes for $B$ and Evaluator 2 challenges (and vice versa in the swapped instance).

**(P2) Aggregation over both rounds**: The final debate score for answer $X \in \{A, B\}$ is:

$$\text{DebateScore}(X) = \sum_{c \in C_X} v(c) - \sum_{a \in A_X} \text{sev}(a, c(a))$$

where $C_X$ is the set of claims made in favor of answer $X$ across *all* debate rounds (both when $X$ is proposed first and when $X$ is proposed second).

**Claim:** Under (P1)–(P2), $\text{GT-Judge}(\pi) = \text{GT-Judge}(\pi')$.

**Proof.** 

*Step 1 (Debate symmetry):* Under (P1), answer $A$ is proposed in round 1 of instance $\pi$ and in round 2 of instance $\pi'$. Under (P2), the debate score for $A$ aggregates over *all rounds in which $A$ is discussed*, regardless of presentation order. Therefore:

$$\text{DebateScore}(A \mid \pi) = \text{DebateScore}(A \mid \pi')$$

and similarly for $B$.

*Step 2 (Calibration independence):* Game 2 operates on the debate transcript, not on the original answer ordering. Since the debate scores are identical (Step 1), the evaluators receive the same information and produce the same posterior beliefs $q_i$.

*Step 3 (Bargaining independence):* Game 3 receives identical debate scores and calibration scores from Steps 1–2. The Nash Bargaining Solution (Eq. 24) is a deterministic function of its inputs. Therefore:

$$v^*(\pi) = v^*(\pi')$$

Hence $\text{GT-Judge}(\pi) = \text{GT-Judge}(\pi')$. $\square$

**Remark.** This invariance is *by construction* (the protocol enforces symmetry), not *by learning* (we do not train the model to be position-invariant). This is a fundamental advantage over single-judge approaches, which require post-hoc debiasing.

---

## Summary of All Changes

| Fix | Location in PDF | What Changed |
|:---|:---|:---|
| **Fix 1** | §2.1, after Def. 1 | Added Assumption (A5) and Definition 7 for text-to-action mapping via structured prompting |
| **Fix 2** | §2.2, replace Def. 2 | Made validity score endogenous (determined by attack outcomes, not external oracle) |
| **Fix 3** | §2.3, Theorem 1 proof | Added Assumption (A6) for tie-breaking; changed $>$ to $\leq$ in abandon/concede; cited Zermelo's theorem |
| **Fix 4** | §3.2, new §3.2.1 | Defined benchmark mode (human $y$) and deployment mode (consensus proxy $\tilde{y}$); proved incentive preservation |
| **Fix 5** | §5.1, replace Prop. 1 | Fully formalized position invariance with explicit debate protocol conditions and 3-step proof |
