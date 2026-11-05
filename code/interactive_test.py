"""
interactive_test.py — Manually test any custom damage claim and view the AI's analysis in real-time.
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
    print("="*80)
    print("INSURANCE CLAIM VERIFICATION — INTERACTIVE TEST MODE")
    print("="*80)
    
    # 1. Load DataStore
    print("Loading datasets...")
    data_store = DataStore(DATASET_DIR)
    
    # 2. Get inputs
    print("\n--- Enter Claim Details ---")
    
    claim_object = ""
    while claim_object not in ["car", "laptop", "package"]:
        claim_object = input("Enter object type (car/laptop/package): ").strip().lower()
        
    user_claim = input("Enter customer's claim text: ").strip()
    if not user_claim:
        user_claim = "My rear bumper is dented."
        print(f"Using default claim: '{user_claim}'")
        
    image_paths_input = input("Enter image paths relative to dataset folder (e.g. images/sample/case_001/img_1.jpg) [separate multiple with semicolon]: ").strip()
    if not image_paths_input:
        # Default to a working sample image
        image_paths_input = "images/sample/case_001/img_1.jpg"
        print(f"Using default image: '{image_paths_input}'")
        
    user_id = input("Enter user ID (optional, hit Enter to use default 'user_001'): ").strip()
    if not user_id:
        user_id = "user_001"

    # Resolve paths
    image_paths = [p.strip() for p in image_paths_input.split(";") if p.strip()]
    abs_image_paths = []
    for p in image_paths:
        abs_path = data_store.resolve_image_path(p)
        if not os.path.exists(abs_path):
            print(f"WARNING: Image path not found: {abs_path}")
        abs_image_paths.append(abs_path)

    # 3. Retrieve database requirements & user history context
    user_history = data_store.get_user_history(user_id)
    # Default history if not found in CSV
    if not user_history:
        user_history = {
            "user_id": user_id,
            "past_claim_count": 0,
            "accept_claim": 0,
            "manual_review_claim": 0,
            "rejected_claim": 0,
            "last_90_days_claim_count": 0,
            "history_flags": "none",
            "history_summary": "No previous claim history."
        }
    evidence_reqs = data_store.get_evidence_requirements(claim_object)

    print("\n" + "="*80)
    print("RUNNING PIPELINE")
    print("="*80)
    print(f"User ID:    {user_id}")
    print(f"Object:     {claim_object}")
    print(f"Claim:      {user_claim}")
    print(f"Images:     {', '.join(image_paths)}")
    print("-"*80)

    # 4. Stage 1: Vision Inspector
    print("\n[Stage 1] Analyzing Images...")
    image_reports = []
    for path in abs_image_paths:
        image_id = extract_image_id(path)
        if not os.path.exists(path):
            print(f"  Skipping non-existent file: {path}")
            continue
        print(f"  Analyzing image '{image_id}'...")
        report = await run_vision_inspector(path, claim_object, image_id)
        print(f"  Output for '{image_id}':")
        print(json.dumps(report, indent=4))
        image_reports.append(report)

    if not image_reports:
        print("\n[ERROR] No valid images were analyzed. Cannot proceed with Stage 2.")
        return

    # 5. Stage 2: Logic Checker
    print("\n[Stage 2] Running Logic & Decision Checker...")
    final_verdict = await run_logic_checker(
        user_claim=user_claim,
        image_reports=image_reports,
        evidence_requirements=evidence_reqs,
        user_history=user_history
    )

    # 6. Print Verdict
    print("\n" + "="*80)
    print("FINAL CLAIM VERDICT & DECISION")
    print("="*80)
    print(f"Evidence Standard Met:   {final_verdict.get('evidence_standard_met')}")
    print(f"Standard Met Reason:     {final_verdict.get('evidence_standard_met_reason')}")
    print(f"Claim Status Verdict:    {str(final_verdict.get('claim_status')).upper()}")
    print(f"Severity:                {final_verdict.get('severity')}")
    print(f"Detected Part:           {final_verdict.get('object_part')}")
    print(f"Detected Issue Type:     {final_verdict.get('issue_type')}")
    print(f"Supporting Image IDs:    {final_verdict.get('supporting_image_ids')}")
    print(f"Risk Flags:              {final_verdict.get('risk_flags')}")
    print(f"\n[Justification]:\n{final_verdict.get('claim_status_justification')}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
