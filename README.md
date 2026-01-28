<h1 align="center">
  <img src="https://raw.githubusercontent.com/ddc/pythonLogs/main/assets/pythonLogs-icon.svg" alt="pythonLogs" width="150">
  <br>
  pythonLogs
</h1>

<p align="center">
    <a href="https://www.paypal.com/ncp/payment/6G9Z78QHUD4RJ"><img src="https://img.shields.io/badge/Donate-PayPal-brightgreen.svg?style=plastic" alt="Donate"/></a>
    <a href="https://github.com/sponsors/ddc"><img src="https://img.shields.io/static/v1?style=plastic&label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=ff69b4" alt="Sponsor"/></a>
    <br>
    <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json?style=plastic" alt="uv"/></a>
    <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json?style=plastic" alt="Ruff"/></a>
    <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg?style=plastic" alt="Code style: black"/></a>
    <br>
    <a href="https://www.python.org/downloads"><img src="https://img.shields.io/pypi/pyversions/pythonLogs.svg?style=plastic&logo=python&cacheSeconds=3600" alt="Python"/></a>
    <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=plastic" alt="License: MIT"/></a>
    <a href="https://pepy.tech/projects/pythonLogs"><img src="https://static.pepy.tech/badge/pythonLogs?style=plastic" alt="PyPI Downloads"/></a>
    <a href="https://pypi.python.org/pypi/pythonLogs"><img src="https://img.shields.io/pypi/v/pythonLogs.svg?style=plastic&logo=python&cacheSeconds=3600" alt="PyPi"/></a>
    <br>
    <a href="https://github.com/ddc/pythonLogs/issues"><img src="https://img.shields.io/github/issues/ddc/pythonLogs?style=plastic" alt="issues"/></a>
    <a href="https://codecov.io/gh/ddc/pythonLogs"><img src="https://codecov.io/gh/ddc/pythonLogs/graph/badge.svg?token=XWB53034GI&style=plastic" alt="codecov"/></a>
    <a href="https://sonarcloud.io/dashboard?id=ddc_pythonLogs"><img src="https://sonarcloud.io/api/project_badges/measure?project=ddc_pythonLogs&metric=alert_status&style=plastic" alt="Quality Gate Status"/></a>
    <a href="https://github.com/ddc/pythonLogs/actions/workflows/workflow.yml"><img src="https://github.com/ddc/pythonLogs/actions/workflows/workflow.yml/badge.svg?style=plastic" alt="CI/CD Pipeline"/></a>
    <a href="https://actions-badge.atrox.dev/ddc/pythonLogs/goto?ref=main"><img src="https://img.shields.io/endpoint.svg?url=https%3A//actions-badge.atrox.dev/ddc/pythonLogs/badge?ref=main&label=build&logo=none&style=plastic" alt="Build Status"/></a>
</p>

<p align="center">High-performance Python logging library with file rotation and optimized caching for better performance</p>


# Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Logger Types](#logger-types)
  - [Basic Logger](#basic-logger)
  - [Size Rotating Logger](#size-rotating-logger)
  - [Timed Rotating Logger](#timed-rotating-logger)
- [Context Manager Support](#context-manager-support)
- [Using With Multiple Log Levels and Files](#using-with-multiple-log-levels-and-files)
- [Environment Variables](#env-variables-optional)
  - [Settings Cache Management](#settings-cache-management)
- [Flexible Configuration Options](#flexible-configuration-options)
- [Development](#development)
  - [Create DEV Environment, Running Tests and Building Wheel](#create-dev-environment-running-tests-and-building-wheel)
  - [Optionals](#optionals)
- [License](#license)
- [Support](#support)



# Features

✨ **Factory Pattern** - Easy logger creation with centralized configuration  
🚀 **High Performance** - Optimized caching for 90%+ performance improvements  
🔄 **File Rotation** - Automatic rotation by size or time with compression  
🎯 **Type Safety** - Enum-based configuration with IDE support  
⚙️ **Flexible Configuration** - Environment variables, direct parameters, or defaults  
📍 **Location Tracking** - Optional filename and line number in logs  
🌍 **Timezone Support** - Full timezone handling including `localtime` and `UTC`  
💾 **Memory Efficient** - Logger registry and settings caching  
🔒 **Context Manager Support** - Automatic resource cleanup and exception safety  
🧵 **Thread Safe** - Concurrent access protection for all operations  
🔧 **Resource Management** - Automatic handler cleanup and memory leak prevention  


# Installation

```shell
pip install pythonLogs
```


# Logger Types

> **Tip:** All logger types support both string values (e.g., `level="debug"`) and type-safe enums (e.g., `level=LogLevel.DEBUG`). \
> See [Flexible Configuration Options](#flexible-configuration-options) for all available enums.

## Basic Logger

Console-only logging without file output. Perfect for development and simple applications.

### Usage

```python
from pythonLogs import BasicLog

logger = BasicLog(
    name="my_app",
    level="debug",  # "debug", "info", "warning", "error", "critical"
    timezone="America/Sao_Paulo",
    showlocation=False
)
logger.warning("This is a warning example")
```

### Example Output

`[2024-10-08T19:08:56.918-0300]:[WARNING]:[my_app]:This is a warning example`





## Size Rotating Logger

File-based logging with automatic rotation when files reach a specified size. Rotated files are compressed as `.gz`.

- **Rotation**: Based on file size (`maxmbytes` parameter)
- **Naming**: Rotated logs have sequence numbers: `app.log_1.gz`, `app.log_2.gz`
- **Cleanup**: Old logs deleted based on `daystokeep` (default: 30 days)

### Usage

```python
from pythonLogs import SizeRotatingLog

logger = SizeRotatingLog(
    name="my_app",
    level="debug",  # "debug", "info", "warning", "error", "critical"
    directory="/app/logs",
    filenames=["main.log", "app1.log"],
    maxmbytes=5,
    daystokeep=7,
    timezone="America/Chicago",
    streamhandler=True,
    showlocation=False
)
logger.warning("This is a warning example")
```

### Example Output

`[2024-10-08T19:08:56.918-0500]:[WARNING]:[my_app]:This is a warning example`





## Timed Rotating Logger

File-based logging with automatic rotation based on time intervals. Rotated files are compressed as `.gz`.

- **Rotation**: Based on time (`when` parameter, defaults to `midnight`)
- **Naming**: Rotated logs have date suffix: `app_20240816.log.gz`
- **Cleanup**: Old logs deleted based on `daystokeep` (default: 30 days)
- **Supported Intervals**: `midnight`, `hourly`, `daily`, `W0-W6` (weekdays, 0=Monday)

### Usage

```python
from pythonLogs import TimedRotatingLog

logger = TimedRotatingLog(
    name="my_app",
    level="debug",  # "debug", "info", "warning", "error", "critical"
    directory="/app/logs",
    filenames=["main.log", "app2.log"],
    when="midnight",  # "midnight", "H", "D", "W0"-"W6"
    daystokeep=7,
    timezone="UTC",
    streamhandler=True,
    showlocation=False
)
logger.warning("This is a warning example")
```

### Example Output

`[2024-10-08T19:08:56.918-0000]:[WARNING]:[my_app]:This is a warning example`





# Context Manager Support

All logger types support context managers for automatic resource cleanup and exception safety.

## Usage Examples

```python
from pythonLogs import LogLevel
from pythonLogs.basic_log import BasicLog
from pythonLogs.size_rotating import SizeRotatingLog
from pythonLogs.timed_rotating import TimedRotatingLog

# Automatic cleanup with context managers
with BasicLog(name="app", level=LogLevel.INFO) as logger:
    logger.info("This is automatically cleaned up")
    # Handlers are automatically closed on exit

with SizeRotatingLog(name="app", directory="/logs", filenames=["app.log"]) as logger:
    logger.info("File handlers cleaned up automatically")
    # File handlers closed and resources freed

# Exception safety - cleanup happens even if exceptions occur
try:
    with TimedRotatingLog(name="app", directory="/logs") as logger:
        logger.error("Error occurred")
        raise ValueError("Something went wrong")
except ValueError:
    pass  # Logger was still cleaned up properly
```





# Using With Multiple Log Levels and Files

```python
from pythonLogs import SizeRotatingLog, TimedRotatingLog, LogLevel, RotateWhen

# Application logger
app_logger = SizeRotatingLog(
    name="production_app",
    directory="/var/log/myapp",
    filenames=["app.log"],
    maxmbytes=50,  # 50MB files
    daystokeep=30,  # Keep 30 days
    level=LogLevel.INFO,
    streamhandler=True,  # Also log to console
    showlocation=True,   # Show file:function:line
    timezone="UTC"
)

# Error logger with longer retention
error_logger = SizeRotatingLog(
    name="production_errors",
    directory="/var/log/myapp",
    filenames=["errors.log"],
    maxmbytes=10,
    daystokeep=90,  # Keep errors longer
    level=LogLevel.ERROR,
    streamhandler=False
)

# Audit logger with daily rotation
audit_logger = TimedRotatingLog(
    name="audit_log",
    directory="/var/log/myapp",
    filenames=["audit.log"],
    when=RotateWhen.MIDNIGHT,
    level=LogLevel.INFO
)

# Use the loggers
app_logger.info("Application started")
error_logger.error("Database connection failed")
audit_logger.info("User admin logged in")
```




# Env Variables (Optional)

The .env variables file can be used by leaving all options blank when calling the class.\
If not specified inside the .env file, it will use the default value.\
This is a good approach for production environments, since options can be changed easily.
```python
from pythonLogs import TimedRotatingLog
log = TimedRotatingLog()
```

```
LOG_LEVEL=DEBUG
LOG_TIMEZONE=UTC
LOG_ENCODING=UTF-8
LOG_APPNAME=app
LOG_FILENAME=app.log
LOG_DIRECTORY=/app/logs
LOG_DAYS_TO_KEEP=30
LOG_DATE_FORMAT=%Y-%m-%dT%H:%M:%S
LOG_STREAM_HANDLER=True
LOG_SHOW_LOCATION=False
LOG_MAX_LOGGERS=50
LOG_LOGGER_TTL_SECONDS=1800

# SizeRotatingLog
LOG_MAX_FILE_SIZE_MB=10

# TimedRotatingLog
LOG_ROTATE_WHEN=midnight
LOG_ROTATE_AT_UTC=True
LOG_ROTATE_FILE_SUFIX="%Y%m%d"
```

## Settings Cache Management

Use `get_log_settings()` to inspect current configuration and `clear_settings_cache()` to reload configuration from environment variables:

```python
from pythonLogs import get_log_settings, clear_settings_cache

# Inspect current settings
settings = get_log_settings()
print(settings.level)      # Current log level
print(settings.timezone)   # Current timezone

# Clear cache and reload .env on next access (default)
clear_settings_cache()

# Clear cache but keep current .env values
clear_settings_cache(reload_env=False)
```






# Flexible Configuration Options

You can use either enums (for type safety) or strings (for simplicity):

```python
from pythonLogs import LogLevel, RotateWhen

# Option 1: Type-safe enums (recommended)
LogLevel.DEBUG     # "DEBUG"
LogLevel.INFO      # "INFO"
LogLevel.WARNING   # "WARNING"
LogLevel.ERROR     # "ERROR"
LogLevel.CRITICAL  # "CRITICAL"

# Option 2: String values (case-insensitive)
"debug"       # Same as LogLevel.DEBUG
"info"        # Same as LogLevel.INFO
"warning"     # Same as LogLevel.WARNING
"warn"        # Same as LogLevel.WARN (alias)
"error"       # Same as LogLevel.ERROR
"critical"    # Same as LogLevel.CRITICAL
"crit"        # Same as LogLevel.CRIT (alias)
# Also supports: "DEBUG", "Info", "Warning", etc.

# RotateWhen values
RotateWhen.MIDNIGHT   # "midnight"
RotateWhen.HOURLY     # "H"
RotateWhen.DAILY      # "D"
RotateWhen.MONDAY     # "W0"
# ... through SUNDAY  # "W6"
# String equivalents: "midnight", "H", "D", "W0"-"W6"
```





# Development

Must have [UV](https://uv.run/docs/getting-started/installation),
[Black](https://black.readthedocs.io/en/stable/getting_started.html),
[Ruff](https://docs.astral.sh/ruff/installation/), and
[Poe the Poet](https://poethepoet.naber.dev/installation) installed.

## Create DEV Environment, Running Tests and Building Wheel

```shell
uv sync --all-extras
poe linter
poe test
poe build
```

## Optionals

### Create a cprofile.prof file from unit tests
```shell
poe profile
```





# License

Released under the [MIT License](LICENSE)





# Support

If you find this project helpful, consider supporting development:

- [GitHub Sponsor](https://github.com/sponsors/ddc)
- [ko-fi](https://ko-fi.com/ddcsta)
- [PayPal](https://www.paypal.com/ncp/payment/6G9Z78QHUD4RJ)
