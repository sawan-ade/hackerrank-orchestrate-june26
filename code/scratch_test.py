"""
scratch_test.py — Run a single claim to test the pipeline and view output reasoning.
"""
import asyncio
import os
import sys
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from config import DATASET_DIR
from src.data_loader import DataStore
from src.agents.vision_inspector import run_vision_inspector
from src.agents.logic_checker import run_logic_checker
from src.image_processor import extract_image_id


async def main():
    print("Loading datasets...")
    data_store = DataStore(DATASET_DIR)
    
    # Let's pick a representative claim from sample_claims.csv
    # Sample claims contains labeled examples
    claims = data_store.sample_claims.to_dict("records")
    if not claims:
        print("No sample claims found!")
        return
        
    # We will pick the first claim (user_002 - car scratch)
    claim = claims[0]
    
    print("\n" + "="*80)
    print("TESTING SINGLE CLAIM")
    print("="*80)
    print(f"User ID:     {claim['user_id']}")
    print(f"Object:      {claim['claim_object']}")
    print(f"User Claim:  {claim['user_claim']}")
    print(f"Images:      {claim['image_paths']}")
    print("-"*80)
    
    # Resolve image paths
    image_paths = data_store.get_image_paths(claim["image_paths"])
    abs_image_paths = [data_store.resolve_image_path(p) for p in image_paths]
    
    # 1. Run Stage 1: Vision Inspector
    print("\nRunning Stage 1: Vision Inspector (Per-Image Analysis)...")
    image_reports = []
    for path in abs_image_paths:
        image_id = extract_image_id(path)
        print(f"  Analyzing image: {image_id}...")
        report = await run_vision_inspector(path, claim["claim_object"], image_id)
        print(f"    [Stage 1 Output for {image_id}]:")
        print(json.dumps(report, indent=6))
        image_reports.append(report)
        
    # 2. Run Stage 2: Logic Checker (Decision & Risk Analysis)
    print("\nRunning Stage 2: Logic Checker (Context & Verdict)...")
    user_history = data_store.get_user_history(claim["user_id"])
    evidence_reqs = data_store.get_evidence_requirements(claim["claim_object"])
    
    final_verdict = await run_logic_checker(
        user_claim=claim["user_claim"],
        image_reports=image_reports,
        evidence_requirements=evidence_reqs,
        user_history=user_history
    )
    
    print("\n" + "="*80)
    print("FINAL HUMAN-LIKE DECISION RESULTS:")
    print("="*80)
    print(f"Evidence Standard Met:   {final_verdict.get('evidence_standard_met')}")
    print(f"Standard Met Reason:     {final_verdict.get('evidence_standard_met_reason')}")
    print(f"Claim Status Verdict:    {final_verdict.get('claim_status').upper()}")
    print(f"Severity:                {final_verdict.get('severity')}")
    print(f"Detected Part:           {final_verdict.get('object_part')}")
    print(f"Detected Issue Type:     {final_verdict.get('issue_type')}")
    print(f"Supporting Image IDs:    {final_verdict.get('supporting_image_ids')}")
    print(f"Risk Flags:              {final_verdict.get('risk_flags')}")
    print(f"\n[Justification (Grounding reasoning)]:\n{final_verdict.get('claim_status_justification')}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
