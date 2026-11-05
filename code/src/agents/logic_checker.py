"""
logic_checker.py — Stage 2 agent: unified evidence checking and risk evaluation using Gemini.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils import call_gemini_api, safe_parse_json
from prompts.logic_checker_prompt import LOGIC_CHECKER_SYSTEM, build_logic_checker_user_message


async def run_logic_checker(
    user_claim: str,
    image_reports: list[dict],
    evidence_requirements: list[dict],
    user_history: dict,
) -> dict:
    """
    Stage 2 (Merged): Evaluate the claim against visual observations, requirements, and user history.
    Returns the final structured claims decision dict.
    """
    user_message = build_logic_checker_user_message(
        user_claim=user_claim,
        image_reports=image_reports,
        evidence_requirements=evidence_requirements,
        user_history=user_history,
    )

    response_text = await call_gemini_api(
        system_prompt=LOGIC_CHECKER_SYSTEM,
        user_content=[user_message],
        is_vision=False,
    )

    return safe_parse_json(response_text)
