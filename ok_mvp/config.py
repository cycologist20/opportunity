# ok_mvp/config.py
import os

# ------------ General ------------
# Default LLM model (OpenAI Chat Completions API name)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ------------ YouTube ------------
TOP_N_YOUTUBE_VIDEOS = int(os.getenv("TOP_N_YOUTUBE_VIDEOS", "5"))

# ------------ arXiv --------------
TOP_N_ARXIV_PAPERS = int(os.getenv("TOP_N_ARXIV_PAPERS", "5"))

# ------------ Podcast ------------
TOP_N_PODCAST_EPISODES = int(os.getenv("TOP_N_PODCAST_EPISODES", "5"))
PODCAST_TRANSCRIPT_POLL_INTERVAL = int(os.getenv("PODCAST_TRANSCRIPT_POLL_INTERVAL", "30"))  # seconds
PODCAST_TRANSCRIPT_TIMEOUT = int(os.getenv("PODCAST_TRANSCRIPT_TIMEOUT", "600"))  # 10 minutes

# ------------ Chunking / Limits ---
# We estimate ~4 chars per token; add a safety margin. These limits keep us far below 128k tokens.
# Max characters per chunk we send to the LLM in one message (map step).
CHUNK_MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", str(120_000)))  # ~30k tokens

# Hard cap on total corpus characters to summarize (prevents extreme inputs).
CORPUS_HARD_CAP_CHARS = int(os.getenv("CORPUS_HARD_CAP_CHARS", str(600_000)))  # ~150k tokens

# When we do map-reduce, we cap how many intermediate summaries we join for the reduce step.
MAX_MAP_SUMMARIES_FOR_REDUCE = int(os.getenv("MAX_MAP_SUMMARIES_FOR_REDUCE", "30"))

# Tokens allocation hints (not enforced, but used to size prompts)
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1500"))  # target output per call
