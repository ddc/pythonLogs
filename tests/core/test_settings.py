"""Tests for settings module."""

import os
from pythonLogs.core.constants import (
    DEFAULT_BACKUP_COUNT,
    DEFAULT_DATE_FORMAT,
    DEFAULT_ENCODING,
    DEFAULT_ROTATE_SUFFIX,
    DEFAULT_TIMEZONE,
)
from pythonLogs.core.settings import (
    LogSettings,
    clear_settings_cache,
    get_log_settings,
)
from unittest.mock import patch


class TestLogSettings:
    """Test LogSettings class."""

    def test_default_values(self):
        """Test that LogSettings has correct default values when no env vars set."""
        # Save and clear any LOG_ environment variables to test true defaults
        saved_env = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("LOG_")}
        try:
            settings = LogSettings()

            assert settings.level.value == "INFO"
            assert settings.timezone == DEFAULT_TIMEZONE
            assert settings.encoding == DEFAULT_ENCODING
            assert settings.appname == "app"
            assert settings.filename == "app.log"
            assert settings.directory == "./logs"
            assert settings.days_to_keep == DEFAULT_BACKUP_COUNT
            assert settings.date_format == DEFAULT_DATE_FORMAT
            assert settings.stream_handler is True
            assert settings.show_location is False
            assert settings.max_loggers == 100
            assert settings.logger_ttl_seconds == 3600
            assert settings.max_file_size_mb == 10
            assert settings.rotate_when.value == "midnight"
            assert settings.rotate_at_utc is True
            assert settings.rotate_file_sufix == DEFAULT_ROTATE_SUFFIX
        finally:
            # Restore environment variables
            os.environ.update(saved_env)

    def test_env_prefix(self):
        """Test that settings use LOG_ prefix for environment variables."""
        with patch.dict(os.environ, {"LOG_APPNAME": "test_app", "LOG_TIMEZONE": "UTC"}):
            clear_settings_cache()
            settings = get_log_settings()

            assert settings.appname == "test_app"
            assert settings.timezone == "UTC"

        # Cleanup
        clear_settings_cache()

    def test_custom_values(self):
        """Test LogSettings with custom values."""
        from pythonLogs.core.constants import LogLevel

        settings = LogSettings(
            level=LogLevel.DEBUG,
            timezone="UTC",
            appname="custom_app",
            max_loggers=50,
        )

        assert settings.level == LogLevel.DEBUG
        assert settings.timezone == "UTC"
        assert settings.appname == "custom_app"
        assert settings.max_loggers == 50


class TestGetLogSettings:
    """Test get_log_settings function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_settings_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        clear_settings_cache()

    def test_returns_log_settings_instance(self):
        """Test that get_log_settings returns LogSettings instance."""
        settings = get_log_settings()
        assert isinstance(settings, LogSettings)

    def test_caches_settings(self):
        """Test that get_log_settings returns cached instance."""
        settings1 = get_log_settings()
        settings2 = get_log_settings()

        assert settings1 is settings2

    def test_cache_info(self):
        """Test that lru_cache is working."""
        # First call - cache miss
        get_log_settings()
        cache_info = get_log_settings.cache_info()
        assert cache_info.hits == 0
        assert cache_info.misses == 1

        # Second call - cache hit
        get_log_settings()
        cache_info = get_log_settings.cache_info()
        assert cache_info.hits == 1
        assert cache_info.misses == 1


class TestClearSettingsCache:
    """Test clear_settings_cache function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_settings_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        clear_settings_cache()

    def test_clears_cache(self):
        """Test that clear_settings_cache clears the lru_cache."""
        # Populate cache
        settings1 = get_log_settings()
        cache_info = get_log_settings.cache_info()
        assert cache_info.misses == 1

        # Clear cache
        clear_settings_cache()
        cache_info = get_log_settings.cache_info()
        assert cache_info.hits == 0
        assert cache_info.misses == 0

        # Get settings again - should be new instance
        settings2 = get_log_settings()
        cache_info = get_log_settings.cache_info()
        assert cache_info.misses == 1

        # Should be different instances after cache clear
        assert settings1 is not settings2

    def test_reloads_env_by_default(self):
        """Test that clear_settings_cache resets dotenv flag by default."""
        import pythonLogs.core.settings as settings_module

        # Ensure dotenv is loaded
        get_log_settings()
        assert settings_module._dotenv_loaded is True

        # Clear with reload_env=True (default)
        clear_settings_cache()
        assert settings_module._dotenv_loaded is False

    def test_keeps_env_when_reload_false(self):
        """Test that clear_settings_cache keeps dotenv flag when reload_env=False."""
        import pythonLogs.core.settings as settings_module

        # Ensure dotenv is loaded
        get_log_settings()
        assert settings_module._dotenv_loaded is True

        # Clear with reload_env=False
        clear_settings_cache(reload_env=False)
        assert settings_module._dotenv_loaded is True

    def test_new_settings_after_env_change(self):
        """Test that settings reflect env changes after cache clear."""
        # Get initial settings
        settings1 = get_log_settings()
        original_appname = settings1.appname

        # Change environment and clear cache
        with patch.dict(os.environ, {"LOG_APPNAME": "changed_app"}):
            clear_settings_cache()
            settings2 = get_log_settings()

            assert settings2.appname == "changed_app"
            assert settings2.appname != original_appname

        # Cleanup
        clear_settings_cache()


class TestPublicExports:
    """Test that clear_settings_cache is exported from main module."""

    def test_import_from_main_module(self):
        """Test that clear_settings_cache can be imported from pythonLogs."""
        from pythonLogs import clear_settings_cache as exported_func
        from pythonLogs.core.settings import clear_settings_cache as original_func

        assert exported_func is original_func

    def test_in_all(self):
        """Test that clear_settings_cache is in __all__."""
        import pythonLogs

        assert "clear_settings_cache" in pythonLogs.__all__
