# ok_mvp/arxiv_module.py
import io
import json
import re
from pathlib import Path
from typing import List, Dict, Any

import arxiv
import requests
from pypdf import PdfReader

from .logger import get_logger
from .config import TOP_N_ARXIV_PAPERS
from .llm_utils import chunk_text, call_llm
from .cache_utils import get_from_cache, save_to_cache

logger = get_logger()


def _create_opportunities_prompt(num_sources: int) -> str:
    """Create a prompt that instructs the LLM to generate opportunities with source references."""
    return f"""Analyze the following academic paper summaries and identify actionable business opportunities.

Each summary is labeled with [SOURCE X] where X is a number from 0 to {num_sources-1}.

For each opportunity you identify, you MUST:
1. Provide a clear, concise idea (1-2 sentences)
2. Provide a detailed description explaining the opportunity (2-3 sentences)
3. List the specific source numbers that support this opportunity

Format your response EXACTLY as follows:

OPPORTUNITY 1:
IDEA: [Brief opportunity statement]
DESCRIPTION: [Detailed explanation of the opportunity]
SOURCES: [comma-separated list of source numbers, e.g., 0,2,4]

OPPORTUNITY 2:
IDEA: [Brief opportunity statement]
DESCRIPTION: [Detailed explanation of the opportunity]
SOURCES: [comma-separated list of source numbers, e.g., 1,3]

Continue this pattern for all opportunities you identify. Be specific about which sources support each opportunity."""


def _parse_opportunities_response(llm_response: str) -> List[Dict[str, Any]]:
    """Parse the LLM response to extract opportunities with evidence indices."""
    opportunities = []
    
    # Split response into opportunity blocks
    opportunity_blocks = re.split(r'OPPORTUNITY \d+:', llm_response)[1:]  # Skip first empty element
    
    for block in opportunity_blocks:
        block = block.strip()
        if not block:
            continue
            
        # Extract IDEA, DESCRIPTION, and SOURCES using regex
        idea_match = re.search(r'IDEA:\s*(.+?)(?=\nDESCRIPTION:)', block, re.DOTALL)
        desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?=\nSOURCES:)', block, re.DOTALL)
        sources_match = re.search(r'SOURCES:\s*(.+?)(?=\n|$)', block, re.DOTALL)
        
        if idea_match and desc_match and sources_match:
            idea = idea_match.group(1).strip()
            description = desc_match.group(1).strip()
            sources_text = sources_match.group(1).strip()
            
            # Parse source indices
            supporting_evidence_indices = []
            try:
                # Extract numbers from sources text
                source_numbers = re.findall(r'\d+', sources_text)
                supporting_evidence_indices = [int(num) for num in source_numbers]
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse source indices from: {sources_text}. Error: {e}")
                supporting_evidence_indices = []
            
            opportunities.append({
                "idea": idea,
                "description": description,
                "supporting_evidence_indices": supporting_evidence_indices
            })
        else:
            logger.warning(f"Failed to parse opportunity block: {block[:100]}...")
    
    return opportunities


def _search_arxiv(query: str, limit: int) -> List[Dict]:
    search = arxiv.Search(
        query=query,
        max_results=limit,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    # arxiv 2.x returns an iterator of arxiv.Result
    return list(search.results())


def _get_arxiv_id(entry) -> str:
    """Extract ArXiv ID from entry for use as cache key."""
    # ArXiv entries have an entry_id like "http://arxiv.org/abs/2301.12345v1"
    entry_id = getattr(entry, "entry_id", "")
    if entry_id:
        # Extract just the ID part (e.g., "2301.12345v1")
        import re
        match = re.search(r'arxiv\.org/abs/(.+)$', entry_id)
        if match:
            return match.group(1)
    
    # Fallback to title-based ID if entry_id parsing fails
    title = getattr(entry, "title", "unknown")
    return title.replace(" ", "_").replace("/", "_")[:50]


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
    """
    Analyze arXiv papers for a given topic and produce enriched JSON output.
    
    Args:
        topic: The research topic to search for on arXiv
        
    Returns:
        None (writes JSON file to output directory)
    """
    logger.info(f"[arXiv] Topic: {topic} | TopN={TOP_N_ARXIV_PAPERS}")
    entries = _search_arxiv(topic, TOP_N_ARXIV_PAPERS)

    # Build source evidence list and collect paper summaries
    source_evidence = []
    paper_summaries = []

    for idx, e in enumerate(entries):
        title = getattr(e, "title", "")
        authors = [a.name for a in getattr(e, "authors", [])]
        pdf_url = getattr(e, "pdf_url", "")
        arxiv_id = _get_arxiv_id(e)
        
        # Check cache first
        text = get_from_cache("arxiv", arxiv_id)
        
        if not text:
            # Cache miss - download and extract text from PDF
            pdf_bytes = _download_pdf_bytes(e)
            text = _pdf_to_text(pdf_bytes)
            
            # Save to cache if we got text
            if text:
                save_to_cache("arxiv", arxiv_id, text)
        
        if text:
            # Generate individual paper summary
            chunks = chunk_text(text)
            prompt = (
                "Summarize this paper for a product strategist. Extract problem, methods, "
                "key findings, and potential business applications."
            )
            summary = call_llm(prompt, chunks) if chunks else "No text extracted."
            
            # Extract key quote from abstract or first part of text
            key_quote = text[:300].strip()
            if len(text) > 300:
                key_quote += "..."
            
            # Add to source evidence
            source_evidence.append({
                "index": idx,
                "source_type": "arXiv",
                "title": title,
                "authors": authors,
                "url": pdf_url,
                "key_quote": key_quote
            })
            
            # Add summary with source reference for final synthesis
            paper_summaries.append(f"[SOURCE {idx}] {title} by {', '.join(authors)}\n{summary}")
        else:
            logger.warning(f"No text extracted from paper: {title}")

    if not paper_summaries:
        logger.warning(f"[arXiv] No paper summaries generated for topic: {topic}")
        # Return empty structure if no summaries
        out = {
            "synthesized_opportunities": [],
            "source_evidence": []
        }
    else:
        # Create enhanced prompt for linked opportunities
        corpus = "\n\n---\n\n".join(paper_summaries)
        chunks = chunk_text(corpus)
        
        prompt = _create_opportunities_prompt(len(source_evidence))
        llm_response = call_llm(prompt, chunks)
        
        # Parse LLM response to extract opportunities with evidence indices
        synthesized_opportunities = _parse_opportunities_response(llm_response)
        
        out = {
            "synthesized_opportunities": synthesized_opportunities,
            "source_evidence": source_evidence
        }

    # Write output file
    out_path = Path("output") / f"{topic.replace(' ', '_')}_arxiv.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    logger.info(f"[arXiv] Wrote {out_path} with {len(out['synthesized_opportunities'])} opportunities and {len(out['source_evidence'])} sources")
