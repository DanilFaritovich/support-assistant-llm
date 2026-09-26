import pytest
from pydantic import ValidationError

from app.api.schemas.ticket_processing import TicketProcessingRequest
from app.api.schemas.ticket_routing import TicketRoutingRequest


def test_accepts_ticket_text_at_maximum_length() -> None:
    ticket_text = "x" * 4000

    routing = TicketRoutingRequest(ticket_text=ticket_text)
    processing = TicketProcessingRequest(
        ticket_text=ticket_text,
        department_id=1,
        template="Template",
    )

    assert routing.ticket_text == ticket_text
    assert processing.ticket_text == ticket_text


def test_rejects_routing_ticket_text_over_maximum_length() -> None:
    with pytest.raises(ValidationError):
        TicketRoutingRequest(ticket_text="x" * 4001)


def test_rejects_processing_ticket_text_over_maximum_length() -> None:
    with pytest.raises(ValidationError):
        TicketProcessingRequest(
            ticket_text="x" * 4001,
            department_id=1,
            template="Template",
        )


def test_accepts_template_at_maximum_length() -> None:
    template = "x" * 2000

    request = TicketProcessingRequest(
        ticket_text="Ticket",
        department_id=1,
        template=template,
    )

    assert request.template == template


def test_rejects_template_over_maximum_length() -> None:
    with pytest.raises(ValidationError):
        TicketProcessingRequest(
            ticket_text="Ticket",
            department_id=1,
            template="x" * 2001,
        )
