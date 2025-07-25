import atexit
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple, Union
from pythonLogs.basic_log import BasicLog
from pythonLogs.constants import LogLevel, RotateWhen
from pythonLogs.log_utils import cleanup_logger_handlers
from pythonLogs.settings import get_log_settings
from pythonLogs.size_rotating import SizeRotatingLog
from pythonLogs.timed_rotating import TimedRotatingLog


@dataclass
class LoggerConfig:
    """Configuration class to group logger parameters"""

    level: Optional[Union[LogLevel, str]] = None
    name: Optional[str] = None
    directory: Optional[str] = None
    filenames: Optional[list | tuple] = None
    encoding: Optional[str] = None
    datefmt: Optional[str] = None
    timezone: Optional[str] = None
    streamhandler: Optional[bool] = None
    showlocation: Optional[bool] = None
    maxmbytes: Optional[int] = None
    when: Optional[Union[RotateWhen, str]] = None
    sufix: Optional[str] = None
    rotateatutc: Optional[bool] = None
    daystokeep: Optional[int] = None


class LoggerType(str, Enum):
    """Available logger types"""

    BASIC = "basic"
    SIZE_ROTATING = "size_rotating"
    TIMED_ROTATING = "timed_rotating"


class LoggerFactory:
    """Factory for creating different types of loggers with optimized instantiation and memory management"""

    # Logger registry for reusing loggers by name with timestamp tracking
    _logger_registry: Dict[str, Tuple[logging.Logger, float]] = {}
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
        logger_type: Union[LoggerType, str],
        name: Optional[str] = None,
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
        except Exception:
            # Silently ignore exceptions during shutdown cleanup
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
            return {
                'max_loggers': cls._max_loggers,
                'ttl_seconds': cls._logger_ttl
            }

    @staticmethod
    def create_logger(
        logger_type: Union[LoggerType, str], config: Optional[LoggerConfig] = None, **kwargs
    ) -> logging.Logger:
        """
        Factory method to create loggers based on type.

        Args:
            logger_type: Type of logger to create (LoggerType enum or string)
            config: LoggerConfig object with logger parameters
            **kwargs: Individual logger parameters (for backward compatibility)

        Returns:
            Configured logger instance

        Raises:
            ValueError: If invalid logger_type is provided
        """
        # Convert string to enum if needed
        if isinstance(logger_type, str):
            try:
                logger_type = LoggerType(logger_type.lower())
            except ValueError:
                raise ValueError(f"Invalid logger type: {logger_type}. Valid types: {[t.value for t in LoggerType]}")

        # Merge config and kwargs (kwargs take precedence for backward compatibility)
        if config is None:
            config = LoggerConfig()

        # Create a new config with kwargs overriding config values
        final_config = LoggerConfig(
            level=kwargs.get('level', config.level),
            name=kwargs.get('name', config.name),
            directory=kwargs.get('directory', config.directory),
            filenames=kwargs.get('filenames', config.filenames),
            encoding=kwargs.get('encoding', config.encoding),
            datefmt=kwargs.get('datefmt', config.datefmt),
            timezone=kwargs.get('timezone', config.timezone),
            streamhandler=kwargs.get('streamhandler', config.streamhandler),
            showlocation=kwargs.get('showlocation', config.showlocation),
            maxmbytes=kwargs.get('maxmbytes', config.maxmbytes),
            when=kwargs.get('when', config.when),
            sufix=kwargs.get('sufix', config.sufix),
            rotateatutc=kwargs.get('rotateatutc', config.rotateatutc),
            daystokeep=kwargs.get('daystokeep', config.daystokeep),
        )

        # Convert enum values to strings for logger classes
        level_str = final_config.level.value if isinstance(final_config.level, LogLevel) else final_config.level
        when_str = final_config.when.value if isinstance(final_config.when, RotateWhen) else final_config.when

        # Create logger based on type
        match logger_type:
            case LoggerType.BASIC:
                logger_instance = BasicLog(
                    level=level_str,
                    name=final_config.name,
                    encoding=final_config.encoding,
                    datefmt=final_config.datefmt,
                    timezone=final_config.timezone,
                    showlocation=final_config.showlocation,
                )

            case LoggerType.SIZE_ROTATING:
                logger_instance = SizeRotatingLog(
                    level=level_str,
                    name=final_config.name,
                    directory=final_config.directory,
                    filenames=final_config.filenames,
                    maxmbytes=final_config.maxmbytes,
                    daystokeep=final_config.daystokeep,
                    encoding=final_config.encoding,
                    datefmt=final_config.datefmt,
                    timezone=final_config.timezone,
                    streamhandler=final_config.streamhandler,
                    showlocation=final_config.showlocation,
                )

            case LoggerType.TIMED_ROTATING:
                logger_instance = TimedRotatingLog(
                    level=level_str,
                    name=final_config.name,
                    directory=final_config.directory,
                    filenames=final_config.filenames,
                    when=when_str,
                    sufix=final_config.sufix,
                    daystokeep=final_config.daystokeep,
                    encoding=final_config.encoding,
                    datefmt=final_config.datefmt,
                    timezone=final_config.timezone,
                    streamhandler=final_config.streamhandler,
                    showlocation=final_config.showlocation,
                    rotateatutc=final_config.rotateatutc,
                )

            case _:
                raise ValueError(f"Unsupported logger type: {logger_type}")

        return logger_instance.init()

    @staticmethod
    def create_basic_logger(
        level: Optional[Union[LogLevel, str]] = None,
        name: Optional[str] = None,
        encoding: Optional[str] = None,
        datefmt: Optional[str] = None,
        timezone: Optional[str] = None,
        showlocation: Optional[bool] = None,
    ) -> logging.Logger:
        """Convenience method for creating a basic logger"""
        return LoggerFactory.create_logger(
            LoggerType.BASIC,
            level=level,
            name=name,
            encoding=encoding,
            datefmt=datefmt,
            timezone=timezone,
            showlocation=showlocation,
        )

    @staticmethod
    def create_size_rotating_logger(
        level: Optional[Union[LogLevel, str]] = None,
        name: Optional[str] = None,
        directory: Optional[str] = None,
        filenames: Optional[list | tuple] = None,
        maxmbytes: Optional[int] = None,
        daystokeep: Optional[int] = None,
        encoding: Optional[str] = None,
        datefmt: Optional[str] = None,
        timezone: Optional[str] = None,
        streamhandler: Optional[bool] = None,
        showlocation: Optional[bool] = None,
    ) -> logging.Logger:
        """Convenience method for creating a size rotating logger"""
        return LoggerFactory.create_logger(
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

    @staticmethod
    def create_timed_rotating_logger(
        level: Optional[Union[LogLevel, str]] = None,
        name: Optional[str] = None,
        directory: Optional[str] = None,
        filenames: Optional[list | tuple] = None,
        when: Optional[Union[RotateWhen, str]] = None,
        sufix: Optional[str] = None,
        daystokeep: Optional[int] = None,
        encoding: Optional[str] = None,
        datefmt: Optional[str] = None,
        timezone: Optional[str] = None,
        streamhandler: Optional[bool] = None,
        showlocation: Optional[bool] = None,
        rotateatutc: Optional[bool] = None,
    ) -> logging.Logger:
        """Convenience method for creating a timed rotating logger"""
        return LoggerFactory.create_logger(
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


# Convenience functions for backward compatibility and easier usage
def create_logger(logger_type: Union[LoggerType, str], **kwargs) -> logging.Logger:
    """Convenience function to create a logger using the factory"""
    return LoggerFactory.create_logger(logger_type, **kwargs)


def get_or_create_logger(logger_type: Union[LoggerType, str], **kwargs) -> logging.Logger:
    """Convenience function to get cached or create a logger using the factory"""
    return LoggerFactory.get_or_create_logger(logger_type, **kwargs)


def basic_logger(**kwargs) -> logging.Logger:
    """Convenience function to create a basic logger"""
    return LoggerFactory.create_basic_logger(**kwargs)


def size_rotating_logger(**kwargs) -> logging.Logger:
    """Convenience function to create a size rotating logger"""
    return LoggerFactory.create_size_rotating_logger(**kwargs)


def timed_rotating_logger(**kwargs) -> logging.Logger:
    """Convenience function to create a timed rotating logger"""
    return LoggerFactory.create_timed_rotating_logger(**kwargs)


def clear_logger_registry() -> None:
    """Convenience function to clear the logger registry with proper cleanup"""
    LoggerFactory.clear_registry()


def shutdown_logger(name: str) -> bool:
    """Convenience function to shut down a specific logger"""
    return LoggerFactory.shutdown_logger(name)


def get_registered_loggers() -> dict[str, logging.Logger]:
    """Convenience function to get all registered loggers"""
    return LoggerFactory.get_registered_loggers()
