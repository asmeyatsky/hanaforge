"""QuickSizerXMLParser — extracts SAP sizing parameters from Quick Sizer XML output.

Implements QuickSizerParserPort. Parses the standard SAP Quick Sizer export format
and maps extracted values to a domain SizingInput value object.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from domain.value_objects.gcp_types import SizingInput
from domain.value_objects.object_type import SystemRole


# ---------------------------------------------------------------------------
# XML element paths used in SAP Quick Sizer exports
# ---------------------------------------------------------------------------

_XPATH_SAPS = ".//SAPSRating"
_XPATH_SAPS_ALT = ".//SAPS"
_XPATH_MEMORY = ".//HANAMemory"
_XPATH_MEMORY_ALT = ".//MainMemory"
_XPATH_DB_SIZE = ".//DBSize"
_XPATH_DB_SIZE_ALT = ".//DatabaseSize"
_XPATH_USERS = ".//ConcurrentUsers"
_XPATH_USERS_ALT = ".//Users"
_XPATH_LANDSCAPE = ".//LandscapeType"
_XPATH_LANDSCAPE_ALT = ".//SystemRole"

_LANDSCAPE_MAP: dict[str, SystemRole] = {
    "DEV": SystemRole.DEV,
    "DEVELOPMENT": SystemRole.DEV,
    "QAS": SystemRole.QAS,
    "QUALITY": SystemRole.QAS,
    "QA": SystemRole.QAS,
    "PRD": SystemRole.PRD,
    "PRODUCTION": SystemRole.PRD,
    "PROD": SystemRole.PRD,
}


class QuickSizerXMLParser:
    """Implements QuickSizerParserPort — parses SAP Quick Sizer XML into SizingInput."""

    async def parse_quick_sizer_xml(self, xml_bytes: bytes) -> SizingInput:
        """Parse Quick Sizer XML and return a domain SizingInput value object.

        Supports multiple XML schema variations from different Quick Sizer versions.
        Falls back to sensible defaults when optional elements are missing.
        """
        root = ET.fromstring(xml_bytes)

        saps = self._extract_int(root, _XPATH_SAPS, _XPATH_SAPS_ALT, default=10_000)
        memory_gb = self._extract_int(root, _XPATH_MEMORY, _XPATH_MEMORY_ALT, default=256)
        db_size_gb = self._extract_float(root, _XPATH_DB_SIZE, _XPATH_DB_SIZE_ALT, default=500.0)
        users = self._extract_int(root, _XPATH_USERS, _XPATH_USERS_ALT, default=100)
        landscape_str = self._extract_text(root, _XPATH_LANDSCAPE, _XPATH_LANDSCAPE_ALT, default="PRD")
        landscape_type = _LANDSCAPE_MAP.get(landscape_str.upper(), SystemRole.PRD)

        return SizingInput(
            saps_rating=saps,
            hana_memory_gb=memory_gb,
            db_size_gb=db_size_gb,
            concurrent_users=users,
            landscape_type=landscape_type,
        )

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_int(
        root: ET.Element,
        xpath_primary: str,
        xpath_alt: str,
        *,
        default: int,
    ) -> int:
        for xpath in (xpath_primary, xpath_alt):
            elem = root.find(xpath)
            if elem is not None and elem.text:
                try:
                    return int(float(elem.text.strip()))
                except ValueError:
                    continue
        return default

    @staticmethod
    def _extract_float(
        root: ET.Element,
        xpath_primary: str,
        xpath_alt: str,
        *,
        default: float,
    ) -> float:
        for xpath in (xpath_primary, xpath_alt):
            elem = root.find(xpath)
            if elem is not None and elem.text:
                try:
                    return float(elem.text.strip())
                except ValueError:
                    continue
        return default

    @staticmethod
    def _extract_text(
        root: ET.Element,
        xpath_primary: str,
        xpath_alt: str,
        *,
        default: str,
    ) -> str:
        for xpath in (xpath_primary, xpath_alt):
            elem = root.find(xpath)
            if elem is not None and elem.text:
                return elem.text.strip()
        return default
