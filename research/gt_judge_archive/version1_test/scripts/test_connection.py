"""
scripts/test_connection.py  (issue §2)
======================================
Make ONE cheap call to the configured provider/model and report latency, token
count, and a truncated response. Exits non-zero with a clear message if the key
is missing or invalid. Run this before burning budget on a full benchmark.

    python scripts/test_connection.py                       # use config default
    python scripts/test_connection.py --provider google --model gemini-1.5-flash
    python scripts/test_connection.py --api-key ...          # explicit key
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402
from src.llm_client import LLMClient, LLMConfigError, PROVIDER_ENV_VAR  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="GT-Judge provider smoke test")
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--api-key", default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config)).get("model", {})
    provider = (args.provider or cfg.get("provider", "openai")).lower()
    model = args.model or cfg.get("evaluator_model", "gpt-4o-mini")

    print(f"Provider: {provider}  |  Model: {model}  |  Key var: "
          f"{PROVIDER_ENV_VAR.get(provider, '??')}")

    try:
        client = LLMClient(provider=provider, model=model, api_key=args.api_key,
                           max_tokens=64, temperature=0.0, max_retries=1)
    except LLMConfigError as e:
        print(f"\n[FAIL] {e}")
        sys.exit(2)

    try:
        t0 = time.time()
        text, tokens = client.call(
            system_prompt="You are a terse assistant. Reply in one short sentence.",
            user_prompt="Reply with exactly: GT-Judge connection OK.",
            temperature=0.0,
        )
        dt = time.time() - t0
    except Exception as e:  # noqa: BLE001
        print(f"\n[FAIL] Call raised {type(e).__name__}: {e}")
        print("Check that the key is valid and the model name is correct for this provider.")
        sys.exit(3)

    preview = (text[:120] + "…") if len(text) > 120 else text
    print(f"\n[OK] latency={dt:.2f}s  tokens={tokens}")
    print(f"     response: {preview!r}")
    sys.exit(0)


if __name__ == "__main__":
    main()
