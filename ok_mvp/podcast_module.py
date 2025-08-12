# ok_mvp/podcast_module.py
import asyncio
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

import aiohttp

from .logger import get_logger
from .config import (
    TOP_N_PODCAST_EPISODES,
    PODCAST_TRANSCRIPT_TIMEOUT,
)
from .llm_utils import call_llm, chunk_text

logger = get_logger()


def _create_opportunities_prompt(num_sources: int) -> str:
    return f"""Analyze the following podcast episode transcripts and identify actionable business opportunities.

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


class TaddyAPIClient:
    """Client for interacting with the Taddy Podcast GraphQL API."""

    def __init__(self):
        self.api_key = os.getenv("TADDY_API_KEY")
        self.user_id = os.getenv("TADDY_USER_ID")
        self.graphql_url = "https://api.taddy.org"
        if not self.api_key or not self.user_id:
            raise ValueError("TADDY_API_KEY and TADDY_USER_ID must be set")
        self.headers = {
            "Content-Type": "application/json",
            "X-USER-ID": self.user_id,
            "X-API-KEY": self.api_key,
        }

    async def _make_request(self, payload: Dict, timeout: int) -> Optional[Dict]:
        """Makes a single, robust GraphQL request."""
        async with aiohttp.ClientSession() as session:
            try:
                timeout_config = aiohttp.ClientTimeout(total=timeout)
                async with session.post(self.graphql_url, headers=self.headers, json=payload, timeout=timeout_config) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "errors" in data:
                            logger.error(f"[Podcast] GraphQL errors: {data['errors']}")
                            return None
                        return data.get("data", {})
                    else:
                        error_text = await response.text()
                        logger.error(f"[Podcast] API error {response.status}: {error_text}")
                        return None
            except Exception as e:
                logger.error(f"[Podcast] Request failed: {e}")
                return None

    async def search_episodes(self, query: str, limit: int) -> List[Dict[str, Any]]:
        graphql_query = """
        query Search($term: String!, $filterForTypes: [SearchContentType!], $limitPerPage: Int) {
          search(term: $term, filterForTypes: $filterForTypes, limitPerPage: $limitPerPage) {
            searchId
            podcastEpisodes {
              uuid
              name
              websiteUrl
              podcastSeries {
                uuid
                name
              }
            }
          }
        }
        """
        graphql_payload = {
            "query": graphql_query,
            "variables": {
                "term": query,
                "filterForTypes": ["PODCASTEPISODE"],
                "limitPerPage": limit,
            }
        }
        data = await self._make_request(graphql_payload, timeout=60)
        if data:
            episodes = data.get("search", {}).get("podcastEpisodes", [])
            logger.info(f"[Podcast] Found {len(episodes)} episodes for query: {query}")
            return episodes
        return []

    async def get_episode_transcript(self, episode_uuid: str) -> Optional[str]:
        # Create cache directory if it doesn't exist
        cache_dir = Path("cache/transcripts")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Check cache first
        cache_file = cache_dir / f"{episode_uuid}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                cached_transcript = cached_data.get("transcript", "")
                if cached_transcript:
                    logger.info(f"[Podcast] Using cached transcript for {episode_uuid}")
                    return cached_transcript
            except Exception as e:
                logger.warning(f"[Podcast] Failed to read cached transcript for {episode_uuid}: {e}")
        
        # Cache miss - fetch from API
        graphql_query = """
        query GetEpisodeTranscript($uuid: ID!, $useOnDemand: Boolean) {
          getEpisodeTranscript(uuid: $uuid, useOnDemandCreditsIfNeeded: $useOnDemand) {
            id
            text
          }
        }
        """
        graphql_payload = {
            "query": graphql_query,
            "variables": {
                "uuid": episode_uuid,
                "useOnDemand": True
            }
        }
        logger.info(f"[Podcast] Requesting transcript for {episode_uuid} (on-demand if needed)...")
        data = await self._make_request(graphql_payload, timeout=PODCAST_TRANSCRIPT_TIMEOUT)
        if data:
            transcript_items = data.get("getEpisodeTranscript", [])
            if transcript_items:
                full_text = " ".join(item.get("text", "") for item in transcript_items)
                
                # Save to cache
                try:
                    cache_data = {
                        "episode_uuid": episode_uuid,
                        "transcript": full_text,
                        "cached_at": None  # Could add timestamp if needed
                    }
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(cache_data, f, indent=2)
                    logger.info(f"[Podcast] Successfully retrieved and cached transcript for {episode_uuid}")
                except Exception as e:
                    logger.warning(f"[Podcast] Failed to cache transcript for {episode_uuid}: {e}")
                
                return full_text
        
        logger.warning(f"[Podcast] No transcript available for episode: {episode_uuid}")
        return None


async def fetch_and_analyze_podcasts(topic: str):
    logger.info(f"[Podcast] Topic: {topic} | TopN={TOP_N_PODCAST_EPISODES}")
    try:
        client = TaddyAPIClient()
    except ValueError as e:
        logger.error(f"[Podcast] API client initialization failed: {e}")
        return

    episodes = await client.search_episodes(topic, TOP_N_PODCAST_EPISODES)
    
    source_evidence = []
    episode_transcripts = []
    source_index = 0
    
    for idx, episode in enumerate(episodes):
        title = episode.get("name", "")
        show_name = episode.get("podcastSeries", {}).get("name", "")
        episode_url = episode.get("websiteUrl", "") # Corrected field
        episode_uuid = episode.get("uuid", "")
        
        logger.info(f"[Podcast] Processing episode {idx + 1}/{len(episodes)}: '{title}'")
        if not episode_uuid: continue
        
        transcript = await client.get_episode_transcript(episode_uuid)
        
        if transcript and transcript.strip():
            key_quote = transcript[:200].strip() + "..."
            
            source_evidence.append({
                "index": source_index,
                "source_type": "Podcast",
                "title": title,
                "author": show_name,
                "url": episode_url,
                "key_quote": key_quote
            })
            
            episode_transcripts.append(f"[SOURCE {source_index}] {title} from {show_name}\n{transcript}")
            source_index += 1
    
    if not episode_transcripts:
        logger.warning(f"[Podcast] No episode transcripts found for topic: {topic}")
        out = {"search_topic": topic, "synthesized_opportunities": [], "source_evidence": []}
    else:
        corpus = "\n\n---\n\n".join(episode_transcripts)
        chunks = chunk_text(corpus)
        prompt = _create_opportunities_prompt(len(source_evidence))
        llm_response = call_llm(prompt, chunks)
        synthesized_opportunities = _parse_opportunities_response(llm_response)
        out = {
            "search_topic": topic,
            "synthesized_opportunities": synthesized_opportunities,
            "source_evidence": source_evidence
        }
    
    out_path = Path("output") / f"{topic.replace(' ', '_')}_podcast.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    logger.info(f"[Podcast] Wrote {out_path} with {len(out['synthesized_opportunities'])} opportunities and {len(out['source_evidence'])} sources")