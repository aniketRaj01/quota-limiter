from fastapi import APIRouter, Query

from service.controllers import quota_controller
from service.schemas.quota import UsageResponse

router = APIRouter()


@router.get("/v1/quota/usage", response_model=UsageResponse)
def get_usage(
    org_id: str = Query(alias="orgId"),
    feature: str = Query(),
) -> UsageResponse:
    return quota_controller.get_usage(org_id, feature)
