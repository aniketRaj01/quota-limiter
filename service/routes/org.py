from fastapi import APIRouter

from service.controllers import org_controller
from service.schemas.org import CreateOrgRequest, CreateOrgResponse

router = APIRouter()


@router.post("/v1/orgs", response_model=CreateOrgResponse, status_code=201)
def create_org(request: CreateOrgRequest) -> CreateOrgResponse:
    return org_controller.create_org(request)
