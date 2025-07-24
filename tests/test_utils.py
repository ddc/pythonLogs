#!/usr/bin/env python3
"""Utility functions for tests across different platforms."""
import pytest


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
    def wrapper(*args, **kwargs):
        skip_if_no_zoneinfo_utc()
        return func(*args, **kwargs)
    return wrapper