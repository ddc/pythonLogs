import logging
from importlib.metadata import version
from typing import Literal, NamedTuple
from pythonLogs.basic_log import BasicLog
from pythonLogs.constants import LogLevel, RotateWhen
from pythonLogs.factory import (
    basic_logger,
    clear_logger_registry,
    create_logger,
    get_or_create_logger,
    get_registered_loggers,
    LoggerFactory,
    LoggerType,
    shutdown_logger,
    size_rotating_logger,
    timed_rotating_logger,
)
from pythonLogs.memory_utils import (
    clear_directory_cache,
    clear_formatter_cache,
    force_garbage_collection,
    get_memory_stats,
    optimize_lru_cache_sizes,
    set_directory_cache_limit,
)
from pythonLogs.size_rotating import SizeRotatingLog
from pythonLogs.timed_rotating import TimedRotatingLog


__all__ = (
    "BasicLog",
    "TimedRotatingLog",
    "SizeRotatingLog",
    "LoggerFactory",
    "LoggerType",
    "LogLevel",
    "RotateWhen",
    "create_logger",
    "get_or_create_logger",
    "basic_logger",
    "size_rotating_logger",
    "timed_rotating_logger",
    "clear_logger_registry",
    "get_registered_loggers",
    "shutdown_logger",
    # Memory management utilities
    "get_memory_stats",
    "clear_formatter_cache",
    "clear_directory_cache",
    "force_garbage_collection",
    "optimize_lru_cache_sizes",
    "set_directory_cache_limit",
)

__title__ = "pythonLogs"
__author__ = "Daniel Costa"
__email__ = "danieldcsta@gmail.com>"
__license__ = "MIT"
__copyright__ = "Copyright 2024-present ddc"
_req_python_version = (3, 12, 0)


try:
    _version = tuple(int(x) for x in version(__title__).split("."))
except ModuleNotFoundError:
    _version = (0, 0, 0)


class VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: Literal["alpha", "beta", "candidate", "final"]
    serial: int


__version__ = _version
__version_info__: VersionInfo = VersionInfo(
    major=__version__[0], minor=__version__[1], micro=__version__[2], releaselevel="final", serial=0
)
__req_python_version__: VersionInfo = VersionInfo(
    major=_req_python_version[0],
    minor=_req_python_version[1],
    micro=_req_python_version[2],
    releaselevel="final",
    serial=0,
)

logging.getLogger(__name__).addHandler(logging.NullHandler())

del logging, NamedTuple, Literal, VersionInfo, version, _version, _req_python_version
