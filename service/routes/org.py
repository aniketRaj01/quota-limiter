from fastapi import APIRouter

from service.controllers import org_controller
from service.schemas.org import CreateOrgRequest, CreateOrgResponse, OrgSummary

router = APIRouter()


@router.post("/v1/orgs", response_model=CreateOrgResponse, status_code=201)
def create_org(request: CreateOrgRequest) -> CreateOrgResponse:
    return org_controller.create_org(request)


@router.get("/v1/orgs", response_model=list[OrgSummary])
def list_orgs() -> list[OrgSummary]:
    return org_controller.list_orgs()
