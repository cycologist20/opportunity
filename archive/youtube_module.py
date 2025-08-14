# ok_mvp/youtube_module.py
import asyncio
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import requests
from yt_dlp import YoutubeDL
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

from .logger import get_logger
from .config import TOP_N_YOUTUBE_VIDEOS
from .llm_utils import call_llm, chunk_text
from .text_utils import vtt_to_text, finalize_text
from .cache_utils import get_from_cache, save_to_cache

logger = get_logger()


def _create_opportunities_prompt(num_sources: int) -> str:
    # This function remains unchanged
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

Continue this pattern for all opportunities you identify."""


def _parse_opportunities_response(llm_response: str) -> List[Dict[str, Any]]:
    # This function remains unchanged
    opportunities = []
    opportunity_blocks = re.split(r'OPPORTUNITY \d+:', llm_response)[1:]
    for block in opportunity_blocks:
        block = block.strip()
        if not block: continue
        idea_match = re.search(r'IDEA:\s*(.+?)(?=\nDESCRIPTION:)', block, re.DOTALL)
        desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?=\nSOURCES:)', block, re.DOTALL)
        sources_match = re.search(r'SOURCES:\s*(.+?)(?=\n|$)', block, re.DOTALL)
        if idea_match and desc_match and sources_match:
            idea = idea_match.group(1).strip()
            description = desc_match.group(1).strip()
            sources_text = sources_match.group(1).strip()
            try:
                source_numbers = re.findall(r'\d+', sources_text)
                supporting_evidence_indices = [int(num) for num in source_numbers]
            except (ValueError, TypeError):
                logger.warning(f"Failed to parse source indices from: {sources_text}. Error: {e}")
                supporting_evidence_indices = []
            opportunities.append({
                "idea": idea,
                "description": description,
                "supporting_evidence_indices": supporting_evidence_indices
            })
    return opportunities

# --- NEW ROBUST TRANSCRIPT LOGIC ---

def _search_videos(query: str, limit: int) -> List[Dict[str, Any]]:
    """Use yt-dlp to search YouTube and get video metadata."""
    logger.info(f"[YouTube] Searching for top {limit} videos for query: '{query}'")
    ydl_opts = {"quiet": True, "skip_download": True, "extract_flat": False, "noplaylist": True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
    entries = info.get("entries", []) if isinstance(info, dict) else []
    
    out = []
    for e in entries:
        if not isinstance(e, dict): continue
        vid = e.get("id") or ""
        out.append({
            "video_id": vid,
            "title": e.get("title") or vid,
            "author": e.get("uploader") or e.g_et("channel") or "N/A",
            "url": e.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
            "raw_info": e # Keep raw info for fallback
        })
    logger.info(f"[YouTube] Found {len(out)} videos.")
    return out

def _fetch_transcript_from_api(video_id: str) -> Optional[str]:
    """Primary Method: Use youtube-transcript-api's get_transcript."""
    try:
        # This is the most direct way to get an English transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])
        text = " ".join([d['text'] for d in transcript_list])
        logger.debug(f"Successfully fetched transcript via API for {video_id}")
        return text
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        logger.warning(f"Transcript unavailable via API for {video_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred with Transcript API for {video_id}: {e}")
        return None

def _fetch_transcript_from_vtt(video_info: Dict) -> Optional[str]:
    """Fallback Method: Use yt-dlp to find and parse VTT caption files."""
    logger.info(f"Attempting VTT fallback for video ID: {video_info['video_id']}")
    subs = video_info['raw_info'].get("subtitles") or {}
    autosubs = video_info['raw_info'].get("automatic_captions") or {}
    
    caption_url = None
    preferred_langs = ['en', 'en-US', 'en-GB']
    
    # Logic to find the best VTT url
    for lang in preferred_langs:
        if lang in subs and subs[lang]:
            caption_url = subs[lang][0].get("url")
            break
    if not caption_url:
        for lang in preferred_langs:
            if lang in autosubs and autosubs[lang]:
                caption_url = autosubs[lang][0].get("url")
                break
    
    if not caption_url:
        logger.warning(f"No VTT caption URL found for {video_info['video_id']}")
        return None
        
    try:
        response = requests.get(caption_url, timeout=30)
        response.raise_for_status()
        return vtt_to_text(response.text)
    except Exception as e:
        logger.error(f"Failed to download or parse VTT file for {video_info['video_id']}: {e}")
        return None

async def _get_transcript(video: Dict) -> Optional[str]:
    """Orchestrates fetching a transcript using a two-level fallback system with caching."""
    video_id = video.get("video_id")
    if not video_id:
        return None
    
    # Check cache first
    cached_transcript = get_from_cache("youtube", video_id)
    if cached_transcript:
        return cached_transcript
        
    # Attempt 1: Primary API
    transcript = await asyncio.to_thread(_fetch_transcript_from_api, video_id)
    if transcript:
        save_to_cache("youtube", video_id, transcript)
        return transcript

    # Attempt 2: VTT Fallback
    transcript = await asyncio.to_thread(_fetch_transcript_from_vtt, video)
    if transcript:
        save_to_cache("youtube", video_id, transcript)
        return transcript
        
    return None

# --- Main Module Function ---

async def fetch_and_analyze_youtube(topic: str):
    logger.info(f"[YouTube] Topic: {topic} | TopN={TOP_N_YOUTUBE_VIDEOS}")
    
    # Run sync search in an executor to avoid blocking async event loop
    videos = await asyncio.to_thread(_search_videos, topic, TOP_N_YOUTUBE_VIDEOS)
    
    source_evidence = []
    video_transcripts = []
    source_index = 0
    
    tasks = [_get_transcript(video) for video in videos]
    transcripts = await asyncio.gather(*tasks)

    for idx, transcript in enumerate(transcripts):
        video = videos[idx]
        title = video.get("title", "")
        logger.info(f"[YouTube] Processing video {idx + 1}/{len(videos)}: '{title}'")
        
        if transcript and transcript.strip():
            key_quote = transcript[:200].strip() + "..."
            
            source_evidence.append({
                "index": source_index,
                "source_type": "YouTube",
                "title": title,
                "author": video.get("author", "N/A"),
                "url": video.get("url", ""),
                "key_quote": key_quote
            })
            
            # Use finalize_text for consistent cleaning
            cleaned_transcript = finalize_text(transcript.splitlines())
            video_transcripts.append(f"[SOURCE {source_index}] {title} by {video.get('author', 'N/A')}\n{cleaned_transcript}")
            source_index += 1
        else:
            logger.warning(f"[YouTube] No transcript retrieved for video: {title}")

    if not video_transcripts:
        logger.warning(f"[YouTube] No episode transcripts found for topic: {topic}")
        out = {"search_topic": topic, "synthesized_opportunities": [], "source_evidence": []}
    else:
        corpus = "\n\n---\n\n".join(video_transcripts)
        chunks = chunk_text(corpus)
        prompt = _create_opportunities_prompt(len(source_evidence))
        llm_response = call_llm(prompt, chunks)
        synthesized_opportunities = _parse_opportunities_response(llm_response)
        out = {
            "search_topic": topic,
            "synthesized_opportunities": synthesized_opportunities,
            "source_evidence": source_evidence
        }
    
    out_path = Path("output") / f"{topic.replace(' ', '_')}_youtube.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    logger.info(f"[YouTube] Wrote {out_path} with {len(out['synthesized_opportunities'])} opportunities and {len(out['source_evidence'])} sources")