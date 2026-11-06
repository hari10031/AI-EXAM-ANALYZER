"""Gemini embeddings + vector helpers.

Vectors are L2-normalized and stored as JSON float arrays in a TEXT column, so cosine
similarity is a plain dot product and storage works identically on SQLite and Postgres.
pgvector replaces this only if the question bank outgrows in-memory similarity
(thousands of rows) — see Implmentation-03.md.
"""

import json
import time

import numpy as np
from google import genai
from google.genai import types

from .config import get_settings

# Gemini embed_content accepts up to 100 texts per request
BATCH_SIZE = 100
# Free-tier backoff for 429/503
RETRIES = 4
RETRY_WAIT_SECONDS = 20


class EmbeddingError(Exception):
    pass


def normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def to_json(vec: np.ndarray) -> str:
    return json.dumps([round(float(x), 6) for x in vec])


def from_json(raw: str) -> np.ndarray:
    return np.asarray(json.loads(raw), dtype=np.float32)


def embed_texts(texts: list[str]) -> list[np.ndarray]:
    """Embed texts with Gemini; returns L2-normalized vectors. Normalization is required
    because truncated output_dimensionality embeddings are not unit-length."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise EmbeddingError(
            "GEMINI_API_KEY is not set. Copy backend/.env.example to backend/.env and add "
            "your key (free at https://aistudio.google.com/apikey)."
        )

    client = genai.Client(api_key=settings.gemini_api_key)
    config = {
        "output_dimensionality": settings.embed_dim,
        "task_type": "SEMANTIC_SIMILARITY",
    }

    def call(batch: list[str]) -> list:
        # A bare list of strings is folded into ONE content (single embedding back);
        # typed Content objects are what makes batchEmbedContents actually batch.
        contents = [types.Content(parts=[types.Part(text=t)]) for t in batch]
        last_exc: Exception | None = None
        for attempt in range(RETRIES):
            try:
                return client.models.embed_content(
                    model=settings.gemini_embed_model, contents=contents, config=config
                ).embeddings
            except Exception as exc:
                last_exc = exc
                transient = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc) or "503" in str(exc)
                if transient and attempt < RETRIES - 1:
                    time.sleep(RETRY_WAIT_SECONDS)
                else:
                    break
        raise EmbeddingError(f"Gemini embedding call failed: {last_exc}") from last_exc

    vectors: list[np.ndarray] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        embeddings = call(batch)
        if len(embeddings) != len(batch):
            raise EmbeddingError(
                f"Expected {len(batch)} embeddings, got {len(embeddings)} — aborting "
                "instead of silently storing a partial set."
            )
        for emb in embeddings:
            vectors.append(normalize(np.asarray(emb.values, dtype=np.float32)))
    return vectors
