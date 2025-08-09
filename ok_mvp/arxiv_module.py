# ok_mvp/arxiv_module.py
import io
import json
from pathlib import Path
from typing import List, Dict

import arxiv
import requests
from pypdf import PdfReader

from .logger import get_logger
from .config import TOP_N_ARXIV_PAPERS
from .llm_utils import chunk_text, call_llm

logger = get_logger()


def _search_arxiv(query: str, limit: int) -> List[Dict]:
    search = arxiv.Search(
        query=query,
        max_results=limit,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    # arxiv 2.x returns an iterator of arxiv.Result
    return list(search.results())


def _download_pdf_bytes(entry) -> bytes:
    """Download PDF via entry.pdf_url (arxiv 2.x), returning raw bytes."""
    pdf_url = getattr(entry, "pdf_url", "")
    if not pdf_url:
        return b""
    try:
        resp = requests.get(pdf_url, timeout=30)
        if resp.status_code == 200 and resp.content:
            return resp.content
        logger.warning(
            f"PDF HTTP {resp.status_code} for {getattr(entry, 'title', 'unknown')}"
        )
        return b""
    except Exception as e:
        logger.warning(f"PDF download failed for {getattr(entry, 'title', 'unknown')}: {e}")
        return b""


def _pdf_to_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes:
        return ""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                texts.append("")
        return "\n".join(texts)
    except Exception as e:
        logger.warning(f"PDF parse failed: {e}")
        return ""


def fetch_and_analyze_arxiv(topic: str):
    logger.info(f"[arXiv] Topic: {topic} | TopN={TOP_N_ARXIV_PAPERS}")
    entries = _search_arxiv(topic, TOP_N_ARXIV_PAPERS)

    papers = []
    per_paper_summaries = []

    for e in entries:
        title = getattr(e, "title", "")
        authors = [a.name for a in getattr(e, "authors", [])]
        pdf_bytes = _download_pdf_bytes(e)
        text = _pdf_to_text(pdf_bytes)
        chunks = chunk_text(text)
        prompt = (
            "Summarize this paper for a product strategist. Extract problem, methods, "
            "key findings, and potential business applications."
        )
        summary = call_llm(prompt, chunks) if chunks else "No text extracted."
        per_paper_summaries.append({"title": title, "summary": summary})
        papers.append(
            {
                "title": title,
                "authors": authors,
                "entry_id": getattr(e, "entry_id", ""),
                "pdf_url": getattr(e, "pdf_url", ""),
                "extracted_chars": len(text),
            }
        )

    combined = "\n\n".join(s["summary"] for s in per_paper_summaries if s.get("summary"))
    final = (
        call_llm(
            "Synthesize cross-paper insights into concrete market opportunities and risks. "
            "Be concise, actionable, and specific.",
            chunk_text(combined),
        )
        if combined
        else "No summaries produced."
    )

    out = {
        "topic": topic,
        "source": "arxiv",
        "top_n": TOP_N_ARXIV_PAPERS,
        "papers": papers,
        "per_paper_summaries": per_paper_summaries,
        "synthesis": final,
    }
    out_path = Path("output") / f"{topic.replace(' ', '_')}_arxiv.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    logger.info(f"[arXiv] Wrote {out_path}")
