"""
evaluation/main.py — Evaluate pipeline output against sample_claims.csv ground truth.
Computes per-field accuracy and generates a classification report for claim_status.

Usage:
    python evaluation/main.py                           # Uses default paths
    python evaluation/main.py <output.csv> <sample.csv> # Custom paths
"""
import os
import sys
import pandas as pd

# Ensure code/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


FIELDS_TO_EVALUATE = [
    "evidence_standard_met",   # exact match (bool-like)
    "claim_status",            # exact match (3-way)
    "issue_type",              # exact match
    "object_part",             # exact match
    "valid_image",             # exact match (bool-like)
    "severity",                # exact match
]


def run_evaluation(output_path: str, ground_truth_path: str):
    """Compare predictions to ground truth and print accuracy metrics."""
    print(f"\n{'='*60}")
    print(f"EVALUATION REPORT")
    print(f"{'='*60}")

    pred = pd.read_csv(output_path)
    gt = pd.read_csv(ground_truth_path)

    print(f"\nPredictions: {len(pred)} rows")
    print(f"Ground truth: {len(gt)} rows")

    if len(pred) != len(gt):
        print(f"WARNING: Row count mismatch! Predictions={len(pred)}, Ground truth={len(gt)}")
        min_len = min(len(pred), len(gt))
        pred = pred.head(min_len)
        gt = gt.head(min_len)

    print(f"\n{'Field':<30} {'Accuracy':>10} {'Correct':>10} {'Total':>10}")
    print("-" * 65)

    results = {}
    for field in FIELDS_TO_EVALUATE:
        if field in gt.columns and field in pred.columns:
            pred_vals = pred[field].astype(str).str.lower().str.strip()
            gt_vals = gt[field].astype(str).str.lower().str.strip()
            match = pred_vals == gt_vals
            accuracy = match.mean()
            results[field] = {
                "accuracy": accuracy,
                "correct": match.sum(),
                "total": len(match),
            }
            print(f"{field:<30} {accuracy:>10.1%} {match.sum():>10} {len(match):>10}")

    # Overall accuracy (average across fields)
    if results:
        overall = sum(r["accuracy"] for r in results.values()) / len(results)
        print(f"\n{'OVERALL (avg across fields)':<30} {overall:>10.1%}")

    # Claim status confusion matrix
    if "claim_status" in gt.columns and "claim_status" in pred.columns:
        print(f"\n{'='*60}")
        print("CLAIM STATUS DETAILED ANALYSIS")
        print(f"{'='*60}")

        pred_status = pred["claim_status"].astype(str).str.lower().str.strip()
        gt_status = gt["claim_status"].astype(str).str.lower().str.strip()

        # Per-class accuracy
        for status in ["supported", "contradicted", "not_enough_information"]:
            mask = gt_status == status
            if mask.any():
                correct = (pred_status[mask] == gt_status[mask]).sum()
                total = mask.sum()
                print(f"  {status:<30} {correct}/{total} = {correct/total:.1%}")

        # Try sklearn classification report
        try:
            from sklearn.metrics import classification_report, confusion_matrix
            print(f"\nClassification Report:")
            print(classification_report(gt_status, pred_status, zero_division=0))

            print(f"Confusion Matrix:")
            labels = ["supported", "contradicted", "not_enough_information"]
            cm = confusion_matrix(gt_status, pred_status, labels=labels)
            print(f"{'':>30} {'supported':>15} {'contradicted':>15} {'not_enough':>15}")
            for i, label in enumerate(labels):
                print(f"{'Actual ' + label:<30} {cm[i][0]:>15} {cm[i][1]:>15} {cm[i][2]:>15}")
        except ImportError:
            print("  (Install scikit-learn for detailed classification report)")

    # Risk flags analysis
    if "risk_flags" in gt.columns and "risk_flags" in pred.columns:
        print(f"\n{'='*60}")
        print("RISK FLAGS ANALYSIS")
        print(f"{'='*60}")
        pred_flags = pred["risk_flags"].astype(str).str.lower().str.strip()
        gt_flags = gt["risk_flags"].astype(str).str.lower().str.strip()
        exact_match = (pred_flags == gt_flags).mean()
        print(f"  Exact match rate: {exact_match:.1%}")

    print(f"\n{'='*60}")
    print("Evaluation complete.")
    print(f"{'='*60}\n")

    return results


if __name__ == "__main__":
    # Default paths
    code_dir = os.path.dirname(os.path.dirname(__file__))
    default_output = os.path.join(code_dir, "..", "output.csv")
    default_gt = os.path.join(code_dir, "..", "dataset", "sample_claims.csv")

    if len(sys.argv) >= 3:
        output_path = sys.argv[1]
        gt_path = sys.argv[2]
    else:
        output_path = default_output
        gt_path = default_gt

    run_evaluation(output_path, gt_path)
