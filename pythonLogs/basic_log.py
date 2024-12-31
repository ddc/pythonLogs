# -*- encoding: utf-8 -*-
import logging
from typing import Optional
from pythonLogs.log_utils import get_format, get_level, get_timezone_function
from pythonLogs.settings import LogSettings


class BasicLog:
    def __init__(
        self,
        level: Optional[str] = None,
        name: Optional[str] = None,
        encoding: Optional[str] = None,
        datefmt: Optional[str] = None,
        timezone: Optional[str] = None,
        showlocation: Optional[bool] = None,
    ):
        _settings = LogSettings()
        self.level = get_level(level or _settings.level)
        self.appname = name or _settings.appname
        self.encoding = encoding or _settings.encoding
        self.datefmt = datefmt or _settings.date_format
        self.timezone = timezone or _settings.timezone
        self.showlocation = showlocation or _settings.show_location

    def init(self):
        logger = logging.getLogger(self.appname)
        logger.setLevel(self.level)
        logging.Formatter.converter = get_timezone_function(self.timezone)
        _format = get_format(self.showlocation, self.appname, self.timezone)
        logging.basicConfig(datefmt=self.datefmt, encoding=self.encoding, format=_format)
        return logger
