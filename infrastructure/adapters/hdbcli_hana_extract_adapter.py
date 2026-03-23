"""SAP HANA extraction via hdbcli (optional dependency)."""

from __future__ import annotations

import csv
import importlib
import importlib.util
import io
from typing import Any

from infrastructure.adapters.hana_sql_identifiers import assert_safe_identifier


def _load_hdbcli_dbapi() -> Any:
    if importlib.util.find_spec("hdbcli.dbapi") is None:
        raise RuntimeError(
            "hdbcli is not installed. Install the 'hana' extra: pip install 'hanaforge[hana]'"
        )
    return importlib.import_module("hdbcli.dbapi")


class HdbcliHanaExtractAdapter:
    """Connects to SAP HANA and exports a single table as UTF-8 CSV."""

    def __init__(self, default_port: int = 443) -> None:
        self._default_port = default_port

    async def test_connection(self, connection_params: dict[str, Any]) -> bool:
        try:
            _load_hdbcli_dbapi()
            conn = self._connect(connection_params)
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM DUMMY")
            cur.fetchone()
            cur.close()
            conn.close()
            return True
        except Exception:
            return False

    async def extract_table_to_csv(
        self,
        connection_params: dict[str, Any],
        schema: str,
        table: str,
        *,
        limit_rows: int | None = None,
    ) -> tuple[bytes, int]:
        assert_safe_identifier(schema, label="schema")
        assert_safe_identifier(table, label="table")

        _load_hdbcli_dbapi()
        conn = self._connect(connection_params)
        try:
            cur = conn.cursor()
            qualified = f'"{schema.upper()}"."{table.upper()}"'
            sql = f"SELECT * FROM {qualified}"
            if limit_rows is not None:
                sql = f"SELECT * FROM {qualified} LIMIT {int(limit_rows)}"
            cur.execute(sql)
            rows = cur.fetchall()
            colnames = [d[0] for d in cur.description] if cur.description else []
            buf = io.StringIO()
            writer = csv.writer(buf)
            if colnames:
                writer.writerow(colnames)
            for row in rows:
                writer.writerow(list(row))
            data = buf.getvalue().encode("utf-8")
            return data, len(rows)
        finally:
            conn.close()

    def _connect(self, p: dict[str, Any]) -> Any:
        dbapi = _load_hdbcli_dbapi()

        address = p.get("address") or p.get("host")
        if not address:
            raise ValueError("hana connection requires 'address' or 'host'")
        port = int(p.get("port", self._default_port))
        user = p.get("user")
        password = p.get("password")
        if not user or password is None:
            raise ValueError("hana connection requires 'user' and 'password'")
        return dbapi.connect(
            address=address,
            port=port,
            user=user,
            password=password,
        )
