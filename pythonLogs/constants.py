import logging
from enum import Enum

# File and Directory Constants
MB_TO_BYTES = 1024 * 1024
DEFAULT_FILE_MODE = 0o755
DEFAULT_BACKUP_COUNT = 30

# Date Format Constants
DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
DEFAULT_ROTATE_SUFFIX = "%Y%m%d"

# Encoding Constants
DEFAULT_ENCODING = "UTF-8"

# Timezone Constants
DEFAULT_TIMEZONE = "UTC"


class LogLevel(str, Enum):
    """Log levels"""

    CRITICAL = "CRITICAL"
    CRIT = "CRIT"
    ERROR = "ERROR"
    WARNING = "WARNING"
    WARN = "WARN"
    INFO = "INFO"
    DEBUG = "DEBUG"


class RotateWhen(str, Enum):
    """Rotation timing options for TimedRotatingLog"""

    MIDNIGHT = "midnight"
    MONDAY = "W0"
    TUESDAY = "W1"
    WEDNESDAY = "W2"
    THURSDAY = "W3"
    FRIDAY = "W4"
    SATURDAY = "W5"
    SUNDAY = "W6"
    HOURLY = "H"
    DAILY = "D"


# Level mapping for performance optimization
LEVEL_MAP = {
    LogLevel.DEBUG.value.lower(): logging.DEBUG,
    LogLevel.WARNING.value.lower(): logging.WARNING,
    LogLevel.WARN.value.lower(): logging.WARNING,
    LogLevel.ERROR.value.lower(): logging.ERROR,
    LogLevel.CRITICAL.value.lower(): logging.CRITICAL,
    LogLevel.CRIT.value.lower(): logging.CRITICAL,
    LogLevel.INFO.value.lower(): logging.INFO,
}
