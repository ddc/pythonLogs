import logging
from importlib.metadata import version
from pythonLogs.core.constants import LogLevel, RotateWhen
from pythonLogs.core.factory import BasicLog, SizeRotatingLog, TimedRotatingLog
from pythonLogs.core.settings import clear_settings_cache, get_log_settings

__all__ = (
    "BasicLog",
    "SizeRotatingLog",
    "TimedRotatingLog",
    "LogLevel",
    "RotateWhen",
    "clear_settings_cache",
    "get_log_settings",
)

__title__ = "pythonLogs"
__author__ = "Daniel Costa"
__email__ = "ddcsoftwares@proton.me"
__license__ = "MIT"
__copyright__ = "Copyright 2024-present DDC Softwares"
__version__ = version(__title__)

logging.getLogger(__name__).addHandler(logging.NullHandler())
