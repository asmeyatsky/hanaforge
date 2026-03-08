"""StubSystemHealthAdapter — simulated system health checks for development.

Implements SystemHealthCheckPort with realistic-looking stub responses.
Replace with real SAP/HANA connectivity checks in production.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class StubSystemHealthAdapter:
    """Returns simulated health check results for HANA, interfaces, and performance."""

    async def check_hana_availability(self, connection_params: dict) -> dict:
        """Simulate HANA availability check."""
        logger.info(
            "StubSystemHealthAdapter: checking HANA availability for %s",
            connection_params.get("host", "unknown"),
        )
        return {
            "hana_ping": "AVAILABLE",
            "app_server": "RUNNING",
            "user_sessions": "ZERO_SESSIONS",
            "interface_status": "ALL_SUSPENDED",
            "hana_health": "HEALTHY",
            "os_status": "OK",
            "memory_utilisation": "62%",
            "cpu_utilisation": "35%",
            "disk_free_gb": 450,
        }

    async def check_interface_connectivity(self, endpoints: list[dict]) -> dict:
        """Simulate interface connectivity checks."""
        logger.info(
            "StubSystemHealthAdapter: checking %d interface endpoints",
            len(endpoints),
        )
        results = {
            "rfc_test": "ALL_CONNECTED",
            "idoc_test": "PROCESSING_OK",
            "api_health": "ALL_HEALTHY",
        }
        for ep in endpoints:
            ep_name = ep.get("name", "unknown")
            results[ep_name] = "CONNECTED"
        return results

    async def check_performance_baseline(self, connection_params: dict) -> dict:
        """Simulate performance baseline checks."""
        logger.info(
            "StubSystemHealthAdapter: checking performance baseline for %s",
            connection_params.get("host", "unknown"),
        )
        return {
            "response_time": "850ms",
            "batch_throughput": "92%",
            "hana_memory": "62%",
            "dialog_response_time": "750ms",
            "rfc_response_time": "120ms",
            "enqueue_time": "5ms",
        }
