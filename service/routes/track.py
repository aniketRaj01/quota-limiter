from fastapi import APIRouter

from service.controllers import track_controller
from service.schemas.track import TrackRequest, TrackResponse

router = APIRouter()


@router.post("/v1/features/container-tracking/track", response_model=TrackResponse)
def track_containers(request: TrackRequest) -> TrackResponse:
    return track_controller.track_containers(request)
