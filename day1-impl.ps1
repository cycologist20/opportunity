# day1-impl-fixed.ps1
# Day-1 implementation: YouTube search+transcripts, arXiv PDFs+summaries, LLM plumbing.
# Safe for Windows PowerShell 5.1 (no here-strings, no trailing commas)

param(
  [string]$ProjectRoot = (Get-Location).Path
)

function Write-Text {
  param([string]$Path, [string[]]$Lines)
  [System.IO.Directory]::CreateDirectory((Split-Path $Path -Parent)) | Out-Null
  [System.IO.File]::WriteAllLines($Path, $Lines)
  Write-Host "Wrote: $Path"
}

Push-Location $ProjectRoot

# --- Dependencies ---
if (Get-Command poetry -ErrorAction SilentlyContinue) {
  if (-not (Test-Path "$ProjectRoot\pyproject.toml")) {
    poetry init -n --name "ok-mvp" --description "Wizards Toolkit MVP CLI" --license "MIT" | Out-Null
  }
  poetry add youtubesearchpython youtube-transcript-api arxiv pypdf openai python-dotenv argparse | Out-Null
  poetry add --dev black ruff | Out-Null
} else {
  Write-Warning "Poetry not found; install later. Needed deps: youtubesearchpython, youtube-transcript-api, arxiv, pypdf, openai, python-dotenv, argparse"
}

# --- ok_mvp/config.py ---
$cfg = @(
  '# Central configuration',
  'TOP_N_YOUTUBE_VIDEOS = 10',
  'TOP_N_ARXIV_PAPERS = 5',
  '',
  '# Chunking (approx characters per chunk; conservative)',
  'CHUNK_SIZE = 8000',
  '',
  '# Default LLM model (can be overridden via env OPENAI_MODEL)',
  'LLM_MODEL = "gpt-4o-mini"'
)
Write-Text "$ProjectRoot\ok_mvp\config.py" $cfg

# --- ok_mvp/llm_utils.py ---
$llm = @(
  'import os',
  'from typing import List',
  'from .logger import get_logger',
  'from .config import CHUNK_SIZE, LLM_MODEL',
  'from dotenv import load_dotenv',
  '',
  'logger = get_logger()',
  'load_dotenv()',
  '',
  'def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:',
  '    if not text:',
  '        return []',
  '    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]',
  '',
  'def _openai_client():',
  '    try:',
  '        from openai import OpenAI',
  '        return OpenAI()',
  '    except Exception as e:',
  '        logger.warning(f"OpenAI SDK not available or misconfigured: {e}")',
  '        return None',
  '',
  'def call_llm(prompt: str, chunks: List[str]) -> str:',
  '    """Calls OpenAI if configured, else returns a placeholder synthesis."""',
  '    model = os.getenv("OPENAI_MODEL", LLM_MODEL)',
  '    api_key = os.getenv("OPENAI_API_KEY")',
  '    if not api_key:',
  '        logger.warning("OPENAI_API_KEY not set; returning placeholder.")',
  '        return "Placeholder synthesis (no OPENAI_API_KEY)."',
  '',
  '    client = _openai_client()',
  '    if client is None:',
  '        return "Placeholder synthesis (OpenAI client unavailable)."',
  '',
  '    combined = "" if not chunks else "\\n\\n".join(chunks)',
  '    try:',
  '        resp = client.chat.completions.create(',
  '            model=model,',
  '            messages=[',
  '                {"role": "system", "content": "You are a concise research assistant."},',
  '                {"role": "user", "content": f"{prompt}\\n\\nTEXT:\\n{combined}"}',
  '            ],',
  '            temperature=0.2',
  '        )',
  '        return resp.choices[0].message.content.strip() if resp and resp.choices else ""',
  '    except Exception as e:',
  '        logger.warning(f"LLM call failed; returning placeholder. Error: {e}")',
  '        return "Placeholder synthesis (LLM call failed)."'
)
Write-Text "$ProjectRoot\ok_mvp\llm_utils.py" $llm

# --- ok_mvp/youtube_module.py ---
$yt = @(
  'import json',
  'from pathlib import Path',
  'from typing import List, Dict',
  'from youtubesearchpython import VideosSearch',
  'from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable',
  'from .logger import get_logger',
  'from .config import TOP_N_YOUTUBE_VIDEOS',
  'from .llm_utils import chunk_text, call_llm',
  '',
  'logger = get_logger()',
  '',
  'def _search_videos(query: str, limit: int) -> List[Dict]:',
  '    vs = VideosSearch(query, limit=limit)',
  '    result = vs.result() or {}',
  '    return result.get("result", [])',
  '',
  'def _video_id_from_link(link: str) -> str:',
  '    if "v=" in link:',
  '        return link.split("v=", 1)[1].split("&", 1)[0]',
  '    return link.rsplit("/", 1)[-1]',
  '',
  'def _fetch_transcript_text(video_id: str) -> str:',
  '    try:',
  '        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)',
  '        try:',
  '            transcript = transcript_list.find_transcript(["en"])',
  '        except Exception:',
  '            transcript = next(iter(transcript_list), None)',
  '        if not transcript:',
  '            return ""',
  '        lines = transcript.fetch()',
  '        return " ".join(chunk.get("text", "") for chunk in lines)',
  '    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:',
  '        logger.warning(f"Transcript unavailable for {video_id}: {e}")',
  '        return ""',
  '    except Exception as e:',
  '        logger.warning(f"Transcript error for {video_id}: {e}")',
  '        return ""',
  '',
  'def fetch_and_analyze_youtube(topic: str):',
  '    logger.info(f"[YouTube] Topic: {topic} | TopN={TOP_N_YOUTUBE_VIDEOS}")',
  '    results = _search_videos(topic, TOP_N_YOUTUBE_VIDEOS)',
  '    videos = []',
  '    corpus_parts = []',
  '    for r in results:',
  '        title = r.get("title", "")',
  '        link = r.get("link", "")',
  '        vid = _video_id_from_link(link) if link else ""',
  '        transcript = _fetch_transcript_text(vid) if vid else ""',
  '        if transcript:',
  '            corpus_parts.append(transcript)',
  '        videos.append({',
  '            "title": title,',
  '            "link": link,',
  '            "video_id": vid,',
  '            "has_transcript": bool(transcript),',
  '            "transcript_chars": len(transcript) if transcript else 0',
  '        })',
  '',
  '    corpus = "\\n\\n".join(corpus_parts)',
  '    chunks = chunk_text(corpus)',
  '    prompt = "Summarize the core insights, trends, and actionable opportunities from these YouTube transcripts. Output concise bullet points suitable for an Opportunity Brief."',
  '    summary = call_llm(prompt, chunks)',
  '',
  '    out = {',
  '        "topic": topic,',
  '        "source": "youtube",',
  '        "top_n": TOP_N_YOUTUBE_VIDEOS,',
  '        "videos": videos,',
  '        "summary": summary',
  '    }',
  '    out_path = Path("output") / f"{topic.replace('' '', ''_'')}_youtube.json"',
  '    out_path.parent.mkdir(parents=True, exist_ok=True)',
  '    with open(out_path, "w", encoding="utf-8") as f:',
  '        json.dump(out, f, indent=2)',
  '    logger.info(f"[YouTube] Wrote {out_path}")'
)
Write-Text "$ProjectRoot\ok_mvp\youtube_module.py" $yt

# --- ok_mvp/arxiv_module.py ---
$ax = @(
  'import json',
  'from pathlib import Path',
  'import tempfile',
  'from typing import List, Dict',
  'import arxiv',
  'from pypdf import PdfReader',
  'from .logger import get_logger',
  'from .config import TOP_N_ARXIV_PAPERS',
  'from .llm_utils import chunk_text, call_llm',
  '',
  'logger = get_logger()',
  '',
  'def _search_arxiv(query: str, limit: int) -> List[Dict]:',
  '    search = arxiv.Search(query=query, max_results=limit, sort_by=arxiv.SortCriterion.Relevance)',
  '    return list(search.results())',
  '',
  'def _download_pdf(entry) -> bytes:',
  '    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:',
  '        try:',
  '            # Prefer new helper if available',
  '            entry.download_pdf(filename=tmp.name)',
  '            return Path(tmp.name).read_bytes()',
  '        except Exception:',
  '            try:',
  '                entry.download(filename=tmp.name)',
  '                return Path(tmp.name).read_bytes()',
  '            except Exception as e:',
  '                logger.warning(f"PDF download failed for {getattr(entry, ''title'', ''unknown'')}: {e}")',
  '                return b""',
  '',
  'def _pdf_to_text(pdf_bytes: bytes) -> str:',
  '    if not pdf_bytes:',
  '        return ""',
  '    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:',
  '        tmp.write(pdf_bytes)',
  '        tmp.flush()',
  '        try:',
  '            reader = PdfReader(tmp.name)',
  '            pages = []',
  '            for p in reader.pages:',
  '                try:',
  '                    pages.append(p.extract_text() or "")',
  '                except Exception:',
  '                    pages.append("")',
  '            return "\\n".join(pages)',
  '        except Exception as e:',
  '            logger.warning(f"PDF parse failed: {e}")',
  '            return ""',
  '',
  'def fetch_and_analyze_arxiv(topic: str):',
  '    logger.info(f"[arXiv] Topic: {topic} | TopN={TOP_N_ARXIV_PAPERS}")',
  '    entries = _search_arxiv(topic, TOP_N_ARXIV_PAPERS)',
  '    papers = []',
  '    per_paper_summaries = []',
  '    for e in entries:',
  '        title = getattr(e, "title", "")',
  '        authors = [a.name for a in getattr(e, "authors", [])]',
  '        pdf_bytes = _download_pdf(e)',
  '        text = _pdf_to_text(pdf_bytes)',
  '        chunks = chunk_text(text)',
  '        prompt = "Summarize this paper for a product strategist. Extract problem, methods, key findings, and potential business applications."',
  '        summary = call_llm(prompt, chunks) if chunks else "No text extracted."',
  '        per_paper_summaries.append({"title": title, "summary": summary})',
  '        papers.append({',
  '            "title": title,',
  '            "authors": authors,',
  '            "entry_id": getattr(e, "entry_id", ""),',
  '            "pdf_url": getattr(e, "pdf_url", ""),',
  '            "extracted_chars": len(text)',
  '        })',
  '',
  '    combined = "\\n\\n".join(s["summary"] for s in per_paper_summaries if s.get("summary"))',
  '    final = call_llm(',
  '        "Synthesize cross-paper insights into concrete market opportunities and risks. Be concise, actionable, and specific.",',
  '        chunk_text(combined)',
  '    ) if combined else "No summaries produced."',
  '',
  '    out = {',
  '        "topic": topic,',
  '        "source": "arxiv",',
  '        "top_n": TOP_N_ARXIV_PAPERS,',
  '        "papers": papers,',
  '        "per_paper_summaries": per_paper_summaries,',
  '        "synthesis": final',
  '    }',
  '    out_path = Path("output") / f"{topic.replace('' '', ''_'')}_arxiv.json"',
  '    out_path.parent.mkdir(parents=True, exist_ok=True)',
  '    with open(out_path, "w", encoding="utf-8") as f:',
  '        json.dump(out, f, indent=2)',
  '    logger.info(f"[arXiv] Wrote {out_path}")'
)
Write-Text "$ProjectRoot\ok_mvp\arxiv_module.py" $ax

# --- smoke.ps1 ---
$smoke = @(
  '$t = "AI in preventative healthcare"',
  'poetry run python -m ok_mvp --topic $t',
  '$yt = Join-Path "output" (($t -replace " ", "_") + "_youtube.json")',
  '$ax = Join-Path "output" (($t -replace " ", "_") + "_arxiv.json")',
  'if ((Test-Path $yt) -and (Test-Path $ax)) {',
  '  Write-Host "SMOKE PASS"',
  '} else {',
  '  Write-Host "SMOKE FAIL"; exit 1',
  '}'
)
Write-Text "$ProjectRoot\smoke.ps1" $smoke

Pop-Location
Write-Host "Day-1 implementation written."
