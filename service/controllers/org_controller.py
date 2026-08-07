from fastapi import HTTPException

from service.schemas.org import CreateOrgRequest, CreateOrgResponse, OrgSummary
from service.services import org_service


def create_org(request: CreateOrgRequest) -> CreateOrgResponse:
    quota_configs = [(q.feature.value, q.limit) for q in request.quotas]
    try:
        result = org_service.create_org(quota_configs)
    except org_service.DuplicateOrgError as exc:
        raise HTTPException(
            status_code=409, detail=f"orgId '{exc}' already exists"
        ) from exc
    return CreateOrgResponse(**result)


def list_orgs() -> list[OrgSummary]:
    return [OrgSummary(**org) for org in org_service.list_orgs()]
