import json
import logging
import sys
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_STANDARD_RECORD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__) | {
    "asctime",
    "message",
}


def set_request_id(request_id: str) -> Token[str | None]:
    """Attach a request ID to the current async context."""
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the previous request ID context."""
    _request_id.reset(token)


class RequestContextFilter(logging.Filter):
    """Attach request correlation data to every emitted record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


class JsonFormatter(logging.Formatter):
    """Format one Loki-compatible JSON object per log line."""

    def __init__(self, service_name: str, environment: str) -> None:
        super().__init__()
        self._service_name = service_name
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self._service_name,
            "environment": self._environment,
        }

        request_id = getattr(record, "request_id", None)
        if request_id is not None:
            payload["request_id"] = request_id

        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_FIELDS and key != "request_id":
                payload[key] = value

        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(
    *,
    level: str,
    log_format: str,
    service_name: str,
    environment: str,
) -> None:
    """Configure application and Uvicorn logs through one stdout handler."""
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestContextFilter())

    if log_format == "json":
        handler.setFormatter(JsonFormatter(service_name, environment))
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s "
                "[request_id=%(request_id)s] %(message)s"
            )
        )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    for logger_name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    logging.getLogger("uvicorn.access").disabled = True
