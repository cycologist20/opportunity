# ok_mvp/podcast_module.py
import asyncio
from taddy import Taddy

# Assuming these utilities are in your project
from .cache_utils import get_from_cache, save_to_cache
from .logger import get_logger

logger = get_logger()

def _search_podcasts(api_key, query, max_results):
    logger.info(f"  [Podcast] Searching for top {max_results} episodes for query: '{query}'")
    taddy = Taddy(api_key)
    response = taddy.search_for_podcast_episodes(
        query=query, page=1, per_page=max_results, filter_for_transcripts=True
    )
    episodes = response.data.search_for_podcast_episodes.podcast_episodes
    logger.info(f"  [Podcast] Found {len(episodes)} episodes with transcripts.")
    return episodes

def _get_transcript(api_key, episode_uuid):
    cached = get_from_cache("podcast", episode_uuid)
    if cached: return cached
    
    taddy = Taddy(api_key)
    response = taddy.get_podcast_episode(uuid=episode_uuid)
    transcript_obj = response.data.get_podcast_episode.podcast_episode.transcript
    
    if transcript_obj:
        transcript = " ".join([line.text for line in transcript_obj])
        save_to_cache("podcast", episode_uuid, transcript)
        return transcript
    return None

async def research(search_terms: list[str], config: dict) -> tuple:
    print("  Calling Podcast Module...")
    api_key = config.get("TADDY_API_KEY")
    max_results = config.get("MAX_RESULTS_PER_SOURCE", 3)
    main_query = search_terms[0] if search_terms else ""
    if not api_key or not main_query:
        return [], []

    loop = asyncio.get_running_loop()
    episodes = await loop.run_in_executor(None, _search_podcasts, api_key, main_query, max_results)
    
    source_evidence, content_for_synthesis = [], []
    for episode in episodes:
        transcript = await loop.run_in_executor(None, _get_transcript, api_key, episode.uuid)
        if transcript:
            source_evidence.append({
                "index": -1, "source_type": "Podcast",
                "title": episode.title, "author": episode.podcast_series.name,
                "url": episode.share_url, "key_quote": "",
            })
            content_for_synthesis.append(transcript)
    return source_evidence, content_for_synthesis