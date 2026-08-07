from service.schemas.base import CamelModel


class UsageResponse(CamelModel):
    org_id: str
    feature: str
    limit: int
    used: int
    remaining: int
    period_start: str
    resets_at: str
