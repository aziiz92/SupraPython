import os
import sys
import logging
from logging import handlers


def init_logger(logger_name, log_file_path, log_file_name):
    """
    This function was co-opted from https://aykutakin.wordpress.com/2013/08/06/logging-to-console-and-file-in-python/
      with minor changes
    This function sets up a error logger at the debug level and opens a file for that logging to be written to
    Args:
        logger_name:
        log_file_name:
        log_file_path:

    Returns:
        logger
    """
    current_logger = logging.getLogger(logger_name)
    current_logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler = logging.handlers.RotatingFileHandler(os.path.join(log_file_path, log_file_name + "_info.log"),
                                                   mode="a",
                                                   maxBytes=5 * 1024 * 1024,
                                                   backupCount=7,
                                                   encoding="UTF-8")
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    current_logger.addHandler(handler)
    handler2 = logging.handlers.RotatingFileHandler(os.path.join(log_file_path, log_file_name + "_error.log"),
                                                    mode="a",
                                                    maxBytes=5 * 1024 * 1024,
                                                    backupCount=7,
                                                    encoding="UTF-8")
    handler2.setLevel(logging.WARNING)
    handler2.setFormatter(formatter)
    current_logger.addHandler(handler2)
    handler3 = logging.StreamHandler(sys.stdout)
    handler3.setLevel(logging.INFO)
    handler3.setFormatter(formatter)
    current_logger.addHandler(handler3)
    return current_logger


def close_logger(logger_name):
    root_logger = logging.getLogger(logger_name)
    current_handlers = root_logger.handlers[:]
    for handler in current_handlers:
        handler.close()
        root_logger.removeHandler(handler)
