from service.schemas.base import CamelModel


class TrackRequest(CamelModel):
    request_id: str
    org_id: str
    container_ids: list[str]


class TrackResponse(CamelModel):
    status: str
    org_id: str
    feature: str
    requested: int
    succeeded_container_ids: list[str]
    failed_container_ids: list[str]
    units_refunded: int
    remaining: int


class InsufficientQuotaResponse(CamelModel):
    status: str
    org_id: str
    feature: str
    requested: int
    remaining: int
    limit: int
    resets_at: str


class ConflictResponse(CamelModel):
    status: str
    request_id: str
    reason: str
