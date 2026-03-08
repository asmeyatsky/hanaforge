"""LoggingNotificationAdapter — logs alerts instead of sending real notifications.

Implements NotificationPort. In production, replace with Slack/Teams/email adapter.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class LoggingNotificationAdapter:
    """Implements NotificationPort by logging all alerts."""

    async def send_alert(
        self, channels: list[str], message: str, severity: str
    ) -> bool:
        """Log the alert. Returns True to indicate 'delivery'."""
        logger.info(
            "[ALERT][%s] channels=%s | %s",
            severity,
            ", ".join(channels),
            message,
        )
        return True
