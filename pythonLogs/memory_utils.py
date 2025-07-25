import logging
import threading
import weakref
from functools import lru_cache
from typing import Any, Dict, Optional, Set

from . import log_utils
from .log_utils import cleanup_logger_handlers



# Formatter cache to reduce memory usage for identical formatters
_formatter_cache: Dict[str, logging.Formatter] = {}
_formatter_cache_lock = threading.Lock()
_max_formatters = 50  # Limit formatter cache size


def get_cached_formatter(format_string: str, datefmt: Optional[str] = None) -> logging.Formatter:
    """Get a cached formatter or create and cache a new one.

    This reduces memory usage by reusing formatter instances with
    identical configuration instead of creating new ones each time.

    Args:
        format_string: The format string for the formatter
        datefmt: Optional date format string

    Returns:
        Cached or newly created formatter instance
    """
    # Create cache key from configuration
    cache_key = f"{format_string}|{datefmt or ''}"

    with _formatter_cache_lock:
        # Return existing formatter if cached
        if cache_key in _formatter_cache:
            return _formatter_cache[cache_key]

        # Enforce cache size limit
        if len(_formatter_cache) >= _max_formatters:
            # Remove the oldest entry (FIFO eviction)
            oldest_key = next(iter(_formatter_cache))
            _formatter_cache.pop(oldest_key)

        # Create and cache new formatter
        formatter = logging.Formatter(fmt=format_string, datefmt=datefmt)
        _formatter_cache[cache_key] = formatter
        return formatter


def clear_formatter_cache() -> None:
    """Clear the formatter cache to free memory."""
    with _formatter_cache_lock:
        _formatter_cache.clear()


# Directory cache utilities with memory management
def set_directory_cache_limit(max_directories: int) -> None:
    """Set the maximum number of directories to cache.

    Args:
        max_directories: Maximum number of directories to keep in cache
    """
    log_utils.set_directory_cache_limit(max_directories)


def clear_directory_cache() -> None:
    """Clear the directory cache to free memory."""
    log_utils.clear_directory_cache()


# Weak reference registry for tracking active loggers without preventing GC
_active_loggers: Set[weakref.ReferenceType] = set()
_weak_ref_lock = threading.Lock()


def register_logger_weakref(logger: logging.Logger) -> None:
    """Register a weak reference to a logger for memory tracking.

    This allows monitoring active loggers without preventing garbage collection.

    Args:
        logger: Logger to track
    """
    global _active_loggers

    def cleanup_callback(ref):
        with _weak_ref_lock:
            _active_loggers.discard(ref)

    with _weak_ref_lock:
        weak_ref = weakref.ref(logger, cleanup_callback)
        _active_loggers.add(weak_ref)


def get_active_logger_count() -> int:
    """Get the count of currently active loggers.

    Returns:
        Number of active logger instances
    """
    global _active_loggers
    with _weak_ref_lock:
        # Clean up dead references
        dead_refs = {ref for ref in _active_loggers if ref() is None}
        _active_loggers -= dead_refs
        return len(_active_loggers)


def get_memory_stats() -> Dict[str, Any]:
    """Get memory usage statistics for the logging system.

    Returns:
        Dictionary containing memory usage statistics
    """
    from . import factory
    
    # Get registry stats using public API
    registered_loggers = factory.LoggerFactory.get_registered_loggers()
    registry_size = len(registered_loggers)
    
    # Get memory limits using public API
    factory_limits = factory.LoggerFactory.get_memory_limits()

    with _formatter_cache_lock:
        formatter_cache_size = len(_formatter_cache)

    # Get directory cache stats using public API
    directory_stats = log_utils.get_directory_cache_stats()

    return {
        'registry_size': registry_size,
        'formatter_cache_size': formatter_cache_size,
        'directory_cache_size': directory_stats['cached_directories'],
        'active_logger_count': get_active_logger_count(),
        'max_registry_size': factory_limits['max_loggers'],
        'max_formatter_cache': _max_formatters,
        'max_directory_cache': directory_stats['max_directories'],
    }


# LRU cache size optimization
def optimize_lru_cache_sizes() -> None:
    """Optimize LRU cache sizes based on typical usage patterns."""
    # Clear existing caches and reduce their sizes
    
    # Clear and recreate timezone function cache with smaller size
    log_utils.get_timezone_function.cache_clear()
    log_utils.get_timezone_function = lru_cache(maxsize=8)(log_utils.get_timezone_function.__wrapped__)

    # Clear and recreate timezone offset cache with smaller size
    log_utils.get_timezone_offset.cache_clear()
    log_utils.get_timezone_offset = lru_cache(maxsize=8)(log_utils.get_timezone_offset.__wrapped__)

    # Clear and recreate stderr timezone cache with smaller size
    log_utils.get_stderr_timezone.cache_clear()
    log_utils.get_stderr_timezone = lru_cache(maxsize=4)(log_utils.get_stderr_timezone.__wrapped__)


def force_garbage_collection() -> Dict[str, int]:
    """Force garbage collection and return collection statistics.

    This can be useful for testing memory leaks or forcing cleanup
    in long-running applications.

    Returns:
        Dictionary with garbage collection statistics
    """
    import gc

    # Clear all our caches first using public APIs
    clear_formatter_cache()
    clear_directory_cache()

    # Force garbage collection
    collected = gc.collect()

    return {
        'objects_collected': collected,
        'garbage_count': len(gc.garbage),
        'reference_cycles': gc.get_count(),
    }
