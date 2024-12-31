# Simple python logs with file rotation

[![Donate](https://img.shields.io/badge/Donate-PayPal-brightgreen.svg?style=plastic)](https://www.paypal.com/ncp/payment/6G9Z78QHUD4RJ)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPi](https://img.shields.io/pypi/v/pythonLogs.svg)](https://pypi.python.org/pypi/pythonLogs)
[![PyPI Downloads](https://static.pepy.tech/badge/pythonLogs)](https://pepy.tech/projects/pythonLogs)
[![codecov](https://codecov.io/gh/ddc/pythonLogs/graph/badge.svg?token=QsjwsmYzgD)](https://codecov.io/gh/ddc/pythonLogs)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Build Status](https://img.shields.io/endpoint.svg?url=https%3A//actions-badge.atrox.dev/ddc/pythonLogs/badge?ref=main&label=build&logo=none)](https://actions-badge.atrox.dev/ddc/pythonLogs/goto?ref=main)
[![Python](https://img.shields.io/pypi/pyversions/pythonLogs.svg)](https://www.python.org)



# Notes
+ Arguments for all classes are declared as OPTIONAL 
  + arguments takes priority over environment variables
+ If any [.env](./pythonLogs/.env.example) variable is omitted, it falls back to default values here: [settings.py](pythonLogs/settings.py)
+ Timezone parameter can also accept `localtime`, default to `UTC`
  + This parameter is only to display the timezone datetime inside the log file
  + For timed rotation, only UTC and localtime are supported, meaning it will rotate at UTC or localtime
    + env variable to change between UTC and localtime is `LOG_ROTATE_AT_UTC` and default to True
+ Streamhandler parameter will add stream handler along with file handler
+ Showlocation parameter will show the filename and the line number where the message originated




# Install
```shell
pip install pythonLogs
```



# BasicLog
+ Setup Logging
  + This is just a basic log, it does not use any file
```python
from pythonLogs import BasicLog
logger = BasicLog(
    level="debug",
    name="app",
    timezone="America/Sao_Paulo",
    showlocation=False,
).init()
logger.warning("This is a warning example")
```
#### Example of output
`[2024-10-08T19:08:56.918-0300]:[WARNING]:[app]:This is a warning example`





# SizeRotatingLog
+ Setup Logging
  + Logs will rotate based on the file size using the `maxmbytes` variable
  + Rotated logs will have a sequence number starting from 1: `app.log_1.gz, app.log_2.gz`
  + Logs will be deleted based on the `daystokeep` variable, defaults to 30
```python
from pythonLogs import SizeRotatingLog
logger = SizeRotatingLog(
    level="debug",
    name="app",
    directory="/app/logs",
    filenames=["main.log", "app1.log"],
    maxmbytes=5,
    daystokeep=7,
    timezone="America/Chicago",
    streamhandler=True,
    showlocation=False
).init()
logger.warning("This is a warning example")
```
#### Example of output
`[2024-10-08T19:08:56.918-0500]:[WARNING]:[app]:This is a warning example`





# TimedRotatingLog
+ Setup Logging
  + Logs will rotate based on `when` variable to a `.gz` file, defaults to `midnight`
  + Rotated log will have the sufix variable on its name: `app_20240816.log.gz`
  + Logs will be deleted based on the `daystokeep` variable, defaults to 30
  + Current 'when' events supported:
      + midnight — roll over at midnight
      + W{0-6} - roll over on a certain day; 0 - Monday
```python
from pythonLogs import TimedRotatingLog
logger = TimedRotatingLog(
    level="debug",
    name="app",
    directory="/app/logs",
    filenames=["main.log", "app2.log"],
    when="midnight",
    daystokeep=7,
    timezone="UTC",
    streamhandler=True,
    showlocation=False
).init()
logger.warning("This is a warning example")
```
#### Example of output
`[2024-10-08T19:08:56.918-0000]:[WARNING]:[app]:This is a warning example`





## Env Variables (Optional)
```
LOG_LEVEL=DEBUG
LOG_TIMEZONE=America/Chicago
LOG_ENCODING=UTF-8
LOG_APPNAME=app
LOG_FILENAME=app.log
LOG_DIRECTORY=/app/logs
LOG_DAYS_TO_KEEP=30
LOG_STREAM_HANDLER=True
LOG_SHOW_LOCATION=False
LOG_DATE_FORMAT=%Y-%m-%dT%H:%M:%S

# SizeRotatingLog
LOG_MAX_FILE_SIZE_MB=10

# TimedRotatingLog
LOG_ROTATE_WHEN=midnight
LOG_ROTATE_AT_UTC=True
```




# Source Code
### Build
```shell
poetry build -f wheel
```



# Run Tests and Get Coverage Report using Poe
```shell
poetry update --with test
poe test
```



# License
Released under the [MIT License](LICENSE)




# Buy me a cup of coffee
+ [GitHub Sponsor](https://github.com/sponsors/ddc)
+ [ko-fi](https://ko-fi.com/ddcsta)
+ [Paypal](https://www.paypal.com/ncp/payment/6G9Z78QHUD4RJ)
