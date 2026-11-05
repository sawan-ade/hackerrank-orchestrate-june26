# MATHEMATICAL NOTATION DICTIONARY: NOTATION.md

This document serves as the single source of truth for mathematical symbols used across paper drafts, proofs, algorithms, and configurations. Never redefine these symbols without updating this registry.

---

## 1. Game-Theoretic Framework Symbols

| Symbol | Mathematical Object | Description | Standard Usage |
|:---|:---|:---|:---|
| $G$ | Game structure | $G = \langle N, \{\mathcal{A}_i\}, \{\mathcal{U}_i\}, \Theta, P \rangle$ | Represents the overall evaluation game |
| $N$ | Player Set | $N = \{1, 2, \dots, n\}$ | The set of active agent players (Proposer, Challenger) |
| $\mathcal{A}_i$ | Action Space | The set of discrete moves available to agent $i$ | $\mathcal{A}_i = \{\text{Defend}, \text{Attack}, \text{Concede}\}$ |
| $s_i$ | Strategy | A policy mapping an information state to an action | $s_i \in \mathcal{S}_i$ |
| $s_{-i}$ | Opponent Strategies | Strategy profile of all players except player $i$ | $\mathcal{U}_i(s_i, s_{-i})$ |
| $\mathcal{U}_i$ | Utility Function | Payoff mapping strategy profiles to real values | $\mathcal{U}_i: \mathcal{S} \to \mathbb{R}$ |
| $\theta$ | Quality State | True quality of candidate answer: $\theta \in \{0, 1\}$ | $\theta = 1$ (Valid), $\theta = 0$ (Invalid) |
| $P$ | Prior Beliefs | Probability distribution over state space $\Theta$ | $P(\theta)$ |
| $\hat{p}_i$ | Reported Confidence | Agent $i$'s reported probability estimate that Answer A wins | $\hat{p}_i \in [0, 1]$ |
| $y$ | Ground Truth | Indicator variable for candidate answer correctness | $y \in \{0, 1\}$ |
| $\lambda$ | Cost Penalty | Token or computational cost factor | $\lambda \cdot \text{Tokens}(i)$ |

---

## 2. Bargaining & Calibration Symbols

| Symbol | Mathematical Object | Description | Standard Usage |
|:---|:---|:---|:---|
| $v$ | Verdict | Outcome of the consensus negotiation | $v \in \{\text{A wins}, \text{B wins}, \text{Tie}\}$ |
| $d_i$ | Disagreement Point | Utility of player $i$ when consensus bargaining fails | $d_i \in \mathbb{R}$ (represents fallback cost) |
| $w_i$ | Bargaining Weight | Negotiating power of agent $i$ derived from game metrics | $w_i = f(\text{DebateScore}_i, \hat{p}_i)$ |
| $U_{\text{cal}}$ | Calibration Utility | Utility function for proper scoring | $\mathcal{U}_{\text{cal}}(\hat{p}, y) = 1 - (y - \hat{p})^2$ |
| $q^*$ | Inspection Rate | Mixed strategy probability of auditing in inspection game | $q^* = \frac{V}{V+F}$ |

---

## 3. Policy on Modifications
1.  Any changes to these symbols must be documented in [CHANGELOG.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/CHANGELOG.md).
2.  If an agent or human researcher needs to introduce a new symbol (e.g., for visual attention, retriever query depth), it must be appended here first to avoid clashes.
