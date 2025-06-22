import logging
import sys


def get_logging_config() -> dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(levelname)s: %(asctime)s - %(name)s: %(message)s"
            }
        },
        "filters": {
            "stdout_filter": {
                "()": LevelFilter,
                "max_level": 39,  # INFO and below
            }
        },
        "handlers": {
            "stdout_handler": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "stream": sys.stdout,
                "filters": ["stdout_filter"]
            },
            "stderr_handler": {
                "class": "logging.StreamHandler",
                "level": "ERROR",
                "formatter": "standard",
                "stream": sys.stderr
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["stdout_handler", "stderr_handler"]
        }
    }


def get_logging_level_by_verbosity(i):
    return {
        0: logging.NOTSET,
        1: logging.ERROR,
        2: logging.INFO,
        3: logging.DEBUG
    }.get(i)


class LevelFilter(logging.Filter):
    def __init__(self, min_level=None, max_level=None):
        super().__init__()
        self.min_level = min_level
        self.max_level = max_level

    def filter(self, record):
        if self.min_level is not None and record.levelno < self.min_level:
            return False
        if self.max_level is not None and record.levelno > self.max_level:
            return False
        return True
