import logging
from typing import Optional
from pythonLogs.log_utils import get_format, get_level, get_timezone_function
from pythonLogs.log_utils import cleanup_logger_handlers
from pythonLogs.memory_utils import register_logger_weakref
from pythonLogs.settings import get_log_settings
from pythonLogs.thread_safety import auto_thread_safe


@auto_thread_safe(['init', '_cleanup_logger'])
class BasicLog:
    """Basic logger with context manager support for automatic resource cleanup."""

    def __init__(
        self,
        level: Optional[str] = None,
        name: Optional[str] = None,
        encoding: Optional[str] = None,
        datefmt: Optional[str] = None,
        timezone: Optional[str] = None,
        showlocation: Optional[bool] = None,
    ):
        _settings = get_log_settings()
        self.level = get_level(level or _settings.level)
        self.appname = name or _settings.appname
        self.encoding = encoding or _settings.encoding
        self.datefmt = datefmt or _settings.date_format
        self.timezone = timezone or _settings.timezone
        self.showlocation = showlocation or _settings.show_location
        self.logger = None

    def init(self):
        logger = logging.getLogger(self.appname)
        logger.setLevel(self.level)
        logging.Formatter.converter = get_timezone_function(self.timezone)
        _format = get_format(self.showlocation, self.appname, self.timezone)

        # Only add handler if logger doesn't have any handlers
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(_format, datefmt=self.datefmt)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        self.logger = logger
        # Register weak reference for memory tracking
        register_logger_weakref(logger)
        return logger

    def __enter__(self):
        """Context manager entry."""
        if not hasattr(self, 'logger') or self.logger is None:
            self.init()
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        if hasattr(self, 'logger'):
            self._cleanup_logger(self.logger)

    def _cleanup_logger(self, logger: logging.Logger) -> None:
        """Clean up logger resources by closing all handlers with thread safety."""
        cleanup_logger_handlers(logger)

    @staticmethod
    def cleanup_logger(logger: logging.Logger) -> None:
        """Static method for cleaning up logger resources (backward compatibility)."""
        cleanup_logger_handlers(logger)
