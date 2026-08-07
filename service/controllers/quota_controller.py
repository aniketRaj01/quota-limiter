from fastapi import HTTPException

from service.schemas.quota import UsageResponse


def get_usage(org_id: str, feature: str) -> UsageResponse:
    raise HTTPException(status_code=501, detail="Not implemented")
