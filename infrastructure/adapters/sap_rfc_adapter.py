"""SAPRFCAdapter — stub implementation of SAPDiscoveryPort.

The real implementation requires the pyrfc library which in turn depends on
the SAP NetWeaver RFC SDK (a proprietary C library).  This stub returns
placeholder data structures showing what real RFC calls would return.

Real implementation would use these RFC function modules:
- RFC_READ_TABLE: Read arbitrary SAP tables (TADIR, TRDIR, etc.)
- RPY_FUNCTIONMODULE_READ: Read function module source code
- RPY_PROGRAM_READ: Read ABAP program source
- RPY_CLIF_DEF_READ: Read class/interface definition
- REPOSITORY_INFOSYSTEM: Query the ABAP repository for custom objects
- BAPI_SYSTEM_INFO_GET: Retrieve system metadata
- RFC_SYSTEM_INFO: Get system ID, database info, etc.
- SWNC_STATREC_READ: Read workload statistics for user count estimation
"""

from __future__ import annotations

from typing import Any


class SAPRFCAdapter:
    """Stub implementation of SAPDiscoveryPort for development.

    Replace with pyrfc-backed implementation when SAP NW RFC SDK is available.
    """

    def __init__(
        self,
        host: str = "",
        system_number: str = "00",
        client: str = "100",
        user: str = "",
        password: str = "",
    ) -> None:
        self._host = host
        self._system_number = system_number
        self._client = client
        self._user = user
        self._password = password

    async def extract_custom_objects(self, connection: Any) -> list[dict]:
        """Extract custom Z/Y objects from the SAP repository.

        Real implementation would call:
          RFC_READ_TABLE on TADIR where OBJ_NAME LIKE 'Z%' OR OBJ_NAME LIKE 'Y%'
          Then for each object, call the appropriate RFC to get source code:
          - RPY_PROGRAM_READ for programs
          - RPY_FUNCTIONMODULE_READ for function modules
          - RPY_CLIF_DEF_READ for classes/interfaces

        Returns a list of dicts with keys:
          object_name, object_type, package_name, source_code (if available)
        """
        return [
            {
                "object_name": "Z_FI_CUSTOM_BSEG_REPORT",
                "object_type": "PROG",
                "package_name": "ZFINANCE",
                "source_code": "* Placeholder — real source would come from RPY_PROGRAM_READ",
                "description": "Custom financial line item report accessing BSEG directly",
            },
            {
                "object_name": "Z_MM_VENDOR_LOOKUP",
                "object_type": "FUGR",
                "package_name": "ZMM_CUSTOM",
                "source_code": "* Placeholder — real source would come from RPY_FUNCTIONMODULE_READ",
                "description": "Vendor master lookup using LFA1 (pre-Business Partner)",
            },
            {
                "object_name": "ZCL_SD_PRICING_ENGINE",
                "object_type": "CLAS",
                "package_name": "ZSD_PRICING",
                "source_code": "* Placeholder — real source would come from RPY_CLIF_DEF_READ",
                "description": "Custom pricing engine with KONV table access",
            },
        ]

    async def extract_integration_points(self, connection: Any) -> list[dict]:
        """Extract integration points (IDocs, RFCs, web services).

        Real implementation would query:
          - EDIPOA/EDIDC for IDoc interfaces
          - RFCDES for RFC destinations
          - SOTR_HEAD for web service endpoints

        Returns a list of dicts with keys:
          name, type (IDOC/RFC/ODATA/WEBSERVICE), direction (INBOUND/OUTBOUND),
          target_system
        """
        return [
            {
                "name": "ORDERS05",
                "type": "IDOC",
                "direction": "INBOUND",
                "target_system": "ERP_TO_CRM",
                "description": "Sales order inbound IDoc from CRM",
            },
            {
                "name": "Z_RFC_GET_VENDOR",
                "type": "RFC",
                "direction": "OUTBOUND",
                "target_system": "SRM",
                "description": "Custom RFC for vendor data to SRM",
            },
            {
                "name": "API_BUSINESS_PARTNER",
                "type": "ODATA",
                "direction": "OUTBOUND",
                "target_system": "FIORI",
                "description": "Business Partner OData service for Fiori apps",
            },
        ]

    async def extract_landscape_metadata(self, connection: Any) -> dict:
        """Extract system-level metadata (DB size, user count, version).

        Real implementation would call:
          - RFC_SYSTEM_INFO / BAPI_SYSTEM_INFO_GET for system details
          - DB02 equivalent RFC for database size
          - USR02 table read for active user count

        Returns a dict with keys:
          system_id, db_type, db_size_gb, number_of_users,
          sap_release, kernel_release
        """
        return {
            "system_id": "S4D",
            "db_type": "HANA",
            "db_size_gb": 850.0,
            "number_of_users": 2500,
            "sap_release": "750",
            "kernel_release": "753",
            "os_type": "Linux",
            "unicode": True,
        }
