# ok_mvp/youtube_module.py
"""
This module handles all interactions with YouTube. It finds relevant
videos based on search terms and extracts their transcripts using yt-dlp
and a two-level fallback system.
"""
import asyncio
import requests
from yt_dlp import YoutubeDL
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

# Assuming these utilities exist from your original structure.
# If not, we will need to define them.
from .text_utils import vtt_to_text, finalize_text
from .cache_utils import get_from_cache, save_to_cache
from .logger import get_logger

logger = get_logger()

# --- Core YouTube Logic (Preserved from your original script) ---

def _search_videos(query, limit):
    """Use yt-dlp to search YouTube and get video metadata."""
    logger.info(f"  [YouTube] Searching for top {limit} videos for query: '{query}'")
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
            "author": e.get("uploader") or e.get("channel") or "N/A",
            "url": e.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
            "raw_info": e # Keep raw info for fallback
        })
    logger.info(f"  [YouTube] Found {len(out)} videos.")
    return out

def _fetch_transcript_from_api(video_id):
    """Primary Method: Use youtube-transcript-api with a robust two-step fetch."""
    try:
        # Step 1: Find the English transcript from the list of available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        
        # Step 2: Fetch the content of that transcript
        transcript_data = transcript.fetch()
        
        # Combine the text segments
        text = " ".join([d['text'] for d in transcript_data])
        return text
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        # This is an expected failure when no transcript exists
        return None
    except Exception as e:
        logger.error(f"  An unexpected error occurred with Transcript API for {video_id}: {e}")
        return None

def _fetch_transcript_from_vtt(video_info):
    """Fallback Method: Parse VTT caption files."""
    subs = video_info['raw_info'].get("subtitles") or {}
    autosubs = video_info['raw_info'].get("automatic_captions") or {}
    
    caption_url = None
    for lang in ['en', 'en-US', 'en-GB']:
        if lang in subs and subs[lang] and subs[lang][0].get("url"):
            caption_url = subs[lang][0]["url"]
            break
    if not caption_url:
        for lang in ['en', 'en-US', 'en-GB']:
            if lang in autosubs and autosubs[lang] and autosubs[lang][0].get("url"):
                caption_url = autosubs[lang][0]["url"]
                break
    
    if not caption_url:
        return None
        
    try:
        response = requests.get(caption_url, timeout=30)
        response.raise_for_status()
        return vtt_to_text(response.text)
    except Exception as e:
        logger.error(f"  Failed to download/parse VTT for {video_info['video_id']}: {e}")
        return None

async def _get_transcript(video):
    """Orchestrates fetching a transcript with caching and fallbacks."""
    video_id = video.get("video_id")
    if not video_id: return None
    
    cached = get_from_cache("youtube", video_id)
    if cached: return cached
        
    transcript = await asyncio.to_thread(_fetch_transcript_from_api, video_id)
    if not transcript:
        transcript = await asyncio.to_thread(_fetch_transcript_from_vtt, video)
    
    if transcript:
        save_to_cache("youtube", video_id, transcript)
        return transcript
        
    return None

# --- NEW ORCHESTRATOR FUNCTION ---

async def research(search_terms: list[str], config: dict) -> tuple:
    """
    The main entry point for the orchestrator.
    It performs the research and returns the data in the required format.
    """
    max_results = config.get("MAX_RESULTS_PER_SOURCE", 3)
    main_query = search_terms[0] if search_terms else ""
    if not main_query:
        return [], []

    # Run sync search in an executor to avoid blocking the async event loop
    videos = await asyncio.to_thread(_search_videos, main_query, max_results)
    
    source_evidence = []
    content_for_synthesis = []
    
    tasks = [_get_transcript(video) for video in videos]
    transcripts = await asyncio.gather(*tasks)

    for idx, transcript in enumerate(transcripts):
        video = videos[idx]
        if transcript and transcript.strip():
            source_evidence.append({
                "index": -1, # To be re-indexed by orchestrator
                "source_type": "YouTube",
                "title": video.get("title", ""),
                "author": video.get("author", "N/A"),
                "url": video.get("url", ""),
                "key_quote": "" # To be populated by a later prompt
            })
            
            cleaned_transcript = finalize_text(transcript.splitlines())
            content_for_synthesis.append(cleaned_transcript)
        else:
            logger.warning(f"  [YouTube] No transcript retrieved for video: {video.get('title', '')}")

    return source_evidence, content_for_synthesis