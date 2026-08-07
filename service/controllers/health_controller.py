from service.schemas.health import HealthResponse
from service.services import health_service


def get_health() -> HealthResponse:
    return HealthResponse(**health_service.get_status())
