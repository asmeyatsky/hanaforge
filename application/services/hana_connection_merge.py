"""Merge request-body HANA overrides with HANAFORGE_* defaults."""

from __future__ import annotations

from typing import Any

from application.dtos.hana_bq_dto import HanaConnectionParams
from infrastructure.config.settings import Settings


def merge_hana_connection_params(settings: Settings, body: HanaConnectionParams | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if body is not None:
        if body.address:
            out["address"] = body.address
        elif body.host:
            out["address"] = body.host
        if body.port is not None:
            out["port"] = body.port
        if body.user is not None:
            out["user"] = body.user
        if body.password is not None:
            out["password"] = body.password
    if "address" not in out and settings.hana_address:
        out["address"] = settings.hana_address
    if "port" not in out:
        out["port"] = settings.hana_port
    if "user" not in out and settings.hana_user:
        out["user"] = settings.hana_user
    if "password" not in out and settings.hana_password:
        out["password"] = settings.hana_password
    return out
