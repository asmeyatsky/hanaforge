"""LocalDataProfilingAdapter — pure Python in-memory data profiling implementation."""

from __future__ import annotations

import csv
import io
import xml.etree.ElementTree as ET

from domain.ports.data_analysis_ports import ProfileResult
from domain.value_objects.data_quality import FieldNullRate


class LocalDataProfilingAdapter:
    """Implements DataProfilingPort using pure Python in-memory analysis.

    Profiles table data for: record counts, null rates per field,
    duplicate key detection, and character encoding issues.
    """

    async def profile_table(
        self,
        table_data: bytes,
        format: str,
    ) -> ProfileResult:
        """Profile a table dataset and return structured results."""
        rows = self._parse_data(table_data, format)

        if not rows:
            return ProfileResult(
                record_count=0,
                field_count=0,
                null_rates=(),
                duplicate_keys=0,
                encoding_issues=(),
            )

        record_count = len(rows)
        fields = list(rows[0].keys()) if rows else []
        field_count = len(fields)

        # Calculate null rates per field
        null_rates = self._calculate_null_rates(rows, fields, record_count)

        # Detect duplicate keys (use first field as key column heuristic)
        duplicate_keys = self._detect_duplicate_keys(rows, fields)

        # Check encoding issues
        encoding_issues = self._detect_encoding_issues(rows, fields)

        return ProfileResult(
            record_count=record_count,
            field_count=field_count,
            null_rates=tuple(null_rates),
            duplicate_keys=duplicate_keys,
            encoding_issues=tuple(encoding_issues),
        )

    def _parse_data(self, table_data: bytes, format: str) -> list[dict]:
        """Parse raw bytes into list of dicts based on format."""
        if not table_data:
            return []

        text = table_data.decode("utf-8", errors="replace")

        if format.lower() == "csv":
            reader = csv.DictReader(io.StringIO(text))
            return list(reader)

        if format.lower() == "xml":
            return self._parse_xml(text)

        if format.lower() == "xlsx":
            # For XLSX, attempt CSV fallback (openpyxl may not be available)
            try:
                import openpyxl

                wb = openpyxl.load_workbook(io.BytesIO(table_data), read_only=True)
                ws = wb.active
                if ws is None:
                    return []
                all_rows = list(ws.iter_rows(values_only=True))
                if not all_rows:
                    return []
                headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(all_rows[0])]
                result = []
                for row in all_rows[1:]:
                    record = {}
                    for i, value in enumerate(row):
                        if i < len(headers):
                            record[headers[i]] = value
                    result.append(record)
                wb.close()
                return result
            except ImportError:
                reader = csv.DictReader(io.StringIO(text))
                return list(reader)

        return []

    @staticmethod
    def _parse_xml(text: str) -> list[dict]:
        """Parse XML into list of dicts."""
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return []

        records: list[dict] = []
        for record_elem in root.iter("Record"):
            row: dict = {}
            for field_elem in record_elem:
                field_name = field_elem.get("name", field_elem.tag)
                row[field_name] = field_elem.text or ""
            if row:
                records.append(row)

        if not records:
            for record_elem in root:
                row = {}
                for field_elem in record_elem:
                    row[field_elem.tag] = field_elem.text or ""
                if row:
                    records.append(row)

        return records

    @staticmethod
    def _calculate_null_rates(
        rows: list[dict],
        fields: list[str],
        record_count: int,
    ) -> list[FieldNullRate]:
        """Calculate null/empty rates for each field."""
        null_rates: list[FieldNullRate] = []
        for field in fields:
            null_count = sum(1 for row in rows if row.get(field) is None or str(row.get(field, "")).strip() == "")
            null_rates.append(
                FieldNullRate(
                    field_name=field,
                    null_count=null_count,
                    total_count=record_count,
                )
            )
        return null_rates

    @staticmethod
    def _detect_duplicate_keys(rows: list[dict], fields: list[str]) -> int:
        """Detect duplicate records based on the first field (assumed primary key)."""
        if not fields or not rows:
            return 0

        key_field = fields[0]
        seen: dict[str, int] = {}
        duplicates = 0

        for row in rows:
            key_val = str(row.get(key_field, ""))
            if key_val in seen:
                if seen[key_val] == 1:
                    duplicates += 1  # first duplicate pair
                duplicates += 0 if seen[key_val] > 1 else 0
                seen[key_val] += 1
            else:
                seen[key_val] = 1

        # Count total records that are part of any duplicate group
        return sum(count - 1 for count in seen.values() if count > 1)

    @staticmethod
    def _detect_encoding_issues(rows: list[dict], fields: list[str]) -> list[str]:
        """Detect fields with potential character encoding problems."""
        issues: list[str] = []
        replacement_char = "\ufffd"  # Unicode replacement character

        for field in fields:
            has_issue = False
            for row in rows:
                value = str(row.get(field, ""))
                if replacement_char in value:
                    has_issue = True
                    break
                # Check for common encoding artefacts
                for artefact in ("Ã¤", "Ã¶", "Ã¼", "Ã", "â€"):
                    if artefact in value:
                        has_issue = True
                        break
                if has_issue:
                    break
            if has_issue:
                issues.append(f"Encoding issue detected in field: {field}")

        return issues
