# ok_mvp/cache_utils.py
import json
import os
from pathlib import Path
from typing import Optional

from .logger import get_logger

logger = get_logger()


def get_from_cache(source: str, item_id: str) -> Optional[str]:
    """
    Retrieve cached content for a given source and item ID.
    
    Args:
        source: The source type (e.g., 'youtube', 'arxiv', 'podcast')
        item_id: The unique identifier for the item (e.g., video_id, arxiv_id, episode_uuid)
    
    Returns:
        The cached content as a string, or None if not found or error occurred
    """
    try:
        # Create cache directory structure
        cache_dir = Path("cache") / source
        cache_file = cache_dir / f"{item_id}.json"
        
        if not cache_file.exists():
            return None
            
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
            
        content = cached_data.get("content", "")
        if content:
            logger.info(f"[Cache] Using cached content for {source}/{item_id}")
            return content
        else:
            logger.warning(f"[Cache] Empty content in cache file for {source}/{item_id}")
            return None
            
    except Exception as e:
        logger.warning(f"[Cache] Failed to read cached content for {source}/{item_id}: {e}")
        return None


def save_to_cache(source: str, item_id: str, content: str) -> bool:
    """
    Save content to cache for a given source and item ID.
    
    Args:
        source: The source type (e.g., 'youtube', 'arxiv', 'podcast')
        item_id: The unique identifier for the item (e.g., video_id, arxiv_id, episode_uuid)
        content: The content to cache
    
    Returns:
        True if successfully saved, False otherwise
    """
    try:
        # Create cache directory structure
        cache_dir = Path("cache") / source
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        cache_file = cache_dir / f"{item_id}.json"
        
        # Prepare cache data
        cache_data = {
            "source": source,
            "item_id": item_id,
            "content": content,
            "cached_at": None  # Could add timestamp if needed
        }
        
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
            
        logger.info(f"[Cache] Successfully cached content for {source}/{item_id}")
        return True
        
    except Exception as e:
        logger.warning(f"[Cache] Failed to cache content for {source}/{item_id}: {e}")
        return False


def clear_cache(source: Optional[str] = None) -> bool:
    """
    Clear cache files. If source is specified, only clear that source's cache.
    
    Args:
        source: Optional source type to clear. If None, clears all cache.
    
    Returns:
        True if successfully cleared, False otherwise
    """
    try:
        cache_root = Path("cache")
        
        if source:
            cache_dir = cache_root / source
            if cache_dir.exists():
                import shutil
                shutil.rmtree(cache_dir)
                logger.info(f"[Cache] Cleared cache for source: {source}")
        else:
            if cache_root.exists():
                import shutil
                shutil.rmtree(cache_root)
                logger.info("[Cache] Cleared all cache")
                
        return True
        
    except Exception as e:
        logger.error(f"[Cache] Failed to clear cache: {e}")
        return False
