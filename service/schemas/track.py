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
