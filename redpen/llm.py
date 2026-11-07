"""thin wrapper around gemini: structured json calls, grounded search calls, embeddings.

every call retries transient failures and walks a list of fallback models when a model
is missing (404) or its free-tier quota is exhausted (429), so one bad model never kills a run.
"""

import json
import re
import threading
import time
from typing import TypeVar

import numpy as np
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from . import config

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    pass


_client = None
_client_lock = threading.Lock()


def client() -> genai.Client:
    """one shared client. the lock matters: qc runs many calls in parallel threads, and two
    threads creating clients at once left one of them holding a closed http connection."""
    global _client
    if not config.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY is not set. put it in .env and restart the server.")
    with _client_lock:
        if _client is None:
            # hard timeout: an overloaded model sometimes accepts a request and never answers
            _client = genai.Client(api_key=config.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=150_000))
        return _client


def _models(fast: bool = False) -> list[str]:
    out = [config.FAST_MODEL] if fast else []
    out += [m for m in [config.MODEL, *config.FALLBACK_MODELS] if m not in out]
    return out


def _retry_delay(err: Exception) -> float | None:
    m = re.search(r"retry(?:Delay)?['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", str(err))
    return float(m.group(1)) if m else None


class _RateLimiter:
    """keeps each model under its requests-per-minute budget across all threads. the free tier
    allows ~15 rpm per model and qc runs many calls in parallel; queueing here is cheaper than
    collecting 429s and backing off."""

    def __init__(self, rpm: int):
        self.rpm, self.calls, self.lock = rpm, {}, threading.Lock()

    def wait(self, key: str) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                q = [t for t in self.calls.get(key, []) if now - t < 60]
                if len(q) < self.rpm:
                    q.append(now)
                    self.calls[key] = q
                    return
                delay = 60 - (now - q[0]) + 0.05
                self.calls[key] = q
            time.sleep(delay)


_limiter = _RateLimiter(config.RPM_PER_MODEL)


def _call(fn, what: str, fast: bool = False, limit_key: str | None = None):
    last: Exception | None = None
    for model in _models(fast):
        for attempt in range(5):
            try:
                _limiter.wait(limit_key or model)
                return fn(model)
            except errors.ClientError as e:
                last = e
                if e.code == 404:
                    break  # model not available on this key, try the next one
                if e.code == 429:
                    if "PerDay" in str(e) or attempt >= 4:
                        break  # a daily limit never recovers by waiting: next model
                    # per-minute limit: it resets within a minute, so wait and retry the same model
                    time.sleep(max(_retry_delay(e) or 0, 6 * (attempt + 1)))
                    continue
                raise LLMError(f"{what}: {e.message or e}") from e
            except errors.ServerError as e:
                last = e
                if attempt >= 1:
                    break  # overloaded (503/504) twice: the next model is a better bet than waiting
                time.sleep(3)
            except (ValidationError, json.JSONDecodeError, LLMError) as e:
                last = e  # malformed output: just ask again
    raise LLMError(f"{what} failed after retries: {last}")


def _strip_fences(text: str) -> str:
    """remove a ```json wrapper around the whole reply. only the outer wrapper: lesson json
    legitimately contains ```python blocks inside its strings."""
    text = text.strip()
    m = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    return m.group(1) if m else text


def generate(prompt: str, schema: type[T], *, system: str | None = None, temperature: float = 0.3,
             what: str = "llm call", fast: bool = False, thinking: str | None = None) -> T:
    """fast=True starts with the cheap model. thinking='low' trims reasoning for simple tasks."""

    def fn(model: str) -> T:
        r = client().models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=temperature,
                response_mime_type="application/json",
                response_schema=schema,
                thinking_config=types.ThinkingConfig(thinking_level=thinking) if thinking else None,
            ),
        )
        if not r.text:
            reason = r.candidates[0].finish_reason if r.candidates else "no candidates"
            raise LLMError(f"empty response ({reason})")
        return schema.model_validate_json(_strip_fences(r.text))

    return _call(fn, what, fast)


def grounded(prompt: str, *, what: str = "grounded search", fast: bool = True) -> tuple[str, list[dict]]:
    """free-text answer from gemini with google search grounding, plus the web pages it used."""

    def fn(model: str):
        r = client().models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        pages = []
        try:
            for ch in r.candidates[0].grounding_metadata.grounding_chunks or []:
                if ch.web:
                    pages.append({"title": ch.web.title, "url": ch.web.uri})
        except (AttributeError, IndexError, TypeError):
            pass
        return r.text or "", pages

    return _call(fn, what, fast)


def parse_json_loose(text: str):
    text = _strip_fences(text)
    for opener, closer in (("[", "]"), ("{", "}")):
        i, j = text.find(opener), text.rfind(closer)
        if i != -1 and j > i:
            try:
                return json.loads(text[i : j + 1])
            except json.JSONDecodeError:
                continue
    raise LLMError("could not parse json from model output")


def embed(texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> np.ndarray:
    vecs: list[list[float]] = []
    for i in range(0, len(texts), 90):
        batch = [t[:6000] for t in texts[i : i + 90]]

        def fn(_model: str, batch=batch):
            r = client().models.embed_content(
                model=config.EMBED_MODEL,
                contents=batch,
                config=types.EmbedContentConfig(task_type=task, output_dimensionality=768),
            )
            return [e.values for e in r.embeddings]

        vecs.extend(_call(fn, "embedding", limit_key=config.EMBED_MODEL))
    arr = np.array(vecs, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return arr / norms
