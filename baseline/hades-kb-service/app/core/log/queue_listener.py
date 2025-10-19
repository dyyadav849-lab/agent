import atexit
import logging
import sys
from logging.handlers import QueueListener, RotatingFileHandler
from queue import Queue

from pythonjsonlogger import jsonlogger

# init log queue for handler and listener
log_queue: Queue = Queue()
log_qlistener: QueueListener = QueueListener(log_queue, respect_handler_level=True)
log_qlistener.start()
atexit.register(log_qlistener.stop)


def _get_log_formatter() -> jsonlogger.JsonFormatter:
    return jsonlogger.JsonFormatter(
        "%(name)s %(asctime)s %(message)s %(levelname)s %(filename)s %(lineno)s %(process)d",
        rename_fields={
            "levelname": "log_level",
            "asctime": "timestamp",
            "name": "tags",
        },
    )


def _get_file_handler(
    log_path: str = "main.log", log_level: int = logging.DEBUG
) -> RotatingFileHandler:
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2**20,  # 1 MB
        backupCount=10,  # 10 backups
        encoding="utf8",
        delay=True,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(_get_log_formatter())
    return file_handler


def configure_log_listener(
    *, console: bool = True, log_path: str = ""
) -> QueueListener:
    """Configure log queue listener to log into file and console.

    Args:
    ----
        console (bool): whether to log on console
        log_path (str): path of log file
    Returns:
        log_qlistener (logging.handlers.QueueListener): configured log queue listener.
    """
    global log_qlistener  # noqa: PLW0603
    try:
        atexit.unregister(log_qlistener.stop)
        log_qlistener.stop()
    except (AttributeError, NameError):
        pass

    handlers: list[logging.Handler] = []

    # rotating file handler
    if log_path != "":
        file_handler = _get_file_handler(log_path)
        handlers.append(file_handler)

    # console handler
    if console:
        stdout_handler = _get_stdout_handler()
        handlers.append(stdout_handler)

    # we will use log level at logger level,instead at handler level
    log_qlistener = QueueListener(log_queue, *handlers, respect_handler_level=False)
    log_qlistener.start()
    atexit.register(log_qlistener.stop)
    return log_qlistener


def _get_stdout_handler() -> logging.StreamHandler:
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(_get_log_formatter())
    return stdout_handler
