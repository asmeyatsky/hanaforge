"""Stub HANA extract — deterministic CSV for development without a live database."""

from __future__ import annotations

import csv
import io
from typing import Any

from infrastructure.adapters.hana_sql_identifiers import assert_safe_identifier


class StubHanaExtractAdapter:
    """Produces synthetic CSV rows so the HANA → BQ path can be exercised locally."""

    async def test_connection(self, connection_params: dict[str, Any]) -> bool:
        _ = connection_params
        return True

    async def extract_table_to_csv(
        self,
        connection_params: dict[str, Any],
        schema: str,
        table: str,
        *,
        limit_rows: int | None = None,
    ) -> tuple[bytes, int]:
        _ = connection_params
        assert_safe_identifier(schema, label="schema")
        assert_safe_identifier(table, label="table")

        max_rows = limit_rows if limit_rows is not None else 10
        max_rows = min(max_rows, 10_000)

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "source_schema", "source_table", "payload"])
        for i in range(max_rows):
            writer.writerow([i, schema, table, f"stub-row-{i}"])
        data = buf.getvalue().encode("utf-8")
        return data, max_rows
