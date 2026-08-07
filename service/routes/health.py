from fastapi import APIRouter

from service.controllers import health_controller
from service.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return health_controller.get_health()
