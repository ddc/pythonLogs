"""Smoke test to verify the built package works correctly."""

from pythonLogs import BasicLog, SizeRotatingLog, TimedRotatingLog, __version__

assert __version__, "Version should not be empty"
assert BasicLog, "BasicLog should be importable"
assert TimedRotatingLog, "TimedRotatingLog should be importable"
assert SizeRotatingLog, "SizeRotatingLog should be importable"

print(f"pythonLogs {__version__} OK")
