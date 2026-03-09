"""RISE with SAP routes — integration endpoints for SAP RISE managed systems."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from application.commands.run_readiness_check import (
    ReadinessCheckResponse,
    RunReadinessCheckUseCase,
)
from domain.ports.rise_ports import RISEConnectorPort
from domain.value_objects.rise_types import (
    RISEConnection,
    RISEConnectionMode,
    RISESystemType,
)
from presentation.api.middleware.auth import get_current_user

router = APIRouter(prefix="", tags=["RISE with SAP"])


# ------------------------------------------------------------------
# Request / response models
# ------------------------------------------------------------------


class RISEConnectRequest(BaseModel):
    """Payload to test a RISE with SAP connection."""

    host: str
    port: int = 443
    client: str = "100"
    user: str
    system_type: str = "S4HANA_ON_PREMISE"
    mode: str = "ODATA"


class RISEConnectResponse(BaseModel):
    """Result of a RISE connection test."""

    connected: bool
    system_id: str
    version: str
    db_type: str
    db_size_gb: float
    num_users: int
    kernel_version: str
    unicode_enabled: bool


class TransportResponse(BaseModel):
    """Serialised transport request."""

    id: str
    description: str
    owner: str
    status: str
    created_at: str
    objects: list[str]


class TransportListResponse(BaseModel):
    """List of transport requests."""

    programme_id: str
    transports: list[TransportResponse]
    total: int


class ReadinessCheckRequest(BaseModel):
    """Payload to trigger a RISE readiness check."""

    host: str
    port: int = 443
    client: str = "100"
    user: str
    system_type: str = "S4HANA_ON_PREMISE"
    mode: str = "ODATA"


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.post(
    "/connect",
    response_model=RISEConnectResponse,
    status_code=status.HTTP_200_OK,
    summary="Test RISE with SAP connection",
)
async def connect(
    body: RISEConnectRequest,
    request: Request,
    _user=Depends(get_current_user),
) -> RISEConnectResponse:
    """Test connectivity to a RISE with SAP managed system and retrieve system info."""
    container = request.app.state.container
    connector: RISEConnectorPort = container.resolve(RISEConnectorPort)

    connection = RISEConnection(
        host=body.host,
        port=body.port,
        client=body.client,
        user=body.user,
        system_type=RISESystemType(body.system_type),
        mode=RISEConnectionMode(body.mode),
    )

    try:
        info = await connector.get_system_info(connection)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to SAP system: {exc}",
        ) from exc

    return RISEConnectResponse(
        connected=True,
        system_id=info.system_id,
        version=info.version,
        db_type=info.db_type,
        db_size_gb=info.db_size_gb,
        num_users=info.num_users,
        kernel_version=info.kernel_version,
        unicode_enabled=info.unicode_enabled,
    )


@router.get(
    "/programmes/{programme_id}/system-info",
    response_model=RISEConnectResponse,
    summary="Get SAP system info for a programme",
)
async def get_system_info(
    programme_id: str,
    request: Request,
    host: str = "",
    port: int = 443,
    client: str = "100",
    user: str = "SAPUSER",
    system_type: str = "S4HANA_ON_PREMISE",
    mode: str = "ODATA",
    _user=Depends(get_current_user),
) -> RISEConnectResponse:
    """Retrieve SAP system metadata for a given programme via RISE integration."""
    container = request.app.state.container
    connector: RISEConnectorPort = container.resolve(RISEConnectorPort)

    if not host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="host query parameter is required",
        )

    connection = RISEConnection(
        host=host,
        port=port,
        client=client,
        user=user,
        system_type=RISESystemType(system_type),
        mode=RISEConnectionMode(mode),
    )

    info = await connector.get_system_info(connection)

    return RISEConnectResponse(
        connected=True,
        system_id=info.system_id,
        version=info.version,
        db_type=info.db_type,
        db_size_gb=info.db_size_gb,
        num_users=info.num_users,
        kernel_version=info.kernel_version,
        unicode_enabled=info.unicode_enabled,
    )


@router.get(
    "/programmes/{programme_id}/transports",
    response_model=TransportListResponse,
    summary="List transports for a programme",
)
async def list_transports(
    programme_id: str,
    request: Request,
    host: str = "",
    port: int = 443,
    client: str = "100",
    user: str = "SAPUSER",
    system_type: str = "S4HANA_ON_PREMISE",
    mode: str = "ODATA",
    _user=Depends(get_current_user),
) -> TransportListResponse:
    """List SAP transport requests associated with a programme."""
    container = request.app.state.container
    connector: RISEConnectorPort = container.resolve(RISEConnectorPort)

    if not host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="host query parameter is required",
        )

    connection = RISEConnection(
        host=host,
        port=port,
        client=client,
        user=user,
        system_type=RISESystemType(system_type),
        mode=RISEConnectionMode(mode),
    )

    transports = await connector.get_transport_list(connection)

    return TransportListResponse(
        programme_id=programme_id,
        transports=[
            TransportResponse(
                id=t.id,
                description=t.description,
                owner=t.owner,
                status=t.status.value,
                created_at=t.created_at.isoformat(),
                objects=list(t.objects),
            )
            for t in transports
        ],
        total=len(transports),
    )


@router.post(
    "/programmes/{programme_id}/readiness-check",
    response_model=ReadinessCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run RISE readiness check",
)
async def run_readiness_check(
    programme_id: str,
    body: ReadinessCheckRequest,
    request: Request,
    _user=Depends(get_current_user),
) -> ReadinessCheckResponse:
    """Execute a RISE readiness check against the source SAP system."""
    container = request.app.state.container
    use_case: RunReadinessCheckUseCase = container.resolve(RunReadinessCheckUseCase)

    try:
        return await use_case.execute(
            programme_id=programme_id,
            host=body.host,
            port=body.port,
            client=body.client,
            user=body.user,
            system_type=body.system_type,
            mode=body.mode,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
