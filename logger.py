import logging
import sys

LOGGER_NAME = "MCQConverter"


def setup_logger(level=logging.INFO):
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    fmt = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger


def get_logger():
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        setup_logger()
    return logger
