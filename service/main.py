from fastapi import FastAPI

from service.routes.health import router as health_router

app = FastAPI(title="Quota Limiter")

app.include_router(health_router)
