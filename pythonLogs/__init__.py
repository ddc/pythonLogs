from importlib.metadata import version
import logging
from pythonLogs.core.constants import LogLevel, RotateWhen
from pythonLogs.core.factory import BasicLog, SizeRotatingLog, TimedRotatingLog
from typing import Literal, NamedTuple

__all__ = (
    "BasicLog",
    "SizeRotatingLog",
    "TimedRotatingLog",
    "LogLevel",
    "RotateWhen",
)

__title__ = "pythonLogs"
__author__ = "Daniel Costa"
__email__ = "danieldcsta@gmail.com>"
__license__ = "MIT"
__copyright__ = "Copyright 2024-present DDC Softwares"
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
    major=__version__[0],
    minor=__version__[1],
    micro=__version__[2],
    releaselevel="final",
    serial=0,
)
__req_python_version__: VersionInfo = VersionInfo(
    major=_req_python_version[0],
    minor=_req_python_version[1],
    micro=_req_python_version[2],
    releaselevel="final",
    serial=0,
)

logging.getLogger(__name__).addHandler(logging.NullHandler())

del (
    logging,
    NamedTuple,
    Literal,
    VersionInfo,
    version,
    _version,
    _req_python_version,
)
