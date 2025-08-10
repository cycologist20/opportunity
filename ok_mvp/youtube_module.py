# ok_mvp/youtube_module.py
import json
import re
from pathlib import Path
from typing import List, Dict, Optional

import requests
from yt_dlp import YoutubeDL

# Try to import transcript API symbols, but don't rely on them exclusively
try:
    from youtube_transcript_api import (  # type: ignore
        YouTubeTranscriptApi,
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
    )
except Exception:  # library missing or import issue — we’ll fall back
    YouTubeTranscriptApi = None  # type: ignore
    TranscriptsDisabled = NoTranscriptFound = VideoUnavailable = Exception  # type: ignore

from .logger import get_logger
from .config import TOP_N_YOUTUBE_VIDEOS
from .llm_utils import chunk_text, call_llm

logger = get_logger()


def _create_opportunities_prompt(num_sources: int) -> str:
    """Create a prompt that instructs the LLM to generate opportunities with source references."""
    return f"""Analyze the following YouTube video transcripts and identify actionable business opportunities.

Each transcript is labeled with [SOURCE X] where X is a number from 0 to {num_sources-1}.

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


def _parse_opportunities_response(llm_response: str) -> List[Dict]:
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


def _search_videos(query: str, limit: int) -> List[Dict]:
    """Use yt-dlp to search YouTube without an API key."""
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,  # Changed to False to get more metadata including author
        "noplaylist": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
    entries = info.get("entries", []) if isinstance(info, dict) else []
    out = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        vid = e.get("id") or ""
        title = e.get("title") or ""
        author = e.get("uploader") or e.get("channel") or ""
        url = e.get("webpage_url") or e.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid else "")
        out.append({
            "video_id": vid, 
            "title": title, 
            "link": url,
            "author": author
        })
    return out


def _clean_vtt_to_text(vtt: str) -> str:
    """Convert a simple .vtt payload to plain text (best-effort)."""
    lines = []
    for line in vtt.splitlines():
        # drop WEBVTT header, cue timings, and metadata
        if not line or line.startswith("WEBVTT") or "-->" in line:
            continue
        if re.match(r"^\d+$", line.strip()):  # cue index numbers
            continue
        # remove common VTT tags like <c>...</c>, <00:00:00.000>
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\{\\.*?\}", "", line)
        if line.strip():
            lines.append(line.strip())
    return " ".join(lines)


def _fetch_vtt_via_ytdlp(video_url: str) -> Optional[str]:
    """Fallback: ask yt-dlp for auto/subtitle URLs and fetch the VTT."""
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
        # Prefer English auto-captions, then any language
        caps = info.get("automatic_captions") or info.get("subtitles") or {}
        for lang in ("en", "en-US", "en-GB"):
            if lang in caps and caps[lang]:
                url = caps[lang][0].get("url")
                if url:
                    r = requests.get(url, timeout=30)
                    if r.status_code == 200 and r.text:
                        return _clean_vtt_to_text(r.text)
        # No EN? take first available
        for _, entries in caps.items():
            if entries:
                url = entries[0].get("url")
                if url:
                    r = requests.get(url, timeout=30)
                    if r.status_code == 200 and r.text:
                        return _clean_vtt_to_text(r.text)
    except Exception as e:
        logger.warning(f"yt-dlp caption fetch failed: {e}")
    return None


def _fetch_transcript_text(video_id: str, video_url: str) -> str:
    """Try youtube-transcript-api first; if unavailable, fall back to yt-dlp auto-captions."""
    # 1) youtube-transcript-api path (if available)
    if YouTubeTranscriptApi is not None:
        try:
            if hasattr(YouTubeTranscriptApi, "get_transcript"):
                lines = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])  # type: ignore
                return " ".join(chunk.get("text", "") for chunk in lines)
            elif hasattr(YouTubeTranscriptApi, "list_transcripts"):
                tl = YouTubeTranscriptApi.list_transcripts(video_id)  # type: ignore
                try:
                    tr = tl.find_transcript(["en"])
                except Exception:
                    tr = next(iter(tl), None)
                if tr:
                    lines = tr.fetch()
                    return " ".join(chunk.get("text", "") for chunk in lines)
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
            logger.warning(f"Transcript unavailable for {video_id}: {e}")
        except Exception as e:
            logger.warning(f"Transcript error for {video_id}: {e}")

    # 2) Fallback via yt-dlp captions (VTT)
    vtt_text = _fetch_vtt_via_ytdlp(video_url)
    return vtt_text or ""


def fetch_and_analyze_youtube(topic: str):
    """
    Analyze YouTube videos for a given topic and produce enriched JSON output.
    
    Args:
        topic: The research topic to search for on YouTube
        
    Returns:
        None (writes JSON file to output directory)
    """
    logger.info(f"[YouTube] Topic: {topic} | TopN={TOP_N_YOUTUBE_VIDEOS}")
    results = _search_videos(topic, TOP_N_YOUTUBE_VIDEOS)
    
    # Build source evidence list and collect transcripts
    source_evidence = []
    video_transcripts = []
    
    for idx, r in enumerate(results):
        title = r.get("title", "")
        link = r.get("link", "")
        author = r.get("author", "")
        vid = r.get("video_id", "")
        transcript = _fetch_transcript_text(vid, link) if vid and link else ""
        
        if transcript:
            # Extract a key quote (first 200 characters of transcript)
            key_quote = transcript[:200].strip()
            if len(transcript) > 200:
                key_quote += "..."
            
            source_evidence.append({
                "index": idx,
                "source_type": "YouTube",
                "title": title,
                "author": author,
                "url": link,
                "key_quote": key_quote
            })
            
            # Add transcript with source reference for LLM processing
            video_transcripts.append(f"[SOURCE {idx}] {title} by {author}\n{transcript}")
    
    if not video_transcripts:
        logger.warning(f"[YouTube] No transcripts found for topic: {topic}")
        # Return empty structure if no transcripts
        out = {
            "synthesized_opportunities": [],
            "source_evidence": []
        }
    else:
        # Create enhanced prompt for linked opportunities
        corpus = "\n\n---\n\n".join(video_transcripts)
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
    out_path = Path("output") / f"{topic.replace(' ', '_')}_youtube.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    logger.info(f"[YouTube] Wrote {out_path} with {len(out['synthesized_opportunities'])} opportunities and {len(out['source_evidence'])} sources")
