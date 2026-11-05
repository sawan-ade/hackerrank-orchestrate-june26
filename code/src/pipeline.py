"""
pipeline.py — Orchestrator: runs 3-stage pipeline per claim with async concurrency.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.vision_inspector import run_vision_inspector
from src.agents.logic_checker import run_logic_checker
from src.image_processor import extract_image_id
from src.data_loader import DataStore
from src.utils import (
    normalize_field, normalize_risk_flags, normalize_image_ids, normalize_bool,
    ALLOWED_ISSUE_TYPES, ALLOWED_CLAIM_STATUS, ALLOWED_SEVERITY,
    get_parts_for_object,
)

import pandas as pd


def build_invalid_image_output(claim_row: dict, image_reports: list) -> dict:
    """Fallback output when all images are invalid."""
    return {
        "user_id": claim_row["user_id"],
        "image_paths": claim_row["image_paths"],
        "user_claim": claim_row["user_claim"],
        "claim_object": claim_row["claim_object"],
        "evidence_standard_met": "false",
        "evidence_standard_met_reason": "All submitted images were invalid or could not be processed.",
        "risk_flags": "none",
        "issue_type": "unknown",
        "object_part": "unknown",
        "claim_status": "not_enough_information",
        "claim_status_justification": "No usable images were available for review.",
        "supporting_image_ids": "none",
        "valid_image": "false",
        "severity": "unknown",
    }


def build_error_fallback_row(claim_row: dict) -> dict:
    """Fallback output when the pipeline errors for a claim."""
    return {
        "user_id": claim_row["user_id"],
        "image_paths": claim_row["image_paths"],
        "user_claim": claim_row["user_claim"],
        "claim_object": claim_row["claim_object"],
        "evidence_standard_met": "false",
        "evidence_standard_met_reason": "Processing error occurred.",
        "risk_flags": "manual_review_required",
        "issue_type": "unknown",
        "object_part": "unknown",
        "claim_status": "not_enough_information",
        "claim_status_justification": "System encountered an error processing this claim.",
        "supporting_image_ids": "none",
        "valid_image": "false",
        "severity": "unknown",
    }


def assemble_output_row(claim_row: dict, final_result: dict) -> dict:
    """Assemble a normalized output row from the pipeline result."""
    claim_object = claim_row["claim_object"]
    allowed_parts = get_parts_for_object(claim_object)

    return {
        "user_id": claim_row["user_id"],
        "image_paths": claim_row["image_paths"],
        "user_claim": claim_row["user_claim"],
        "claim_object": claim_row["claim_object"],
        "evidence_standard_met": normalize_bool(final_result.get("evidence_standard_met", False)),
        "evidence_standard_met_reason": str(final_result.get("evidence_standard_met_reason", "No reason provided.")),
        "risk_flags": normalize_risk_flags(final_result.get("risk_flags", ["none"])),
        "issue_type": normalize_field(final_result.get("issue_type"), ALLOWED_ISSUE_TYPES),
        "object_part": normalize_field(final_result.get("object_part"), allowed_parts),
        "claim_status": normalize_field(final_result.get("claim_status"), ALLOWED_CLAIM_STATUS, default="not_enough_information"),
        "claim_status_justification": str(final_result.get("claim_status_justification", "No justification provided.")),
        "supporting_image_ids": normalize_image_ids(final_result.get("supporting_image_ids", ["none"])),
        "valid_image": normalize_bool(final_result.get("valid_image", False)),
        "severity": normalize_field(final_result.get("severity"), ALLOWED_SEVERITY),
    }


async def process_claim(
    claim_row: dict,
    data_store: DataStore,
    semaphore: asyncio.Semaphore,
    claim_index: int = 0,
    total_claims: int = 0,
) -> dict:
    """Process a single claim through the 3-stage pipeline."""
    async with semaphore:
        user_id = claim_row["user_id"]
        claim_object = claim_row["claim_object"]
        user_claim = claim_row["user_claim"]
        image_paths_str = claim_row["image_paths"]

        print(f"\n[{claim_index+1}/{total_claims}] Processing claim for {user_id} ({claim_object})...")

        # --- Data enrichment (zero API calls) ---
        image_paths = data_store.get_image_paths(image_paths_str)
        user_history = data_store.get_user_history(user_id)
        evidence_reqs = data_store.get_evidence_requirements(claim_object)

        # Resolve absolute image paths
        abs_image_paths = [data_store.resolve_image_path(p) for p in image_paths]

        # --- Stage 1: Vision inspection (parallel across images) ---
        print(f"  Stage 1: Analyzing {len(abs_image_paths)} image(s)...")
        image_results = await asyncio.gather(
            *[
                run_vision_inspector(path, claim_object, extract_image_id(path))
                for path in abs_image_paths
            ],
            return_exceptions=True,
        )

        # Separate successful reports from exceptions
        image_reports = [r for r in image_results if isinstance(r, dict)]
        failed_images = [r for r in image_results if isinstance(r, Exception)]
        if failed_images:
            print(f"  [{user_id}] {len(failed_images)} image(s) failed Stage 1:")
            for e in failed_images:
                print(f"    - {e}")

        # --- Short-circuit: if ALL images failed or no object visible ---
        if not image_reports:
            print(f"  [{user_id}] All images failed. Using fallback.")
            return build_invalid_image_output(claim_row, [])

        all_invalid = all(not r.get("object_visible", False) for r in image_reports)
        if all_invalid:
            print(f"  [{user_id}] No valid objects visible in any image. Using fallback.")
            return build_invalid_image_output(claim_row, image_reports)

        # --- Stage 2: Logic check & final decision (text-only) ---
        print(f"  Stage 2: Analyzing evidence, history and making final decision...")
        try:
            final_result = await run_logic_checker(
                user_claim=user_claim,
                image_reports=image_reports,
                evidence_requirements=evidence_reqs,
                user_history=user_history,
            )
        except Exception as e:
            print(f"  [{user_id}] Stage 2 failed: {e}")
            return build_error_fallback_row(claim_row)

        print(f"  [{user_id}] [OK] claim_status={final_result.get('claim_status', 'unknown')}")
        return assemble_output_row(claim_row, final_result)


async def run_pipeline(
    data_store: DataStore,
    use_sample: bool = False,
    max_concurrent: int = 5,
) -> pd.DataFrame:
    """Run the full pipeline on all claims."""
    if use_sample:
        claims_df = data_store.sample_claims
        print(f"\n{'='*60}")
        print(f"Running pipeline on SAMPLE claims ({len(claims_df)} rows)")
        print(f"{'='*60}")
    else:
        claims_df = data_store.claims
        print(f"\n{'='*60}")
        print(f"Running pipeline on TEST claims ({len(claims_df)} rows)")
        print(f"{'='*60}")

    claims = claims_df.to_dict("records")
    total = len(claims)

    # Semaphore controls global concurrency
    semaphore = asyncio.Semaphore(max_concurrent)

    results = await asyncio.gather(
        *[
            process_claim(claim, data_store, semaphore, i, total)
            for i, claim in enumerate(claims)
        ],
        return_exceptions=True,
    )

    # Separate successful rows from failures
    output_rows = []
    for claim, result in zip(claims, results):
        if isinstance(result, Exception):
            print(f"  [{claim['user_id']}] Pipeline failed: {result}")
            output_rows.append(build_error_fallback_row(claim))
        else:
            output_rows.append(result)

    return pd.DataFrame(output_rows)
