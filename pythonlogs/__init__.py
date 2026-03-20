import logging
from importlib.metadata import version
from pythonlogs.core.constants import LogLevel, RotateWhen
from pythonlogs.core.factory import BasicLog, SizeRotatingLog, TimedRotatingLog
from pythonlogs.core.settings import clear_settings_cache, get_log_settings

__all__ = (
    "BasicLog",
    "SizeRotatingLog",
    "TimedRotatingLog",
    "LogLevel",
    "RotateWhen",
    "clear_settings_cache",
    "get_log_settings",
)

__title__ = "pythonlogs"
__author__ = "Daniel Costa"
__email__ = "daniel@ddcsoftwares.com"
__license__ = "MIT"
__copyright__ = "Copyright 2024-present DDC Softwares"
__version__ = version(__title__)

logging.getLogger(__name__).addHandler(logging.NullHandler())
