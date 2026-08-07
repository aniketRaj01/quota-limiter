from __future__ import annotations

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from service.schemas.track import (
    ConflictResponse,
    InsufficientQuotaResponse,
    TrackRequest,
    TrackResponse,
)
from service.services import track as track_service
from service.services.track import TrackStatus


def track_containers(request: TrackRequest) -> TrackResponse | JSONResponse:
    result = track_service.track_containers(request.request_id, request.org_id, request.container_ids)

    if result.status == TrackStatus.NOT_FOUND:
        raise HTTPException(
            status_code=404,
            detail=f"no quota configured for org '{request.org_id}' feature 'container-tracking'",
        )

    if result.status == TrackStatus.CONFLICT:
        body = ConflictResponse(**result.body)
        return JSONResponse(status_code=409, content=body.model_dump(by_alias=True))

    if result.status == TrackStatus.INSUFFICIENT_QUOTA:
        body = InsufficientQuotaResponse(**result.body)
        return JSONResponse(status_code=429, content=body.model_dump(by_alias=True))

    return TrackResponse(**result.body)
