"""Validate HANA SQL identifiers to reduce injection risk."""

from __future__ import annotations

import re

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def assert_safe_identifier(name: str, *, label: str) -> str:
    if not _IDENTIFIER.match(name):
        raise ValueError(f"Invalid {label} {name!r}: use letters, digits, underscore only")
    return name
