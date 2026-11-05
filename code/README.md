# Multi-Modal Evidence Review — Code

## Overview

This is a 3-stage AI pipeline that verifies insurance damage claims using images, user conversations, claim history, and evidence requirements.

**Model backbone:** Claude Sonnet (vision + reasoning)

## Architecture

```
Stage 1 (Vision Inspector)  →  Stage 2 (Evidence Checker)  →  Stage 3 (Risk & Decision)
   Per-image analysis              Claim vs evidence match       Risk flags + final verdict
   No user claim context           Text-only, uses S1 output     Text-only, uses S2 + history
```

## Setup

```bash
cd code/
pip install -r requirements.txt
```

Create a `.env` file in the `code/` directory:
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

## Usage

```bash
# Run on test claims (produces output.csv)
python main.py

# Run on sample claims (for development)
python main.py --sample

# Run on sample claims + evaluate accuracy
python main.py --sample --eval

# Adjust concurrency (default: 5)
python main.py --concurrent 3
```

## Evaluation

```bash
# Standalone evaluation
python evaluation/main.py
python evaluation/main.py path/to/output.csv path/to/ground_truth.csv
```

## File Structure

```
code/
├── main.py                    # Entry point
├── config.py                  # API keys, model config, rate limits
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── src/
│   ├── data_loader.py         # CSV loading and lookups
│   ├── image_processor.py     # PIL resize + base64 encode
│   ├── pipeline.py            # Async orchestrator
│   ├── utils.py               # JSON parser, retry, normalizers
│   └── agents/
│       ├── vision_inspector.py    # Stage 1
│       ├── evidence_checker.py    # Stage 2
│       └── risk_decision.py       # Stage 3
├── prompts/
│   ├── vision_inspector_prompt.py
│   ├── evidence_checker_prompt.py
│   └── risk_decision_prompt.py
└── evaluation/
    └── main.py                # Accuracy evaluation
```

## Cost Estimate

- Per claim (2 images, 3 stages): ~$0.04
- 45 test claims: ~$1.80
- 20 sample claims: ~$0.80
