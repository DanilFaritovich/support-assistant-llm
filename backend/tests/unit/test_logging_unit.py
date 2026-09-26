import json
import logging

from app.core.logging import (
    JsonFormatter,
    RequestContextFilter,
    reset_request_id,
    set_request_id,
)


def test_json_formatter_includes_service_context_and_request_id() -> None:
    formatter = JsonFormatter(
        service_name="support-assistant-backend",
        environment="test",
    )
    context_filter = RequestContextFilter()
    token = set_request_id("request-123")

    try:
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Operation completed.",
            args=(),
            exc_info=None,
        )
        record.event = "test_event"
        context_filter.filter(record)

        payload = json.loads(formatter.format(record))
    finally:
        reset_request_id(token)

    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["message"] == "Operation completed."
    assert payload["service"] == "support-assistant-backend"
    assert payload["environment"] == "test"
    assert payload["request_id"] == "request-123"
    assert payload["event"] == "test_event"
