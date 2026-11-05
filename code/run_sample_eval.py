"""
run_sample_eval.py — Run the pipeline on the sample claims and print the new accuracy metrics,
without overwriting the final test predictions in output.csv.
"""
import asyncio
import os
import sys
import csv

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from config import DATASET_DIR
from src.data_loader import DataStore
from src.pipeline import run_pipeline
from evaluation.main import run_evaluation


async def main():
    print("Loading datasets...")
    data_store = DataStore(DATASET_DIR)
    
    # Run the pipeline on sample claims (20 rows)
    output_df = await run_pipeline(
        data_store=data_store,
        use_sample=True,
        max_concurrent=3,
    )
    
    # Save predictions to sample_predictions.csv
    sample_output_path = os.path.join(DATASET_DIR, "sample_predictions.csv")
    output_df.to_csv(sample_output_path, index=False, quoting=csv.QUOTE_ALL)
    print(f"\nSaved sample predictions to: {sample_output_path}")
    
    # Run evaluation
    sample_gt_path = os.path.join(DATASET_DIR, "sample_claims.csv")
    run_evaluation(sample_output_path, sample_gt_path)


if __name__ == "__main__":
    asyncio.run(main())
