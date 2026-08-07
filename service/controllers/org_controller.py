from fastapi import HTTPException

from service.schemas.org import CreateOrgRequest, CreateOrgResponse


def create_org(request: CreateOrgRequest) -> CreateOrgResponse:
    raise HTTPException(status_code=501, detail="Not implemented")
