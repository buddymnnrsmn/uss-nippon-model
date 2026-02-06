"""
Cache Persistence Module
=========================

Provides disk-based persistence for cached dashboard calculations.
Allows cached results to survive browser refresh and application restarts.
"""

import json
import pickle
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Optional


# Cache directory
CACHE_DIR = Path("./cache")
CACHE_DIR.mkdir(exist_ok=True)


def save_calculation_cache(key: str, data: Any, scenario_hash: str):
    """
    Save calculation results to disk.

    Args:
        key: Cache key (e.g., 'calc_scenario_comparison')
        data: Data to cache (will be pickled)
        scenario_hash: Hash of current scenario parameters
    """
    cache_file = CACHE_DIR / f"{key}_{scenario_hash}.pkl"
    metadata_file = CACHE_DIR / f"{key}_{scenario_hash}.json"

    # Save data as pickle
    with open(cache_file, 'wb') as f:
        pickle.dump(data, f)

    # Save metadata as JSON
    metadata = {
        'key': key,
        'scenario_hash': scenario_hash,
        'timestamp': datetime.now().isoformat(),
        'size_bytes': cache_file.stat().st_size
    }
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)


def load_calculation_cache(key: str, scenario_hash: str) -> Optional[Any]:
    """
    Load calculation results from disk.

    Args:
        key: Cache key (e.g., 'calc_scenario_comparison')
        scenario_hash: Hash of current scenario parameters

    Returns:
        Cached data if exists, None otherwise
    """
    cache_file = CACHE_DIR / f"{key}_{scenario_hash}.pkl"

    if cache_file.exists():
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except (pickle.PickleError, EOFError, FileNotFoundError):
            # Cache file corrupted, return None
            return None
    return None


def clear_old_caches(scenario_hash: str):
    """
    Clear cache files that don't match current scenario.

    Args:
        scenario_hash: Hash of current scenario parameters
    """
    for cache_file in CACHE_DIR.glob("*.pkl"):
        if scenario_hash not in cache_file.name:
            cache_file.unlink()
            # Also delete corresponding metadata
            metadata_file = cache_file.with_suffix('.json')
            if metadata_file.exists():
                metadata_file.unlink()


def get_cache_info(key: str, scenario_hash: str) -> Optional[dict]:
    """
    Get metadata about cached calculation.

    Args:
        key: Cache key
        scenario_hash: Hash of current scenario parameters

    Returns:
        Metadata dict if exists, None otherwise
    """
    metadata_file = CACHE_DIR / f"{key}_{scenario_hash}.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None
    return None


def clear_all_caches():
    """Clear all cache files."""
    for cache_file in CACHE_DIR.glob("*.pkl"):
        cache_file.unlink()
    for metadata_file in CACHE_DIR.glob("*.json"):
        metadata_file.unlink()


def get_cache_size() -> int:
    """
    Get total size of all cache files in bytes.

    Returns:
        Total cache size in bytes
    """
    total_size = 0
    for cache_file in CACHE_DIR.glob("*.pkl"):
        total_size += cache_file.stat().st_size
    return total_size


def list_caches() -> list:
    """
    List all cached items.

    Returns:
        List of dicts with cache metadata
    """
    caches = []
    for metadata_file in CACHE_DIR.glob("*.json"):
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                caches.append(metadata)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return caches
