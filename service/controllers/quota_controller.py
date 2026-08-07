from fastapi import HTTPException

from service.schemas.quota import UsageResponse
from service.services import quota as quota_service
from service.services.period import next_reset_at
from service.services.quota import UsageStatus


def get_usage(org_id: str, feature: str) -> UsageResponse:
    result = quota_service.get_usage(org_id, feature)

    if result.status == UsageStatus.NOT_FOUND:
        raise HTTPException(
            status_code=404,
            detail=f"no quota configured for org '{org_id}' feature '{feature}'",
        )

    return UsageResponse(
        org_id=org_id,
        feature=feature,
        limit=result.limit,
        used=result.used,
        remaining=result.limit - result.used,
        period_start=result.period_start.isoformat(),
        resets_at=next_reset_at(result.period_start, result.anchor_day),
    )
