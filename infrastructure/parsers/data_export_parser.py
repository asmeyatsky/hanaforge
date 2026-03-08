"""Data export parser — handles CSV, XLSX, and LTMC XML format parsing."""

from __future__ import annotations

import csv
import io
import xml.etree.ElementTree as ET


class DataExportParser:
    """Parses SAP table data exports from CSV, XLSX, and LTMC-format XML."""

    def parse_csv(self, file_bytes: bytes) -> list[dict]:
        """Parse CSV bytes into a list of row dicts."""
        text = file_bytes.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)

    def parse_xlsx(self, file_bytes: bytes) -> list[dict]:
        """Parse XLSX bytes into a list of row dicts.

        Falls back to CSV parsing if openpyxl is not available.
        """
        try:
            import openpyxl

            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True)
            ws = wb.active
            if ws is None:
                return []

            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return []

            headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
            result: list[dict] = []
            for row in rows[1:]:
                record = {}
                for i, value in enumerate(row):
                    if i < len(headers):
                        record[headers[i]] = value
                result.append(record)

            wb.close()
            return result

        except ImportError:
            # Fallback: attempt CSV parsing
            return self.parse_csv(file_bytes)

    def parse_ltmc_xml(self, file_bytes: bytes) -> list[dict]:
        """Parse LTMC (Legacy Transfer Migration Cockpit) XML format.

        LTMC XML structure typically follows:
        <DataSet>
          <Record>
            <Field name="FIELD_NAME">value</Field>
            ...
          </Record>
          ...
        </DataSet>
        """
        text = file_bytes.decode("utf-8", errors="replace")
        root = ET.fromstring(text)

        records: list[dict] = []

        # Try standard LTMC format
        for record_elem in root.iter("Record"):
            row: dict = {}
            for field_elem in record_elem:
                field_name = field_elem.get("name", field_elem.tag)
                row[field_name] = field_elem.text or ""
            if row:
                records.append(row)

        # Fallback: try flat element-per-field structure
        if not records:
            for record_elem in root:
                row = {}
                for field_elem in record_elem:
                    row[field_elem.tag] = field_elem.text or ""
                if row:
                    records.append(row)

        return records

    @staticmethod
    def detect_format(filename: str) -> str:
        """Detect the file format from the filename extension."""
        lower = filename.lower()
        if lower.endswith(".csv"):
            return "csv"
        if lower.endswith(".xlsx") or lower.endswith(".xls"):
            return "xlsx"
        if lower.endswith(".xml"):
            return "xml"
        raise ValueError(f"Unsupported file format for {filename!r}")
