from fastapi import HTTPException

from service.schemas.org import CreateOrgRequest, CreateOrgResponse, OrgSummary


def create_org(request: CreateOrgRequest) -> CreateOrgResponse:
    raise HTTPException(status_code=501, detail="Not implemented")


def list_orgs() -> list[OrgSummary]:
    raise HTTPException(status_code=501, detail="Not implemented")
