# ok_mvp/youtube_module.py
import json
from pathlib import Path
from typing import List, Dict

from yt_dlp import YoutubeDL
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
from .logger import get_logger
from .config import TOP_N_YOUTUBE_VIDEOS
from .llm_utils import chunk_text, call_llm

logger = get_logger()


def _search_videos(query: str, limit: int) -> List[Dict]:
    """Use yt-dlp to search YouTube without an API key."""
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "noplaylist": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        # ytsearchN: returns up to N search results
        search_query = f"ytsearch{limit}:{query}"
        info = ydl.extract_info(search_query, download=False)
    entries = info.get("entries", []) if isinstance(info, dict) else []
    out = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        vid = e.get("id") or ""
        title = e.get("title") or ""
        url = (
            e.get("webpage_url")
            or e.get("url")
            or (f"https://www.youtube.com/watch?v={vid}" if vid else "")
        )
        out.append({"video_id": vid, "title": title, "link": url})
    return out


def _fetch_transcript_text(video_id: str) -> str:
    """Fetch transcript text using a direct call (compatible across versions)."""
    try:
        # Try English first; API will fallback to auto-generated if available
        lines = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        return " ".join(chunk.get("text", "") for chunk in lines)
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        logger.warning(f"Transcript unavailable for {video_id}: {e}")
        return ""
    except Exception as e:
        logger.warning(f"Transcript error for {video_id}: {e}")
        return ""


def fetch_and_analyze_youtube(topic: str):
    logger.info(f"[YouTube] Topic: {topic} | TopN={TOP_N_YOUTUBE_VIDEOS}")
    results = _search_videos(topic, TOP_N_YOUTUBE_VIDEOS)
    videos = []
    corpus_parts = []

    for r in results:
        title = r.get("title", "")
        link = r.get("link", "")
        vid = r.get("video_id", "")
        transcript = _fetch_transcript_text(vid) if vid else ""
        if transcript:
            corpus_parts.append(transcript)
        videos.append(
            {
                "title": title,
                "link": link,
                "video_id": vid,
                "has_transcript": bool(transcript),
                "transcript_chars": len(transcript) if transcript else 0,
            }
        )

    corpus = "\n\n".join(corpus_parts)
    chunks = chunk_text(corpus)
    prompt = (
        "Summarize the core insights, trends, and actionable opportunities from these "
        "YouTube transcripts. Output concise bullet points suitable for an Opportunity Brief."
    )
    summary = call_llm(prompt, chunks)

    out = {
        "topic": topic,
        "source": "youtube",
        "top_n": TOP_N_YOUTUBE_VIDEOS,
        "videos": videos,
        "summary": summary,
    }
    out_path = Path("output") / f"{topic.replace(' ', '_')}_youtube.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    logger.info(f"[YouTube] Wrote {out_path}")
