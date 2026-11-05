"""
utils.py — Retry logic, JSON parser, value normalizers, Gemini API wrapper.
Uses a global async lock to serialize ALL API calls (required for free tier 15 RPM).
"""
import asyncio
import json
import random
import re
import time

import google.generativeai as genai

from config import GEMINI_API_KEY, MAX_RETRIES, API_TIMEOUT

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Model lists for rotation to bypass 20 requests/day free tier quota limits
MODELS_VISION = [
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
]

MODELS_TEXT = [
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemma-4-26b-a4b-it",
    "gemma-4-31b-it",
]

_vision_model_idx = 0
_text_model_idx = 0

# Global rate limiter — serializes all API calls with enforced delay
_api_lock = None  # initialized lazily in async context
_last_call_time = 0
MIN_CALL_INTERVAL = 13.0  # seconds between calls (safe for 5 RPM free tier)


def _get_lock():
    global _api_lock
    if _api_lock is None:
        _api_lock = asyncio.Lock()
    return _api_lock


# ---------------------------------------------------------------------------
# JSON Parser (robust)
# ---------------------------------------------------------------------------
def safe_parse_json(text: str) -> dict:
    """Strip markdown fences and parse JSON safely."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Could not parse JSON from response: {text[:300]}")


# ---------------------------------------------------------------------------
# Gemini API call with GLOBAL lock + retry
# ---------------------------------------------------------------------------
async def call_gemini_api(
    system_prompt: str,
    user_content: list,
    is_vision: bool = False,
    max_retries: int = MAX_RETRIES,
) -> str:
    """
    Async Gemini API call with:
    - Global lock ensuring only ONE call at a time (prevents rate limit storms)
    - Enforced minimum interval between calls
    - Automatic model rotation across quota pools on daily limit (429 quota) errors
    - Exponential backoff on rate limits
    """
    global _last_call_time, _vision_model_idx, _text_model_idx

    models_list = MODELS_VISION if is_vision else MODELS_TEXT

    for attempt in range(max_retries):
        idx = _vision_model_idx if is_vision else _text_model_idx
        model_name = models_list[idx % len(models_list)]

        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
        )

        try:
            # Acquire global lock — only one API call at a time
            lock = _get_lock()
            async with lock:
                # Enforce minimum interval
                now = time.time()
                elapsed = now - _last_call_time
                print(f"  [API Lock Debug] Task acquired lock {id(lock)}. Elapsed since last call: {elapsed:.2f}s. Last call: {_last_call_time}")
                if elapsed < MIN_CALL_INTERVAL:
                    sleep_time = MIN_CALL_INTERVAL - elapsed
                    print(f"  [API Lock Debug] Enforcing call interval: sleeping {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)

                _last_call_time = time.time()
                print(f"  [API Lock Debug] Calling Gemini API (model={model_name})...")

                # Run blocking generate_content in thread executor
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: model.generate_content(user_content)
                    ),
                    timeout=API_TIMEOUT,
                )

            return response.text

        except asyncio.TimeoutError:
            print(f"  [Attempt {attempt+1}/{max_retries}] API call timed out")
        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str and "exceeded" in error_str:
                # Rotate model index immediately
                if is_vision:
                    _vision_model_idx += 1
                    new_idx = _vision_model_idx
                else:
                    _text_model_idx += 1
                    new_idx = _text_model_idx
                new_model_name = models_list[new_idx % len(models_list)]
                print(f"  [QUOTA LIMIT] Model {model_name} daily quota exhausted. Rotating to {new_model_name}...")
                await asyncio.sleep(1.0)
            elif "429" in error_str or "resource" in error_str or "rate" in error_str:
                wait = (2 ** attempt) * 10 + random.uniform(1, 5)
                print(f"  [Attempt {attempt+1}/{max_retries}] Rate limited, waiting {wait:.0f}s")
                await asyncio.sleep(wait)
            elif "api key" in error_str or "invalid" in error_str or "permission" in error_str:
                print(f"  [FATAL] API key error: {e}")
                raise
            else:
                print(f"  [Attempt {attempt+1}/{max_retries}] Error: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt + random.uniform(0, 2))

    raise RuntimeError(f"Max retries ({max_retries}) exceeded for Gemini API call")


# ---------------------------------------------------------------------------
# Value normalizers
# ---------------------------------------------------------------------------
ALLOWED_ISSUE_TYPES = {
    "dent", "scratch", "crack", "glass_shatter", "broken_part",
    "missing_part", "torn_packaging", "crushed_packaging",
    "water_damage", "stain", "none", "unknown",
}

ALLOWED_CLAIM_STATUS = {"supported", "contradicted", "not_enough_information"}

ALLOWED_SEVERITY = {"none", "low", "medium", "high", "unknown"}

ALLOWED_RISK_FLAGS = {
    "none", "blurry_image", "cropped_or_obstructed", "low_light_or_glare",
    "wrong_angle", "wrong_object", "wrong_object_part", "damage_not_visible",
    "claim_mismatch", "possible_manipulation", "non_original_image",
    "text_instruction_present", "user_history_risk", "manual_review_required",
}

CAR_PARTS = {
    "front_bumper", "rear_bumper", "door", "hood", "windshield",
    "side_mirror", "headlight", "taillight", "fender", "quarter_panel",
    "body", "unknown",
}

LAPTOP_PARTS = {
    "screen", "keyboard", "trackpad", "hinge", "lid", "corner",
    "port", "base", "body", "unknown",
}

PACKAGE_PARTS = {
    "box", "package_corner", "package_side", "seal", "label",
    "contents", "item", "unknown",
}

SEVERITY_ALIASES = {
    "medium/high": "high",
    "low/medium": "medium",
    "moderate": "medium",
    "severe": "high",
    "minor": "low",
    "n/a": "unknown",
    "": "unknown",
}


def normalize_field(value, allowed: set, default: str = "unknown") -> str:
    if value is None:
        return default
    value = str(value).lower().strip().replace(" ", "_")
    if allowed == ALLOWED_SEVERITY and value in SEVERITY_ALIASES:
        value = SEVERITY_ALIASES[value]
    if value in allowed:
        return value
    return default


def get_parts_for_object(claim_object: str) -> set:
    mapping = {"car": CAR_PARTS, "laptop": LAPTOP_PARTS, "package": PACKAGE_PARTS}
    return mapping.get(claim_object, CAR_PARTS | LAPTOP_PARTS | PACKAGE_PARTS)


def normalize_risk_flags(flags) -> str:
    if isinstance(flags, str):
        items = [f.strip().lower().replace(" ", "_") for f in flags.split(";") if f.strip()]
    elif isinstance(flags, list):
        items = [str(f).strip().lower().replace(" ", "_") for f in flags if f]
    else:
        items = []
    valid = [f for f in items if f in ALLOWED_RISK_FLAGS and f != "none"]
    return ";".join(valid) if valid else "none"


def normalize_image_ids(ids) -> str:
    if isinstance(ids, str):
        items = [i.strip() for i in ids.split(";") if i.strip() and i.strip().lower() != "none"]
    elif isinstance(ids, list):
        items = [str(i).strip() for i in ids if i and str(i).strip().lower() != "none"]
    else:
        items = []
    return ";".join(items) if items else "none"


def normalize_bool(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    s = str(value).lower().strip()
    if s in ("true", "1", "yes"):
        return "true"
    return "false"
