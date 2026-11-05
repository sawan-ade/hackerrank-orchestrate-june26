"""
LLM Client
===========
Provider-agnostic LLM client for the GT-Judge pipeline.

Design (issue §2):
    - `BaseLLMClient` holds ALL provider-independent logic: retry/backoff with
      jitter, the temperature==0 response cache, and structured-JSON parsing.
    - Concrete subclasses (`OpenAIClient`, `AnthropicClient`, `GoogleClient`)
      implement ONLY `_raw_call()` -> (text, total_tokens). No retry/cache logic
      is duplicated per provider.
    - `LLMClient(provider=...)` is a factory that returns the right subclass and
      picks up the correct SDK + env var automatically:
          openai    -> OPENAI_API_KEY
          anthropic -> ANTHROPIC_API_KEY
          google    -> GOOGLE_API_KEY
    - Provider SDKs are imported lazily inside each subclass so importing this
      module never requires all three SDKs to be installed.

Nothing in this module hardcodes a key. Keys come from the environment (see
`.env.example`) or an explicit `api_key=` override.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from abc import ABC, abstractmethod
from typing import Optional

# Providers that the factory knows how to build.
SUPPORTED_PROVIDERS = ("openai", "anthropic", "google")

# Which environment variable holds the key for each provider.
PROVIDER_ENV_VAR = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
}


class LLMConfigError(RuntimeError):
    """Raised for missing keys / unknown providers / missing SDKs — always with
    an actionable message telling the user exactly what to fix."""


class BaseLLMClient(ABC):
    """
    Provider-independent LLM wrapper.

    Subclasses implement `_raw_call(system, user, temperature) -> (text, tokens)`.
    Everything else (retry, cache, JSON parsing) lives here so it is shared, not
    copy-pasted per provider (issue §2, §4 code-quality).
    """

    provider_name: str = "base"

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        api_key: Optional[str] = None,
        max_retries: int = 5,
        backoff_factor: float = 1.5,
        initial_delay: float = 1.0,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay
        self.api_key = api_key or os.getenv(PROVIDER_ENV_VAR.get(self.provider_name, ""))
        # Cache is keyed on (system, user, temp) and only used for temp==0 calls.
        self._cache: dict[tuple[str, str, float], tuple[str, int]] = {}
        # Simple counters so callers/estimators can see real usage.
        self.total_calls = 0
        self.total_tokens = 0
        self._init_sdk()

    # ---- provider hooks -------------------------------------------------
    @abstractmethod
    def _init_sdk(self) -> None:
        """Lazily import the SDK and build the underlying client. Must raise
        LLMConfigError with a clear message if the SDK or key is missing."""

    @abstractmethod
    def _raw_call(self, system_prompt: str, user_prompt: str, temperature: float) -> tuple[str, int]:
        """One provider call. Return (response_text, total_tokens)."""

    @abstractmethod
    def _is_retryable(self, exc: Exception) -> bool:
        """Whether an exception from `_raw_call` is worth retrying."""

    # ---- shared logic ---------------------------------------------------
    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> tuple[str, int]:
        """Make an LLM call with retry/backoff and (for temp==0) caching.

        Returns (response_text, total_tokens_used).
        """
        temp = temperature if temperature is not None else self.temperature

        cache_key = (system_prompt, user_prompt, temp)
        if temp == 0.0 and cache_key in self._cache:
            return self._cache[cache_key]

        delay = self.initial_delay
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                text, tokens = self._raw_call(system_prompt, user_prompt, temp)
                self.total_calls += 1
                self.total_tokens += tokens
                if temp == 0.0:
                    self._cache[cache_key] = (text, tokens)
                return text, tokens
            except Exception as e:  # noqa: BLE001 - re-raised below if not retryable
                last_exc = e
                if self._is_retryable(e) and attempt < self.max_retries:
                    time.sleep(delay * (1.0 + random.random() * 0.1))
                    delay *= self.backoff_factor
                else:
                    raise
        # Unreachable in practice, but keep the type checker + logic honest.
        raise RuntimeError("LLM call failed after all retries.") from last_exc

    def call_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> tuple[dict, int]:
        """Make an LLM call expecting JSON. Robust to code fences and stray prose.

        Returns (parsed_dict, total_tokens). On unrecoverable parse failure returns
        {"raw_response": text, "parse_error": True} so callers can fall back to a
        default action rather than crash (see debate_game action normalization).
        """
        text, tokens = self.call(
            system_prompt=system_prompt + "\n\nRespond ONLY with valid JSON.",
            user_prompt=user_prompt,
            temperature=temperature,
        )
        parsed = self._extract_json(text)
        if parsed is not None:
            return parsed, tokens
        return {"raw_response": text, "parse_error": True}, tokens

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        """Best-effort JSON extraction. Tries: direct parse -> fenced block ->
        first balanced {...} object. Returns None if nothing parses to a dict."""
        if not text:
            return None
        # 1. direct
        try:
            obj = json.loads(text)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            pass
        # 2. ```json ... ``` fence
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(1))
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                pass
        # 3. first balanced brace span
        start = text.find("{")
        while start != -1:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : i + 1]
                        try:
                            obj = json.loads(candidate)
                            if isinstance(obj, dict):
                                return obj
                        except json.JSONDecodeError:
                            break
            start = text.find("{", start + 1)
        return None


# ===========================================================================
# Concrete providers
# ===========================================================================

class OpenAIClient(BaseLLMClient):
    provider_name = "openai"

    def _init_sdk(self) -> None:
        try:
            import openai  # noqa: F401
            from openai import OpenAI
        except ImportError as e:
            raise LLMConfigError(
                "openai SDK not installed. Run: pip install openai>=1.30.0"
            ) from e
        if not self.api_key:
            raise LLMConfigError(
                "OPENAI_API_KEY is not set. Add it to .env (see .env.example) "
                "or pass --api-key."
            )
        self._openai = openai
        self.client = OpenAI(api_key=self.api_key)

    def _raw_call(self, system_prompt, user_prompt, temperature):
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=self.max_tokens,
        )
        text = resp.choices[0].message.content or ""
        tokens = resp.usage.total_tokens if resp.usage else 0
        return text, tokens

    def _is_retryable(self, exc: Exception) -> bool:
        oa = self._openai
        if isinstance(exc, (oa.RateLimitError, oa.APIConnectionError,
                            oa.APITimeoutError, oa.InternalServerError)):
            return True
        if isinstance(exc, oa.APIError):
            code = getattr(exc, "status_code", None)
            return code is None or code in (500, 502, 503, 504)
        return False


class AnthropicClient(BaseLLMClient):
    provider_name = "anthropic"

    def _init_sdk(self) -> None:
        try:
            import anthropic
        except ImportError as e:
            raise LLMConfigError(
                "anthropic SDK not installed. Run: pip install anthropic>=0.39.0"
            ) from e
        if not self.api_key:
            raise LLMConfigError(
                "ANTHROPIC_API_KEY is not set. Add it to .env (see .env.example) "
                "or pass --api-key."
            )
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def _raw_call(self, system_prompt, user_prompt, temperature):
        resp = self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temperature,
            max_tokens=self.max_tokens,
        )
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )
        usage = getattr(resp, "usage", None)
        tokens = (usage.input_tokens + usage.output_tokens) if usage else 0
        return text, tokens

    def _is_retryable(self, exc: Exception) -> bool:
        a = self._anthropic
        retryable = (
            getattr(a, "RateLimitError", ()),
            getattr(a, "APIConnectionError", ()),
            getattr(a, "APITimeoutError", ()),
            getattr(a, "InternalServerError", ()),
        )
        retryable = tuple(t for t in retryable if isinstance(t, type))
        if retryable and isinstance(exc, retryable):
            return True
        if isinstance(exc, getattr(a, "APIStatusError", ())):
            code = getattr(exc, "status_code", None)
            return code in (500, 502, 503, 504, 529)
        return False


class GoogleClient(BaseLLMClient):
    provider_name = "google"

    def _init_sdk(self) -> None:
        # Prefer the current unified SDK (google-genai); fall back to legacy
        # google-generativeai if that's what's installed.
        self._mode = None
        if not self.api_key:
            raise LLMConfigError(
                "GOOGLE_API_KEY is not set. Add it to .env (see .env.example) "
                "or pass --api-key."
            )
        try:
            from google import genai  # google-genai (new)
            self._genai = genai
            self.client = genai.Client(api_key=self.api_key)
            self._mode = "genai"
            return
        except ImportError:
            pass
        try:
            import google.generativeai as legacy  # google-generativeai (old)
            legacy.configure(api_key=self.api_key)
            self._legacy = legacy
            self._mode = "legacy"
            return
        except ImportError as e:
            raise LLMConfigError(
                "No Google SDK installed. Run: pip install google-genai"
            ) from e

    def _raw_call(self, system_prompt, user_prompt, temperature):
        if self._mode == "genai":
            resp = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config={
                    "system_instruction": system_prompt,
                    "temperature": temperature,
                    "max_output_tokens": self.max_tokens,
                },
            )
            text = resp.text or ""
            usage = getattr(resp, "usage_metadata", None)
            tokens = getattr(usage, "total_token_count", 0) if usage else 0
            return text, tokens
        else:  # legacy
            model = self._legacy.GenerativeModel(
                self.model, system_instruction=system_prompt
            )
            resp = model.generate_content(
                user_prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": self.max_tokens,
                },
            )
            text = resp.text or ""
            usage = getattr(resp, "usage_metadata", None)
            tokens = getattr(usage, "total_token_count", 0) if usage else 0
            return text, tokens

    def _is_retryable(self, exc: Exception) -> bool:
        # Google SDK raises google.api_core exceptions; match on class name to
        # avoid a hard dependency on that package being importable here.
        name = type(exc).__name__
        return name in {
            "ResourceExhausted", "ServiceUnavailable", "DeadlineExceeded",
            "InternalServerError", "TooManyRequests",
        }


_PROVIDER_CLASSES = {
    "openai": OpenAIClient,
    "anthropic": AnthropicClient,
    "google": GoogleClient,
}


def LLMClient(  # noqa: N802 - factory kept callable-like for drop-in compatibility
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 1024,
    api_key: Optional[str] = None,
    provider: str = "openai",
    max_retries: int = 5,
    backoff_factor: float = 1.5,
    initial_delay: float = 1.0,
) -> BaseLLMClient:
    """Factory: build the right provider client.

    Kept as a callable named `LLMClient` so existing call sites that did
    `LLMClient(model=..., temperature=...)` keep working; the only new argument
    is `provider`.
    """
    provider = (provider or "openai").lower()
    if provider not in _PROVIDER_CLASSES:
        raise LLMConfigError(
            f"Unknown provider '{provider}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}."
        )
    return _PROVIDER_CLASSES[provider](
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        initial_delay=initial_delay,
    )
