"""Tests for HANA → BigQuery value objects."""

from __future__ import annotations

import pytest

from domain.value_objects.hana_bq_types import TableMapping


class TestTableMapping:
    def test_valid_mapping(self) -> None:
        m = TableMapping(
            source_schema="SAPHANADB",
            source_table="MYTABLE",
            target_dataset="landing",
            target_table="mytable",
        )
        assert m.incremental_column is None

    def test_rejects_empty_schema(self) -> None:
        with pytest.raises(ValueError, match="source_schema must be non-empty"):
            TableMapping(
                source_schema="",
                source_table="T",
                target_dataset="d",
                target_table="t",
            )

    def test_rejects_blank_incremental(self) -> None:
        with pytest.raises(ValueError, match="incremental_column, if set"):
            TableMapping(
                source_schema="S",
                source_table="T",
                target_dataset="d",
                target_table="t",
                incremental_column="   ",
            )
