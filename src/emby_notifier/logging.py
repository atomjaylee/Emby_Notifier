from __future__ import annotations

import datetime
import logging as stdlib_logging
import os

import colorlog


def configure_logger(level: str, export: bool = False, log_path: str = "/var/tmp/emby_notifier_tg"):
    logger = stdlib_logging.getLogger("emby_notifier")
    logger.handlers.clear()
    logger.setLevel(getattr(stdlib_logging, level.upper(), stdlib_logging.INFO))
    logger.propagate = False

    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s[%(levelname)s] : %(message)s",
            log_colors={
                "DEBUG": "white",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    )
    logger.addHandler(console_handler)

    if export:
        os.makedirs(log_path, exist_ok=True)
        filename = datetime.datetime.now().strftime("%Y-%m-%d.log")
        file_handler = stdlib_logging.FileHandler(os.path.join(log_path, filename), encoding="utf-8")
        file_handler.setFormatter(stdlib_logging.Formatter("[%(levelname)s] : %(message)s"))
        logger.addHandler(file_handler)

    return logger
