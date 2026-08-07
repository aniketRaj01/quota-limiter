from fastapi import HTTPException

from service.schemas.track import TrackRequest, TrackResponse


def track_containers(request: TrackRequest) -> TrackResponse:
    raise HTTPException(status_code=501, detail="Not implemented")
