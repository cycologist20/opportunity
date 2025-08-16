# ok_mvp/arxiv_module.py
import asyncio
import os
import arxiv
import pypdf

# Assuming these utilities are in your project
from .cache_utils import get_from_cache, save_to_cache
from .logger import get_logger

logger = get_logger()

def _search_papers(query, max_results):
    logger.info(f"  [ArXiv] Searching for top {max_results} papers for query: '{query}'")
    search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
    papers = list(search.results())
    logger.info(f"  [ArXiv] Found {len(papers)} papers.")
    return papers

def _get_paper_text(paper):
    paper_id = paper.entry_id.split('/')[-1]
    cached = get_from_cache("arxiv", paper_id)
    if cached: return cached
    try:
        pdf_path = paper.download_pdf()
        text = "".join(page.extract_text() or "" for page in pypdf.PdfReader(pdf_path).pages)
        os.remove(pdf_path)
        save_to_cache("arxiv", paper_id, text)
        return text
    except Exception as e:
        logger.error(f"  [ArXiv] Could not process paper '{paper.title}': {e}")
        return ""

async def research(search_terms: list[str], config: dict) -> tuple:
    print("  Calling ArXiv Module...")
    max_results = config.get("MAX_RESULTS_PER_SOURCE", 3)
    main_query = search_terms[0] if search_terms else ""
    if not main_query:
        return [], []

    loop = asyncio.get_running_loop()
    papers = await loop.run_in_executor(None, _search_papers, main_query, max_results)
    
    source_evidence, content_for_synthesis = [], []
    for paper in papers:
        paper_text = await loop.run_in_executor(None, _get_paper_text, paper)
        if paper_text:
            source_evidence.append({
                "index": -1, "source_type": "arXiv",
                "title": paper.title, "author": ", ".join(str(a) for a in paper.authors),
                "url": paper.entry_id, "key_quote": "",
            })
            content_for_synthesis.append(paper_text)
    return source_evidence, content_for_synthesis