from fastapi import HTTPException

from service.schemas.org import CreateOrgRequest, CreateOrgResponse, OrgSummary
from service.services import org_service


def create_org(request: CreateOrgRequest) -> CreateOrgResponse:
    raise HTTPException(status_code=501, detail="Not implemented")


def list_orgs() -> list[OrgSummary]:
    return [OrgSummary(**org) for org in org_service.list_orgs()]
