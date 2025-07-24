#!/usr/bin/env python3
"""Utility functions for tests across different platforms."""
import pytest
import functools


def skip_if_no_zoneinfo_utc():
    """Skip test if zoneinfo or UTC timezone data is not available (common on Windows)."""
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo("UTC")  # Test if UTC is available
    except Exception:
        pytest.skip("zoneinfo not available or UTC timezone data missing on this system")


def get_safe_timezone():
    """Get a timezone that works on all platforms."""
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo("UTC")  # Test if UTC is available
        return "UTC"
    except Exception:
        return "localtime"  # Fallback to localtime which should always work


def requires_zoneinfo_utc(func):
    """Decorator to skip tests that require zoneinfo UTC support."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        skip_if_no_zoneinfo_utc()
        return func(*args, **kwargs)
    return wrapper


def requires_zoneinfo(timezone):
    """Decorator to skip tests that require a specific timezone."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from zoneinfo import ZoneInfo
                ZoneInfo(timezone)  # Test if timezone is available
            except Exception:
                pytest.skip(f"Timezone '{timezone}' not available on this system")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def patch_logger_kwargs_with_safe_timezone(kwargs):
    """Patch logger kwargs to use safe timezone if UTC is specified but not available."""
    if kwargs.get('timezone') == 'UTC':
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo("UTC")  # Test if UTC is available
        except Exception:
            kwargs['timezone'] = 'localtime'  # Fall back to localtime
    return kwargs