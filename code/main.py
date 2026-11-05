"""
main.py — Entry point: runs the 3-stage pipeline on claims.csv and writes output.csv.

Usage:
    python main.py                  # Run on claims.csv (test set)
    python main.py --sample         # Run on sample_claims.csv (development)
    python main.py --sample --eval  # Run on sample + evaluate accuracy
"""
import asyncio
import csv
import os
import sys
import time
import argparse

# Ensure code/ is on the path
sys.path.insert(0, os.path.dirname(__file__))

from config import DATASET_DIR, MAX_CONCURRENT_CLAIMS
from src.data_loader import DataStore
from src.pipeline import run_pipeline


# Output column order (must match problem statement exactly)
OUTPUT_COLUMNS = [
    "user_id",
    "image_paths",
    "user_claim",
    "claim_object",
    "evidence_standard_met",
    "evidence_standard_met_reason",
    "risk_flags",
    "issue_type",
    "object_part",
    "claim_status",
    "claim_status_justification",
    "supporting_image_ids",
    "valid_image",
    "severity",
]


async def main():
    parser = argparse.ArgumentParser(description="Multi-Modal Evidence Review Pipeline")
    parser.add_argument("--sample", action="store_true", help="Run on sample_claims.csv instead of claims.csv")
    parser.add_argument("--eval", action="store_true", help="Run evaluation after processing sample claims")
    parser.add_argument("--concurrent", type=int, default=MAX_CONCURRENT_CLAIMS, help="Max concurrent claims")
    args = parser.parse_args()

    start_time = time.time()

    # Load all data
    print("Loading datasets...")
    data_store = DataStore(DATASET_DIR)
    print(f"  Claims: {len(data_store.claims)} rows")
    print(f"  Sample claims: {len(data_store.sample_claims)} rows")
    print(f"  User history: {len(data_store.user_history)} users")
    print(f"  Evidence requirements: {len(data_store.evidence_requirements)} rules")

    # Run pipeline
    output_df = await run_pipeline(
        data_store=data_store,
        use_sample=args.sample,
        max_concurrent=args.concurrent,
    )

    # Ensure column order matches spec
    output_df = output_df[OUTPUT_COLUMNS]

    # Write output
    output_path = os.path.join(os.path.dirname(__file__), "..", "output.csv")
    output_df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)

    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"Pipeline complete!")
    print(f"  Rows processed: {len(output_df)}")
    print(f"  Output written to: {os.path.abspath(output_path)}")
    print(f"  Time elapsed: {elapsed:.1f}s")
    print(f"{'='*60}")

    # Quick validation
    print("\nRunning output validation...")
    assert len(output_df.columns) == 14, f"Expected 14 columns, got {len(output_df.columns)}"
    assert output_df["claim_status"].isin(["supported", "contradicted", "not_enough_information"]).all(), \
        f"Invalid claim_status values: {output_df['claim_status'].unique()}"
    assert output_df["severity"].isin(["none", "low", "medium", "high", "unknown"]).all(), \
        f"Invalid severity values: {output_df['severity'].unique()}"
    assert output_df[["user_id", "claim_status", "evidence_standard_met", "valid_image"]].notna().all().all(), \
        "NaN values found in critical fields"
    assert output_df["evidence_standard_met"].isin(["true", "false"]).all(), \
        f"Invalid evidence_standard_met values: {output_df['evidence_standard_met'].unique()}"
    print("[OK] All validation checks passed!")

    # Optionally run evaluation
    if args.eval and args.sample:
        print("\nRunning evaluation on sample claims...")
        from evaluation.main import run_evaluation
        run_evaluation(output_path, os.path.join(DATASET_DIR, "sample_claims.csv"))


if __name__ == "__main__":
    asyncio.run(main())
