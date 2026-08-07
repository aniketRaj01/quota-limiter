from contextlib import asynccontextmanager

from fastapi import FastAPI

from service.db import connection as db_connection
from service.db.schema import init_schema
from service.db.seed import seed_data
from service.routes.health import router as health_router
from service.routes.org import router as org_router
from service.routes.quota import router as quota_router
from service.routes.track import router as track_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = db_connection.init_connection()
    init_schema(conn)
    seed_data(conn)
    yield
    db_connection.close_connection()


app = FastAPI(title="Quota Limiter", lifespan=lifespan)

app.include_router(health_router)
app.include_router(org_router)
app.include_router(quota_router)
app.include_router(track_router)
