# RESEARCH WORKFLOW: paper-workflow.md

This document guides the research team from initial concept to the camera-ready version. It outlines the requirements and checklists for each stage.

```
Research Idea ──→ Lit Review ──→ Research Gap ──→ Novel Contribution
      │
      ▼
Mathematical Formulation ──→ Mechanism Design ──→ Algorithm Design
      │
      ▼
Implementation ──→ Experiments & Ablations ──→ Paper Writing & Review Simulation
      │
      ▼
Revision & Resubmission ──→ Camera-Ready Publication
```

---

## Phase 1: Inception & Theoretical Alignment

### 1. Research Idea & Ideation
- [ ] Define the core problem statement clearly. What is the specific LLM judge failure mode (sycophancy, position bias, or verbosity bias) targeted?
- [ ] Draft an informal one-sentence hypothesis explaining why the proposed game mechanics address this failure mode.
- [ ] Estimate initial computation/token costs. Will the mechanism require multiple rounds of frontier models, and is this cost acceptable?

### 2. Literature Review & Reference Mapping
- [ ] Search for at least 15 recent papers (NeurIPS, ICML, ICLR, AAAI, ACL, EMNLP) covering LLM judges, multi-agent debate, and peer prediction.
- [ ] Populate [REFERENCES.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/REFERENCES.md) with detailed analyses of the closest works.
- [ ] Check ICLR/ICML oral listings to ensure no overlapping work has been published within the last 6 months.

### 3. Identifying the Research Gap
- [ ] Explicitly state what existing frameworks fail to do (e.g., "ECON ICML 2025 targets cooperative reasoning, not adversarial evaluation; Peer Prediction ICLR 2026 targets model training, not multi-agent judging").
- [ ] Prove that the gap is significant and not just a minor engineering variation.

### 4. Novel Contribution Statement
- [ ] Write a 150-word abstract paragraph detailing the primary theoretical and empirical contributions of the paper.
- [ ] Get sign-off from Dr. Rahul Mishra and Ashutosh Kumar Sinha on the novelty vector.

---

## Phase 2: Mathematical Formalization

### 5. Game-Theoretic Formulation
- [ ] Define players, action space, utility functions, and type distributions.
- [ ] Ensure all notation is logged and mapped directly to [NOTATION.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/NOTATION.md).
- [ ] Validate that utilities are well-bounded and continuous/discrete strategy mappings are clear.

### 6. Mechanism Design & Equilibrium Analysis
- [ ] Write down the formal definitions of equilibrium (e.g., SPNE, BNE).
- [ ] Prove Theorem 1: Truthful reporting is a Nash Equilibrium.
- [ ] Prove Theorem 2: Collusion resistance (e.g., coordination on false consensus yields strictly lower payoffs than truthfulness).
- [ ] Conduct a mathematical review with peers to search for missing assumptions.

### 7. Algorithm Design
- [ ] Translate the game mechanics into a step-by-step algorithm (e.g., GT-Judge state machine).
- [ ] Calculate the asymptotic time and space complexity of the game solver (e.g., backward induction depth $K$).
- [ ] Define convergence thresholds and early-stopping constraints.

---

## Phase 3: Empirical Validation

### 8. Implementation
- [ ] Initialize code following the standards in [repository-guide.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/repository-guide.md).
- [ ] Implement configurations using YAML files. Avoid hardcoding payoffs or agent roles.
- [ ] Write basic unit tests to verify that agents execute moves exactly as defined by the strategy space.

### 9. Experiments & Benchmarking
- [ ] Run evaluations on MT-Bench, AlpacaEval 2.0, and RewardBench.
- [ ] Register all runs in [EXPERIMENTS.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/EXPERIMENTS.md).
- [ ] Log raw trajectories, model prompts, and agent consensus negotiations.
- [ ] Compute standard deviation and run statistical significance t-tests.

### 10. Ablation Studies
- [ ] Test the pipeline with components removed:
  - [ ] No debate round (direct evaluation with calibration).
  - [ ] No calibration round (direct voting debate).
  - [ ] No Nash Bargaining (majority voting instead).
- [ ] Measure the accuracy-cost frontier across different model backends (e.g., GPT-4o vs. GPT-4o-mini).

---

## Phase 4: Writing & Peer-Review Simulation

### 11. Manuscript Drafting
- [ ] Write sections sequentially: Introduction, Related Work, Theoretical Framework, Experiments, Discussion, and Conclusion.
- [ ] Ensure all figures are compiled as vector graphics (PDF/SVG) and stored in `figures/`.
- [ ] Verify that all citations are formatted correctly using the style file of the target venue.

### 12. Reviewer Simulation (Reviewer #2)
- [ ] Run the reviewer simulation template in [reviewer.md](file:///c:/Users/Sawan/Desktop/New%20folder%20%284%29/hackerrank-orchestrate-june26/reviewer.md).
- [ ] Address all concerns regarding missing baseline comparisons, token overhead, and edge cases.
- [ ] Refine writing to maximize clarity and precision.

### 13. Submission & Camera-Ready
- [ ] Package the codebase with a `README.md` and seed files to guarantee 100% reproducibility.
- [ ] Upload the paper manuscript and supplementary materials to the submission portal.
- [ ] Upon acceptance, address all reviewer feedback and update the final camera-ready version.
