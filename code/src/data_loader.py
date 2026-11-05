"""
data_loader.py — Load and pre-join all CSV data at startup.
All CSV lookups happen BEFORE any API call.
"""
import os
import pandas as pd
from config import DATASET_DIR


class DataStore:
    def __init__(self, dataset_dir: str = None):
        base = dataset_dir or DATASET_DIR
        self.base_dir = os.path.abspath(base)

        self.claims = pd.read_csv(os.path.join(self.base_dir, "claims.csv"))
        self.sample_claims = pd.read_csv(os.path.join(self.base_dir, "sample_claims.csv"))
        self.user_history = pd.read_csv(os.path.join(self.base_dir, "user_history.csv")).set_index("user_id")
        self.evidence_requirements = pd.read_csv(os.path.join(self.base_dir, "evidence_requirements.csv"))

    def get_user_history(self, user_id: str) -> dict:
        """O(1) lookup of user history by user_id."""
        if user_id in self.user_history.index:
            return self.user_history.loc[user_id].to_dict()
        return {
            "past_claim_count": 0,
            "accept_claim": 0,
            "manual_review_claim": 0,
            "rejected_claim": 0,
            "last_90_days_claim_count": 0,
            "history_flags": "none",
            "history_summary": "No history available",
        }

    def get_evidence_requirements(self, claim_object: str) -> list[dict]:
        """Filter evidence requirements for the given object type + 'all'."""
        mask = self.evidence_requirements["claim_object"].isin([claim_object, "all"])
        return self.evidence_requirements[mask].to_dict("records")

    def get_image_paths(self, image_paths_str: str) -> list[str]:
        """Split semicolon-separated image paths into a list."""
        return [p.strip() for p in image_paths_str.split(";") if p.strip()]

    def resolve_image_path(self, relative_path: str) -> str:
        """Resolve relative image path to absolute, using dataset base dir."""
        return os.path.join(self.base_dir, relative_path)
