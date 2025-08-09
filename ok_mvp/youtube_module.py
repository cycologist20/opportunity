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


def _search_videos(query: str, limit: int) -> List[Dict]:
    """Use yt-dlp to search YouTube without an API key."""
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
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
        url = e.get("webpage_url") or e.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid else "")
        out.append({"video_id": vid, "title": title, "link": url})
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
    logger.info(f"[YouTube] Topic: {topic} | TopN={TOP_N_YOUTUBE_VIDEOS}")
    results = _search_videos(topic, TOP_N_YOUTUBE_VIDEOS)

    videos = []
    corpus_parts = []

    for r in results:
        title = r.get("title", "")
        link = r.get("link", "")
        vid = r.get("video_id", "")
        transcript = _fetch_transcript_text(vid, link) if vid and link else ""
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
