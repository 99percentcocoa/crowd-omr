import logging
import os
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler


_request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Inject request_id from context into each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx_var.get("-")
        return True


def set_request_id(request_id: str) -> None:
    _request_id_ctx_var.set(request_id)


def clear_request_id() -> None:
    _request_id_ctx_var.set("-")


def _parse_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def setup_logging() -> None:
    """
    Configure application-wide logging.

    Environment variables:
    - LOG_LEVEL: default INFO
    - LOG_DIR: default logs
    - LOG_FILE: default app.log
    - LOG_MAX_BYTES: default 10485760 (10MB)
    - LOG_BACKUP_COUNT: default 5
    - LOG_CONSOLE: default true
    """
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    log_dir = os.getenv("LOG_DIR", "logs").strip()
    log_file_name = os.getenv("LOG_FILE", "app.log").strip()
    log_max_bytes = int(os.getenv("LOG_MAX_BYTES", "10485760"))
    log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    log_console = _parse_bool(os.getenv("LOG_CONSOLE", "true"), True)

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file_name)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | req=%(request_id)s | %(message)s"
    )

    request_filter = RequestIdFilter()

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=log_max_bytes,
        backupCount=log_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(request_filter)
    root_logger.addHandler(file_handler)

    if log_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(request_filter)
        root_logger.addHandler(console_handler)

    # Keep uvicorn logs consistent with application logging.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.propagate = True
