"""
vision_inspector.py — Stage 1 agent: per-image visual analysis using Gemini Vision.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.image_processor import load_image, extract_image_id
from src.utils import call_gemini_api, safe_parse_json
from prompts.vision_inspector_prompt import VISION_INSPECTOR_SYSTEM


async def run_vision_inspector(image_path: str, claim_object: str, image_id: str) -> dict:
    """
    Stage 1: Analyze a single image without knowing the user's claim.
    Returns structured JSON about what the image shows.
    """
    # Load and resize image (async PIL)
    pil_image = await load_image(image_path)

    # Build user content: image + text instruction
    user_content = [
        pil_image,
        f"Inspect this image. The claimed object type is: {claim_object}. The image ID is: {image_id}. Return JSON only.",
    ]

    # Call Gemini Vision
    response_text = await call_gemini_api(
        system_prompt=VISION_INSPECTOR_SYSTEM,
        user_content=user_content,
        is_vision=True,
    )

    # Parse JSON response
    result = safe_parse_json(response_text)

    # Ensure image_id is set correctly
    result["image_id"] = image_id

    return result
