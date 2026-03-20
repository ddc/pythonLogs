import atexit
import dataclasses
import logging
import threading
import time
from dataclasses import dataclass
from enum import StrEnum
from pythonlogs.basic_log import BasicLog as _BasicLogImpl
from pythonlogs.core.constants import LogLevel, RotateWhen
from pythonlogs.core.log_utils import cleanup_logger_handlers
from pythonlogs.core.settings import get_log_settings
from pythonlogs.size_rotating import SizeRotatingLog as _SizeRotatingLogImpl
from pythonlogs.timed_rotating import TimedRotatingLog as _TimedRotatingLogImpl


@dataclass
class LoggerConfig:
    """Configuration class to group logger parameters"""

    level: LogLevel | str | None = None
    name: str | None = None
    directory: str | None = None
    filenames: list | tuple | None = None
    encoding: str | None = None
    datefmt: str | None = None
    timezone: str | None = None
    streamhandler: bool | None = None
    showlocation: bool | None = None
    maxmbytes: int | None = None
    when: RotateWhen | str | None = None
    sufix: str | None = None
    rotateatutc: bool | None = None
    daystokeep: int | None = None


class LoggerType(StrEnum):
    """Available logger types"""

    BASIC = "basic"
    SIZE_ROTATING = "size_rotating"
    TIMED_ROTATING = "timed_rotating"


class LoggerFactory:
    """Factory for creating different types of loggers with optimized instantiation and memory management"""

    # Logger registry for reusing loggers by name with timestamp tracking
    _logger_registry: dict[str, tuple[logging.Logger, float]] = {}
    # Thread lock for registry access
    _registry_lock = threading.RLock()
    # Memory optimization settings
    _max_loggers = 100  # Maximum number of cached loggers
    _logger_ttl = 3600  # Logger TTL in seconds (1 hour)
    _initialized = False  # Flag to track if memory limits have been initialized
    _atexit_registered = False  # Flag to track if atexit cleanup is registered

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Ensure memory limits are initialized from settings on first use."""
        if not cls._initialized:
            settings = get_log_settings()
            cls._max_loggers = settings.max_loggers
            cls._logger_ttl = settings.logger_ttl_seconds
            cls._initialized = True

        # Register atexit cleanup on first use
        if not cls._atexit_registered:
            atexit.register(cls._atexit_cleanup)
            cls._atexit_registered = True

    @classmethod
    def get_or_create_logger(
        cls,
        logger_type: LoggerType | str,
        name: str | None = None,
        **kwargs,
    ) -> logging.Logger:
        """
        Get an existing logger from registry or create a new one.
        Loggers are cached by name for performance.

        Args:
            logger_type: Type of logger to create
            name: Logger name (used as cache key)
            **kwargs: Additional logger configuration

        Returns:
            Cached or newly created logger instance
        """
        # Use the default name if none provided
        if name is None:
            name = get_log_settings().appname

        # Thread-safe check-and-create operation
        with cls._registry_lock:
            # Initialize memory limits from settings on first use
            cls._ensure_initialized()

            # Clean up expired loggers first
            cls._cleanup_expired_loggers()

            # Check if logger already exists in the registry
            if name in cls._logger_registry:
                logger, _ = cls._logger_registry[name]
                # Update timestamp for LRU tracking
                cls._logger_registry[name] = (logger, time.time())
                return logger

            # Ensure registry size limit
            cls._enforce_size_limit()

            # Create a new logger and cache it with timestamp
            logger = cls.create_logger(logger_type, name=name, **kwargs)
            cls._logger_registry[name] = (logger, time.time())
            return logger

    @classmethod
    def clear_registry(cls) -> None:
        """Clear the logger registry with proper resource cleanup."""
        with cls._registry_lock:
            for logger, _ in cls._logger_registry.values():
                cls._cleanup_logger(logger)
            cls._logger_registry.clear()

    @classmethod
    def _cleanup_expired_loggers(cls) -> None:
        """Remove expired loggers from registry based on TTL."""
        current_time = time.time()
        expired_keys = []

        for name, (logger, timestamp) in cls._logger_registry.items():
            if current_time - timestamp > cls._logger_ttl:
                expired_keys.append(name)
                cls._cleanup_logger(logger)

        for key in expired_keys:
            cls._logger_registry.pop(key, None)

    @classmethod
    def _enforce_size_limit(cls) -> None:
        """Enforce maximum registry size by removing the oldest entries (LRU eviction)."""
        if cls._max_loggers <= 0:
            # Special case: if max_loggers is 0 or negative, clear all
            cls.clear_registry()
            return

        if len(cls._logger_registry) >= cls._max_loggers:
            # Sort by timestamp (oldest first) and remove the oldest entries
            sorted_entries = sorted(cls._logger_registry.items(), key=lambda x: x[1][1])
            entries_to_remove = len(sorted_entries) - cls._max_loggers + 1

            for i in range(min(entries_to_remove, len(sorted_entries))):
                name, (logger, _) = sorted_entries[i]
                cls._cleanup_logger(logger)
                cls._logger_registry.pop(name, None)

    @classmethod
    def set_memory_limits(cls, max_loggers: int = 100, ttl_seconds: int = 3600) -> None:
        """Configure memory management limits for the logger registry at runtime.

        Args:
            max_loggers: Maximum number of cached loggers
            ttl_seconds: Time-to-live for cached loggers in seconds
        """
        with cls._registry_lock:
            cls._max_loggers = max_loggers
            cls._logger_ttl = ttl_seconds
            cls._initialized = True  # Mark as manually configured
            # Clean up immediately with new settings
            cls._cleanup_expired_loggers()
            cls._enforce_size_limit()

    @classmethod
    def _atexit_cleanup(cls) -> None:
        """Cleanup function registered with atexit to ensure proper resource cleanup."""
        try:
            cls.clear_registry()
        except (OSError, ValueError, RuntimeError):
            # Silently ignore expected exceptions during shutdown cleanup
            pass

    @staticmethod
    def _cleanup_logger(logger: logging.Logger) -> None:
        """Clean up logger resources by closing all handlers."""
        cleanup_logger_handlers(logger)

    @classmethod
    def shutdown_logger(cls, name: str) -> bool:
        """Shutdown and remove a specific logger from registry.

        Args:
            name: Logger name to shut down

        Returns:
            True if logger was found and shutdown, False otherwise
        """
        with cls._registry_lock:
            if name in cls._logger_registry:
                logger, _ = cls._logger_registry.pop(name)
                cls._cleanup_logger(logger)
                return True
            return False

    @classmethod
    def get_registered_loggers(cls) -> dict[str, logging.Logger]:
        """Get all registered loggers. Returns a copy of the registry."""
        with cls._registry_lock:
            return {name: logger for name, (logger, _) in cls._logger_registry.items()}

    @classmethod
    def get_memory_limits(cls) -> dict[str, int]:
        """Get current memory management limits.

        Returns:
            Dictionary with current max_loggers and ttl_seconds settings
        """
        with cls._registry_lock:
            return {"max_loggers": cls._max_loggers, "ttl_seconds": cls._logger_ttl}

    # Mapping of logger types to their implementation classes and accepted fields
    _LOGGER_IMPL = {
        LoggerType.BASIC: (
            _BasicLogImpl,
            {"level", "name", "encoding", "datefmt", "timezone", "showlocation"},
        ),
        LoggerType.SIZE_ROTATING: (
            _SizeRotatingLogImpl,
            {
                "level",
                "name",
                "directory",
                "filenames",
                "maxmbytes",
                "daystokeep",
                "encoding",
                "datefmt",
                "timezone",
                "streamhandler",
                "showlocation",
            },
        ),
        LoggerType.TIMED_ROTATING: (
            _TimedRotatingLogImpl,
            {
                "level",
                "name",
                "directory",
                "filenames",
                "when",
                "sufix",
                "daystokeep",
                "encoding",
                "datefmt",
                "timezone",
                "streamhandler",
                "showlocation",
                "rotateatutc",
            },
        ),
    }

    @staticmethod
    def create_logger(logger_type: LoggerType | str, config: LoggerConfig | None = None, **kwargs) -> logging.Logger:
        """
        Factory method to create loggers based on type.

        Args:
            logger_type: Type of logger to create (LoggerType enum or string)
            config: LoggerConfig object with logger parameters
            **kwargs: Individual logger parameters (kwargs take precedence over config)

        Returns:
            Configured logger instance

        Raises:
            ValueError: If invalid logger_type is provided
        """
        # Convert string to enum if needed
        if isinstance(logger_type, str):
            try:
                logger_type = LoggerType(logger_type.lower())
            except ValueError as err:
                raise ValueError(
                    f"Invalid logger type: {logger_type}. Valid types: {[t.value for t in LoggerType]}"
                ) from err

        # Merge config and kwargs (kwargs take precedence)
        if config is None:
            config = LoggerConfig()
        merged = {f.name: kwargs.get(f.name, getattr(config, f.name)) for f in dataclasses.fields(LoggerConfig)}

        # Convert enum values to strings for logger classes
        if isinstance(merged.get("level"), LogLevel):
            merged["level"] = merged["level"].value
        if isinstance(merged.get("when"), RotateWhen):
            merged["when"] = merged["when"].value

        # Create logger using table-driven dispatch
        impl_class, valid_fields = LoggerFactory._LOGGER_IMPL[logger_type]
        logger_kwargs = {k: v for k, v in merged.items() if k in valid_fields}
        return impl_class(**logger_kwargs).init()


# Public API wrapper classes - act like logging.Logger with context manager support
class _LoggerMixin:
    """Mixin providing common logger wrapper functionality with context manager support."""

    _logger: logging.Logger

    def __getattr__(self, name: str):
        """Delegate attribute access to the underlying logger."""
        return getattr(self._logger, name)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        cleanup_logger_handlers(self._logger)
        return False


class BasicLog(_LoggerMixin):
    """Basic logger wrapper that acts like logging.Logger with context manager support.

    Usage:
        # Direct usage
        logger = BasicLog(name="app", level="INFO")
        logger.info("Hello world")

        # Context manager (automatic cleanup)
        with BasicLog(name="app", level="INFO") as logger:
            logger.info("Hello world")
    """

    def __init__(
        self,
        level: LogLevel | str | None = None,
        name: str | None = None,
        encoding: str | None = None,
        datefmt: str | None = None,
        timezone: str | None = None,
        showlocation: bool | None = None,
    ):
        self._logger = LoggerFactory.create_logger(
            LoggerType.BASIC,
            level=level,
            name=name,
            encoding=encoding,
            datefmt=datefmt,
            timezone=timezone,
            showlocation=showlocation,
        )
        self._name = name or get_log_settings().appname


class SizeRotatingLog(_LoggerMixin):
    """Size-based rotating logger wrapper that acts like logging.Logger with context manager support.

    Usage:
        # Direct usage
        logger = SizeRotatingLog(name="app", directory="/logs", filenames=["app.log"])
        logger.info("Hello world")

        # Context manager (automatic cleanup)
        with SizeRotatingLog(name="app", directory="/logs", filenames=["app.log"]) as logger:
            logger.info("Hello world")
    """

    def __init__(
        self,
        level: LogLevel | str | None = None,
        name: str | None = None,
        directory: str | None = None,
        filenames: list | tuple | None = None,
        maxmbytes: int | None = None,
        daystokeep: int | None = None,
        encoding: str | None = None,
        datefmt: str | None = None,
        timezone: str | None = None,
        streamhandler: bool | None = None,
        showlocation: bool | None = None,
    ):
        self._logger = LoggerFactory.create_logger(
            LoggerType.SIZE_ROTATING,
            level=level,
            name=name,
            directory=directory,
            filenames=filenames,
            maxmbytes=maxmbytes,
            daystokeep=daystokeep,
            encoding=encoding,
            datefmt=datefmt,
            timezone=timezone,
            streamhandler=streamhandler,
            showlocation=showlocation,
        )
        self._name = name or get_log_settings().appname


class TimedRotatingLog(_LoggerMixin):
    """Time-based rotating logger wrapper that acts like logging.Logger with context manager support.

    Usage:
        # Direct usage
        logger = TimedRotatingLog(name="app", directory="/logs", when="midnight")
        logger.info("Hello world")

        # Context manager (automatic cleanup)
        with TimedRotatingLog(name="app", directory="/logs", when="midnight") as logger:
            logger.info("Hello world")
    """

    def __init__(
        self,
        level: LogLevel | str | None = None,
        name: str | None = None,
        directory: str | None = None,
        filenames: list | tuple | None = None,
        when: RotateWhen | str | None = None,
        sufix: str | None = None,
        daystokeep: int | None = None,
        encoding: str | None = None,
        datefmt: str | None = None,
        timezone: str | None = None,
        streamhandler: bool | None = None,
        showlocation: bool | None = None,
        rotateatutc: bool | None = None,
    ):
        self._logger = LoggerFactory.create_logger(
            LoggerType.TIMED_ROTATING,
            level=level,
            name=name,
            directory=directory,
            filenames=filenames,
            when=when,
            sufix=sufix,
            daystokeep=daystokeep,
            encoding=encoding,
            datefmt=datefmt,
            timezone=timezone,
            streamhandler=streamhandler,
            showlocation=showlocation,
            rotateatutc=rotateatutc,
        )
        self._name = name or get_log_settings().appname


# Convenience functions
def clear_logger_registry() -> None:
    """Clear the logger registry with proper cleanup."""
    LoggerFactory.clear_registry()


def shutdown_logger(name: str) -> bool:
    """Shut down a specific logger."""
    return LoggerFactory.shutdown_logger(name)


def get_registered_loggers() -> dict[str, logging.Logger]:
    """Get all registered loggers."""
    return LoggerFactory.get_registered_loggers()
