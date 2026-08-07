from fastapi import FastAPI

from service.routes.health import router as health_router
from service.routes.org import router as org_router
from service.routes.quota import router as quota_router
from service.routes.track import router as track_router

app = FastAPI(title="Quota Limiter")

app.include_router(health_router)
app.include_router(org_router)
app.include_router(quota_router)
app.include_router(track_router)
