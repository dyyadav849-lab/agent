import logging
from collections.abc import Mapping
from logging.handlers import QueueHandler

from zion.util.log.queue_listener import log_queue

logging.basicConfig(handlers=[logging.NullHandler()])
#  since we are using "WARN" in golang project, we need to add this level name
logging.addLevelName(logging.WARNING, "WARN")


class Logger:
    def __init__(self, name: str, level: int = logging.DEBUG) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        for log_handler in self.logger.handlers[:]:
            self.logger.removeHandler(log_handler)
        # add queue handler
        queue_handler = QueueHandler(log_queue)
        self.logger.addHandler(queue_handler)

    """
    The 'tags' parameter in the logging methods (info, warn, error, debug, exception) of the Logger class is used to include additional contextual information in the log records.
    This parameter is a dictionary (or None) where each key-value pair represents a tag. These tags are added to the log records as extra fields.

    Here is an example of how to use the 'tags' parameter:

    # Create an instance of Logger
    # logger = Logger(name="my_logger")

    # Define some tags
    # tags = {"user_id": "1234", "transaction_id": "5678"}

    # Use the tags in a log record
    # logger.info("User transaction completed.", tags=tags)

    In this example, the 'tags' dictionary contains two tags: 'user_id' and 'transaction_id'. These tags are included in the log record created by the 'info' method.
    The resulting log record will include these tags as extra fields, providing additional context about the event being logged.

    Please remember not to expose any confidential or sensitive data in the tags.
    """

    def info(
        self, message: object, *args: object, tags: Mapping[str, object] | None = None
    ) -> None:
        self.logger.info(message, *args, extra=tags)

    def warn(
        self, message: object, *args: object, tags: Mapping[str, object] | None = None
    ) -> None:
        self.logger.warning(message, *args, extra=tags)

    def error(
        self, message: object, *args: object, tags: Mapping[str, object] | None = None
    ) -> None:
        self.logger.error(message, *args, extra=tags)

    def debug(
        self, message: object, *args: object, tags: Mapping[str, object] | None = None
    ) -> None:
        self.logger.debug(message, *args, extra=tags)

    def exception(
        self, message: object, *args: object, tags: Mapping[str, object] | None = None
    ) -> None:
        self.logger.exception(message, *args, extra=tags)
