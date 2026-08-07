from service.schemas.base import CamelModel


class OrgQuotaConfigRequest(CamelModel):
    feature: str
    limit: int


class CreateOrgRequest(CamelModel):
    quotas: list[OrgQuotaConfigRequest]


class QuotaStatus(CamelModel):
    feature: str
    limit: int
    used: int
    period_start: str
    resets_at: str


class CreateOrgResponse(CamelModel):
    org_id: str
    anchor_day: int
    quotas: list[QuotaStatus]


class OrgSummary(CamelModel):
    org_id: str
    resets_at: str
