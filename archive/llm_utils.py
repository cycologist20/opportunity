# ok_mvp/llm_utils.py
from __future__ import annotations

import os
from typing import List

from .logger import get_logger
from .config import (
    LLM_MODEL,
    CHUNK_MAX_CHARS,
    CORPUS_HARD_CAP_CHARS,
    MAX_MAP_SUMMARIES_FOR_REDUCE,
)

logger = get_logger()

# Load .env so OPENAI_API_KEY is available for the client
try:
    from dotenv import load_dotenv  # python-dotenv
    load_dotenv()
except Exception:
    pass

# Optional OpenAI client (installed in this project)
try:
    from openai import OpenAI  # openai>=1.x
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found in environment (check your .env).")
    _openai_client: OpenAI | None = OpenAI()
except Exception as e:
    logger.warning(f"OpenAI client init failed: {e}")
    _openai_client = None


def _approx_token_len(text: str) -> int:
    # Very rough heuristic: ~4 chars/token
    return max(1, len(text) // 4)


def chunk_text(text: str) -> List[str]:
    """Split text into chunks <= CHUNK_MAX_CHARS, preferring paragraph boundaries."""
    if not text:
        return []

    if len(text) > CORPUS_HARD_CAP_CHARS:
        logger.warning(
            f"Corpus length {len(text):,} exceeds hard cap {CORPUS_HARD_CAP_CHARS:,}. Truncating."
        )
        text = text[:CORPUS_HARD_CAP_CHARS]

    chunks: List[str] = []
    buf: List[str] = []
    buf_len = 0

    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if buf_len + len(para) + 2 <= CHUNK_MAX_CHARS:
            buf.append(para)
            buf_len += len(para) + 2
        else:
            if buf:
                chunks.append("\n\n".join(buf))
            if len(para) > CHUNK_MAX_CHARS:
                start = 0
                while start < len(para):
                    end = min(start + CHUNK_MAX_CHARS, len(para))
                    chunks.append(para[start:end])
                    start = end
                buf, buf_len = [], 0
            else:
                buf = [para]
                buf_len = len(para)

    if buf:
        chunks.append("\n\n".join(buf))

    return chunks


def _openai_chat(prompt: str, content: str) -> str:
    """Single call wrapper to OpenAI Chat Completions; returns text or raises."""
    if _openai_client is None:
        raise RuntimeError("OPENAI_API_KEY not configured or openai client not available.")

    messages = [
        {"role": "system", "content": "You are a concise research synthesizer."},
        {"role": "user", "content": f"{prompt}\n\n---\n\n{content}"},
    ]

    try:
        resp = _openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.2,
        )
        txt = resp.choices[0].message.content or ""
        return txt.strip()
    except Exception as e:
        raise RuntimeError(str(e))


def call_llm(prompt: str, chunks: List[str]) -> str:
    """
    Robust map-reduce summarization:
      - Map: summarize each chunk
      - Reduce: synthesize the summaries
    """
    if not chunks:
        return "No input text provided."

    # Map
    map_summaries: List[str] = []
    for i, ch in enumerate(chunks, 1):
        try:
            summary = _openai_chat(
                prompt=("Summarize the following section. Focus on key facts, trends, "
                        "implications, and opportunities. Be concise and bulleted."),
                content=ch,
            )
        except Exception as e:
            logger.warning(f"LLM map step failed on chunk {i}: {e}")
            summary = ""
        if summary:
            map_summaries.append(summary)

    if not map_summaries:
        return "No summaries produced (all map steps failed)."

    # Reduce (cap number of summaries to keep context small)
    reduce_input = "\n\n---\n\n".join(map_summaries[:MAX_MAP_SUMMARIES_FOR_REDUCE])
    try:
        final = _openai_chat(
            prompt=(f"{prompt}\n\n"
                    "You are given bullet summaries from multiple sections. "
                    "Synthesize them into a single, concise set of bullet points with "
                    "clear, actionable insights and opportunities. Avoid repetition."),
            content=reduce_input,
        )
    except Exception as e:
        logger.warning(f"LLM reduce step failed; returning concatenated map summaries. Error: {e}")
        final = reduce_input

    return final or "No synthesis produced."
