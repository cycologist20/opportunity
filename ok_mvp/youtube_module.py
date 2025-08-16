# ok_mvp/youtube_module.py
import asyncio
import requests
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

# Assuming these utilities are in your project
from .text_utils import vtt_to_text, finalize_text
from .cache_utils import get_from_cache, save_to_cache
from .logger import get_logger

logger = get_logger()

def _search_videos(query, limit):
    logger.info(f"  [YouTube] Searching for top {limit} videos for query: '{query}'")
    with YoutubeDL({"quiet": True, "skip_download": True, "extract_flat": False, "noplaylist": True}) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
    entries = info.get("entries", []) if isinstance(info, dict) else []
    out = [{"video_id": e.get("id", ""), "title": e.get("title", e.get("id", "")),
            "author": e.get("uploader") or e.get("channel") or "N/A",
            "url": e.get("webpage_url") or f"https://www.youtube.com/watch?v={e.get('id', '')}",
            "raw_info": e} for e in entries if isinstance(e, dict)]
    logger.info(f"  [YouTube] Found {len(out)} videos.")
    return out

def _fetch_transcript_from_api(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        return " ".join(d['text'] for d in transcript.fetch())
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return None
    except Exception as e:
        logger.error(f"  An unexpected error occurred with Transcript API for {video_id}: {e}")
        return None

def _fetch_transcript_from_vtt(video_info):
    subs = video_info['raw_info'].get("subtitles", {}) or {}
    autosubs = video_info['raw_info'].get("automatic_captions", {}) or {}
    caption_url = None
    for lang in ['en', 'en-US', 'en-GB']:
        for sub_type in (subs, autosubs):
            if lang in sub_type and sub_type[lang] and sub_type[lang][0].get("url"):
                caption_url = sub_type[lang][0]["url"]
                break
        if caption_url: break
    if not caption_url: return None
    try:
        return vtt_to_text(requests.get(caption_url, timeout=30).text)
    except Exception:
        return None

async def _get_transcript(video):
    video_id = video.get("video_id")
    if not video_id: return None
    await asyncio.sleep(1)
    cached = get_from_cache("youtube", video_id)
    if cached: return cached
    
    transcript = await asyncio.to_thread(_fetch_transcript_from_api, video_id)
    if not transcript:
        transcript = await asyncio.to_thread(_fetch_transcript_from_vtt, video)
    
    if transcript:
        save_to_cache("youtube", video_id, transcript)
        return transcript
    return None

async def research(search_terms: list[str], config: dict) -> tuple:
    print("  Calling YouTube Module...")
    max_results = config.get("MAX_RESULTS_PER_SOURCE", 3)
    main_query = search_terms[0] if search_terms else ""
    if not main_query: return [], []

    videos = await asyncio.to_thread(_search_videos, main_query, max_results)
    
    source_evidence, content_for_synthesis = [], []
    transcripts = await asyncio.gather(*[_get_transcript(video) for video in videos])

    for idx, transcript in enumerate(transcripts):
        if transcript and transcript.strip():
            video = videos[idx]
            source_evidence.append({
                "index": -1, "source_type": "YouTube", "title": video.get("title", ""),
                "author": video.get("author", "N/A"), "url": video.get("url", ""),
                "key_quote": "",
            })
            content_for_synthesis.append(finalize_text(transcript.splitlines()))
    return source_evidence, content_for_synthesis