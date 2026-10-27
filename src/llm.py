"""llm.py - the one place the app talks to Gemini.

Features:
- retries with a growing pause when Gemini is overloaded (503) or rate limited (429)
- optional fallback model if the main one keeps failing or has been retired (404)
- a disk cache, so the same request is never sent (or paid for) twice

Environment variables:
    GEMINI_API_KEY          required (the google-genai library reads it automatically)
    GEMINI_MODEL            optional, defaults to gemini-3.8-flash
    GEMINI_FALLBACK_MODEL   optional, e.g. a flash-lite model from client.models.list()
"""

import hashlib
import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import errors, types

PRIMARY_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL")
MODELS = [m for m in (PRIMARY_MODEL, FALLBACK_MODEL) if m]

CACHE_DIR = Path(__file__).parent / "gemini_cache"
CACHE_DIR.mkdir(exist_ok=True)


class LLMUnavailable(Exception):
    """Raised when every model keeps failing with a temporary error."""


def _cache_file(key: str) -> Path:
    return CACHE_DIR / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.txt"


def clear_cache() -> None:
    """Delete every cached answer (do this after changing prompts or data)."""
    for f in CACHE_DIR.glob("*.txt"):
        f.unlink()


def ask(
    prompt: str,
    system_instruction: str | None = None,
    use_cache: bool = True,
    attempts_per_model: int = 3,
    response_schema=None,
) -> str:
    """Send a prompt to Gemini and return the text of the answer.

    response_schema: a Pydantic class. If given, Gemini returns JSON matching it
    (used by ingest.py for extraction). The schema is part of the cache key, so
    changing the schema never returns an out-of-date cached extraction.
    """
    schema_key = (
        json.dumps(response_schema.model_json_schema(), sort_keys=True)
        if response_schema
        else ""
    )
    key = f"{system_instruction or ''}\n---\n{schema_key}\n---\n{prompt}"
    cache_file = _cache_file(key)
    if use_cache and cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    client = genai.Client()
    config = None
    if system_instruction or response_schema:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json" if response_schema else None,
            response_schema=response_schema,
        )

    last_problem = "no attempt was made"
    for model in MODELS:
        for attempt in range(attempts_per_model):
            try:
                response = client.models.generate_content(
                    model=model, contents=prompt, config=config
                )
                text = response.text
                if not text:
                    last_problem = f"{model} returned an empty response"
                    break  # try the next model
                if use_cache:
                    cache_file.write_text(text, encoding="utf-8")
                return text

            except errors.ServerError as e:  # 5xx, e.g. 503 high demand
                last_problem = f"{model}: server error {e.code}"
                time.sleep(2 * 2**attempt)  # 2s, 4s, 8s

            except errors.ClientError as e:
                if e.code == 429:  # rate limited
                    last_problem = f"{model}: rate limited"
                    time.sleep(4 * 2**attempt)
                elif e.code == 404:  # model retired / wrong name
                    last_problem = f"{model}: model not found"
                    break  # try the next model
                else:
                    raise  # bad key, bad request, etc. - show the real error

    raise LLMUnavailable(f"Gemini is unavailable right now ({last_problem}).")