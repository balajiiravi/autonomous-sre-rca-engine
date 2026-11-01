
import logging
from pathlib import Path
from contextvars import ContextVar

# Request ID shared across asynchronous service calls
request_id_context = ContextVar(
    "request_id",
    default="system"
)

LOG_FILE = Path("production_telemetry.log")


class RequestContextFilter(logging.Filter):
    """
    Inject request_id into every log record.
    """

    def filter(self, record):
        record.request_id = request_id_context.get()
        return True


def configure_logging():
    """
    Configure centralized file and console logging.
    """

    root = logging.getLogger()

    root.handlers.clear()
    root.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] "
        "[%(name)s] "
        "[%(levelname)s] "
        "[request_id=%(request_id)s] "
        "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler
    file_handler = logging.FileHandler(
        LOG_FILE,
        mode="a",
        encoding="utf-8"
    )

    file_handler.setFormatter(formatter)
    file_handler.addFilter(RequestContextFilter())

    root.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()

    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestContextFilter())

    root.addHandler(console_handler)


def get_service_logger(service_name: str):
    """
    Return a logger for an individual microservice.
    """

    return logging.getLogger(service_name)
