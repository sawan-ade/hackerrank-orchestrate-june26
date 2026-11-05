# GT-Judge — Folder A (Project Root)

All materials for the **Game-Theoretic Multi-Agent LLM-as-a-Judge** paper live here.

---

## 📂 Directory Map

```
A/
├── paper/                         # Paper writing & research planning
│   ├── SELECTED_PAPER.md          # The 3-game GT-Judge research plan
│   ├── RESEARCH_COMPASS.md        # North star: mission, success criteria
│   ├── REFERENCES.md              # Literature index (ECON, TrustJudge, etc.)
│   ├── DECISIONS.md               # Scientific design decision log
│   ├── MEETING_NOTES.md           # Supervisor meeting summaries & action items
│   ├── paper-workflow.md          # Idea-to-publication checklist
│   ├── reviewer.md                # Reviewer #2 simulator templates
│   └── TEMPLATES.md               # Reusable theorem/proof/algorithm templates
│
├── theory/                        # Mathematical formalization & proofs
│   ├── GT-Judge_Phase1_Formalization.pdf  # Phase 1 formal defs & theorems
│   ├── Phase1_Fixes.md            # 5 addenda fixing reviewer-level gaps
│   └── NOTATION.md                # Unified math symbol dictionary
│
├── code/                          # Implementation (Phase 2+)
│   ├── src/                       # Core GT-Judge pipeline source code
│   ├── configs/                   # YAML configs (λ, K, temperature, models)
│   ├── tests/                     # Unit tests for each game module
│   └── EXPERIMENTS.md             # Experiment registry & results tracker
│
├── presentation/                  # Slides for supervisor meetings
│   └── presentation_slides.md
│
├── assignments/                   # Active task milestones
│   └── assignment_1_mathematical_formulation.md
│
└── archive/                       # Rejected ideas & historical drafts
    ├── FINAL_IDEA_SELECTION.md
    ├── IDEAS.md
    ├── game_theoretic_judge_proposal.md
    ├── agentic paper .md
    └── README (2).md
```

---

## Rules

1. **Never delete** files from `archive/` — they are historical records.
2. **All new code** goes into `code/src/`. Unit tests into `code/tests/`.
3. **All game parameters** (payoffs, token costs, rounds) go into `code/configs/`.
4. **Theory updates** (proofs, revised theorems) go into `theory/`.
5. **Paper drafts** (LaTeX, overleaf, references) go into `paper/`.
6. **New math symbols** must be registered in `theory/NOTATION.md`.
