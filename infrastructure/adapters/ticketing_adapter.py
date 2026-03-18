"""StubTicketingAdapter — returns mock ticket IDs for development.

Implements TicketingPort. In production, replace with ServiceNow/Jira adapter.
"""

from __future__ import annotations

import logging
import uuid

logger = logging.getLogger(__name__)


class StubTicketingAdapter:
    """Implements TicketingPort with mock ticket IDs."""

    async def create_ticket(self, title: str, description: str, severity: str, component: str) -> str:
        """Create a mock ticket and return its ID."""
        ticket_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        logger.info(
            "StubTicketingAdapter: created ticket %s — [%s] %s (component: %s)",
            ticket_id,
            severity,
            title,
            component,
        )
        return ticket_id

    async def update_ticket(self, ticket_id: str, status: str, resolution: str) -> bool:
        """Update a mock ticket status."""
        logger.info(
            "StubTicketingAdapter: updated ticket %s — status=%s, resolution=%s",
            ticket_id,
            status,
            resolution,
        )
        return True
