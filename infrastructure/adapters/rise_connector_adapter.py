"""RISEConnectorAdapter — stub implementation of RISEConnectorPort.

Returns realistic mock data for development.  The real implementation would
use one of two connection modes:

RFC mode (pyrfc):
  - BAPI_SYSTEM_INFO_GET / RFC_SYSTEM_INFO for system metadata
  - STMS_IMPORT / CTS_API_READ_TRANSPORTS for transport management
  - /SDF/READINESS_CHECK for readiness assessment

OData mode (REST):
  - /sap/opu/odata/sap/API_SYSTEM_INFO for system metadata
  - /sap/opu/odata/sap/API_TRANSPORT_MANAGEMENT for transports
  - /sap/opu/odata/sap/API_READINESS_CHECK for readiness assessment
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from domain.value_objects.rise_types import (
    OverallReadinessStatus,
    ReadinessCheckItem,
    ReadinessCheckResult,
    ReadinessCheckSeverity,
    ReadinessCheckStatus,
    RISEConnection,
    RISEConnectionMode,
    SAPSystemInfo,
    TransportRequest,
    TransportResult,
    TransportStatus,
)

logger = logging.getLogger(__name__)


class RISEConnectorAdapter:
    """Stub RISE connector for development — returns realistic mock data.

    Replace with pyrfc-backed or OData-backed implementation when
    SAP system connectivity is available.
    """

    async def get_system_info(self, connection: RISEConnection) -> SAPSystemInfo:
        """Retrieve system metadata via RFC or OData.

        TODO: Real implementation:
          RFC mode  -> call BAPI_SYSTEM_INFO_GET, RFC_SYSTEM_INFO
          OData mode -> GET /sap/opu/odata/sap/API_SYSTEM_INFO
        """
        logger.info(
            "RISE stub: get_system_info for %s:%d (mode=%s)",
            connection.host,
            connection.port,
            connection.mode.value,
        )

        if connection.mode == RISEConnectionMode.RFC:
            return self._mock_system_info_rfc(connection)
        return self._mock_system_info_odata(connection)

    async def get_transport_list(self, connection: RISEConnection) -> list[TransportRequest]:
        """List transport requests in the target system.

        TODO: Real implementation:
          RFC mode  -> call CTS_API_READ_TRANSPORTS / STMS table reads
          OData mode -> GET /sap/opu/odata/sap/API_TRANSPORT_MANAGEMENT/TransportRequests
        """
        logger.info(
            "RISE stub: get_transport_list for %s:%d",
            connection.host,
            connection.port,
        )

        return [
            TransportRequest(
                id="S4DK900001",
                description="RISE migration: Custom FI reports",
                owner="MIGUSER",
                status=TransportStatus.RELEASED,
                created_at=datetime(2026, 2, 15, 9, 30, 0, tzinfo=timezone.utc),
                objects=(
                    "PROG Z_FI_CUSTOM_BSEG_REPORT",
                    "PROG Z_FI_BALANCE_RECON",
                    "TABL ZFIT_CUSTOM_CONFIG",
                ),
            ),
            TransportRequest(
                id="S4DK900002",
                description="RISE migration: MM custom enhancements",
                owner="MIGUSER",
                status=TransportStatus.RELEASED,
                created_at=datetime(2026, 2, 16, 14, 0, 0, tzinfo=timezone.utc),
                objects=(
                    "FUGR Z_MM_VENDOR_LOOKUP",
                    "CLAS ZCL_MM_GOODS_RECEIPT",
                ),
            ),
            TransportRequest(
                id="S4DK900003",
                description="RISE migration: SD pricing customizations",
                owner="DEVLEAD",
                status=TransportStatus.MODIFIABLE,
                created_at=datetime(2026, 2, 20, 11, 15, 0, tzinfo=timezone.utc),
                objects=(
                    "CLAS ZCL_SD_PRICING_ENGINE",
                    "INTF ZIF_SD_PRICING_STRATEGY",
                    "TABL ZSDT_PRICE_RULES",
                ),
            ),
            TransportRequest(
                id="S4DK900004",
                description="RISE migration: Basis configuration",
                owner="BASISADM",
                status=TransportStatus.IMPORTED,
                created_at=datetime(2026, 1, 28, 8, 0, 0, tzinfo=timezone.utc),
                objects=(
                    "TABL ZTAB_SYSTEM_CONFIG",
                    "PROG Z_BASIS_HEALTH_CHECK",
                ),
            ),
        ]

    async def execute_transport(
        self, connection: RISEConnection, transport_id: str
    ) -> TransportResult:
        """Execute (import) a transport request into the target system.

        TODO: Real implementation:
          RFC mode  -> call STMS_IMPORT or TMS_MGR_IMPORT_TR_REQUEST
          OData mode -> POST /sap/opu/odata/sap/API_TRANSPORT_MANAGEMENT/ImportTransport
        """
        logger.info(
            "RISE stub: execute_transport %s on %s:%d",
            transport_id,
            connection.host,
            connection.port,
        )

        # Simulate successful transport for stub
        return TransportResult(
            transport_id=transport_id,
            success=True,
            return_code=0,
            messages=(
                f"Transport {transport_id} imported successfully",
                "Post-import activation completed",
                "No warnings or errors detected",
            ),
        )

    async def get_readiness_check(self, connection: RISEConnection) -> ReadinessCheckResult:
        """Run the RISE readiness check suite against the source system.

        TODO: Real implementation:
          RFC mode  -> call /SDF/READINESS_CHECK or equivalent BAdI
          OData mode -> POST /sap/opu/odata/sap/API_READINESS_CHECK/RunCheck
        """
        logger.info(
            "RISE stub: get_readiness_check for %s:%d",
            connection.host,
            connection.port,
        )

        checks = (
            ReadinessCheckItem(
                name="SAP Kernel Version",
                status=ReadinessCheckStatus.PASSED,
                message="Kernel 753 patch level 1200 meets minimum requirement",
                severity=ReadinessCheckSeverity.INFO,
            ),
            ReadinessCheckItem(
                name="Unicode System Check",
                status=ReadinessCheckStatus.PASSED,
                message="System is Unicode-enabled (required for S/4HANA)",
                severity=ReadinessCheckSeverity.INFO,
            ),
            ReadinessCheckItem(
                name="Custom Code Compatibility",
                status=ReadinessCheckStatus.WARNING,
                message="327 custom objects require review for S/4HANA compatibility",
                severity=ReadinessCheckSeverity.WARNING,
            ),
            ReadinessCheckItem(
                name="Database Size Assessment",
                status=ReadinessCheckStatus.PASSED,
                message="Database size 850 GB within acceptable range for HANA migration",
                severity=ReadinessCheckSeverity.INFO,
            ),
            ReadinessCheckItem(
                name="Add-on Compatibility",
                status=ReadinessCheckStatus.WARNING,
                message="2 add-ons require updated versions for S/4HANA 2023",
                severity=ReadinessCheckSeverity.WARNING,
            ),
            ReadinessCheckItem(
                name="Business Function Activation",
                status=ReadinessCheckStatus.PASSED,
                message="All prerequisite business functions are active",
                severity=ReadinessCheckSeverity.INFO,
            ),
            ReadinessCheckItem(
                name="Simplification Item Check",
                status=ReadinessCheckStatus.WARNING,
                message="15 simplification items impact custom code — remediation recommended",
                severity=ReadinessCheckSeverity.WARNING,
            ),
            ReadinessCheckItem(
                name="Data Volume Assessment",
                status=ReadinessCheckStatus.PASSED,
                message="Archiving recommendations generated for 3 tables exceeding thresholds",
                severity=ReadinessCheckSeverity.INFO,
            ),
            ReadinessCheckItem(
                name="Fiori Launchpad Readiness",
                status=ReadinessCheckStatus.PASSED,
                message="Gateway and front-end server components are at required levels",
                severity=ReadinessCheckSeverity.INFO,
            ),
            ReadinessCheckItem(
                name="HANA Sizing Estimate",
                status=ReadinessCheckStatus.PASSED,
                message="Estimated HANA memory requirement: 512 GB (within provisioned capacity)",
                severity=ReadinessCheckSeverity.INFO,
            ),
        )

        return ReadinessCheckResult(
            overall_status=OverallReadinessStatus.CONDITIONAL,
            checks=checks,
        )

    # ------------------------------------------------------------------
    # Internal helpers for mode-specific mock data
    # ------------------------------------------------------------------

    @staticmethod
    def _mock_system_info_rfc(connection: RISEConnection) -> SAPSystemInfo:
        """Mock system info as if retrieved via RFC calls."""
        return SAPSystemInfo(
            system_id="S4D",
            version="S/4HANA 2023 FPS01",
            db_type="HANA",
            db_size_gb=850.0,
            num_users=2500,
            kernel_version="753 patch 1200",
            unicode_enabled=True,
        )

    @staticmethod
    def _mock_system_info_odata(connection: RISEConnection) -> SAPSystemInfo:
        """Mock system info as if retrieved via OData REST API."""
        return SAPSystemInfo(
            system_id="S4D",
            version="S/4HANA 2023 FPS01",
            db_type="HANA",
            db_size_gb=850.0,
            num_users=2500,
            kernel_version="753 patch 1200",
            unicode_enabled=True,
        )
