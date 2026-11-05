"""
LLM Client
===========
Thin wrapper around OpenAI's API for calling LLM models.
Uses the openai package directly — no Rust compilation needed.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from typing import Optional

import openai
from openai import (
    OpenAI,
    APIError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
)


class LLMClient:
    """Wrapper around the OpenAI SDK for structured LLM calls with automatic retry logic."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
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
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self._cache: dict[tuple[str, str, float], tuple[str, int]] = {}

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> tuple[str, int]:
        """
        Make an LLM call and return (response_text, token_count) with retry logic.

        Args:
            system_prompt: System-level instructions for the LLM.
            user_prompt: The user-facing prompt content.
            temperature: Override temperature for this call.

        Returns:
            Tuple of (response_text, total_tokens_used).
        """
        temp = temperature if temperature is not None else self.temperature
        
        # Check cache for fully deterministic temperature=0 calls (C-5)
        cache_key = (system_prompt, user_prompt, temp)
        if temp == 0.0 and cache_key in self._cache:
            return self._cache[cache_key]

        delay = self.initial_delay
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temp,
                    max_tokens=self.max_tokens,
                )
                text = response.choices[0].message.content or ""
                tokens = response.usage.total_tokens if response.usage else 0
                
                # Cache successful deterministic responses
                if temp == 0.0:
                    self._cache[cache_key] = (text, tokens)
                return text, tokens

            except Exception as e:
                # Consolidate exception handling for retryable errors (D-3)
                is_retryable = False
                if isinstance(e, (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)):
                    is_retryable = True
                elif isinstance(e, APIError):
                    status_code = getattr(e, "status_code", None)
                    if status_code is None or status_code in (500, 502, 503, 504):
                        is_retryable = True

                if is_retryable and attempt < self.max_retries:
                    sleep_time = delay * (1.0 + random.random() * 0.1)
                    time.sleep(sleep_time)
                    delay *= self.backoff_factor
                else:
                    raise e

        raise RuntimeError("LLM call failed after all retries.")

    def call_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> tuple[dict, int]:
        """
        Make an LLM call expecting structured JSON output.
        Parses the response as JSON. Falls back to regex extraction.

        Returns:
            Tuple of (parsed_dict, total_tokens_used).
        """
        text, tokens = self.call(
            system_prompt=system_prompt + "\n\nRespond ONLY with valid JSON.",
            user_prompt=user_prompt,
            temperature=temperature,
        )
        # Try direct JSON parse first
        try:
            return json.loads(text), tokens
        except json.JSONDecodeError:
            pass

        # Fallback: extract JSON from markdown code block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1)), tokens
            except json.JSONDecodeError:
                pass

        # Last resort: return raw text as a dict
        return {"raw_response": text, "parse_error": True}, tokens
