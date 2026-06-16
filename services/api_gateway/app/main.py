import os
import time
from contextlib import asynccontextmanager
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.middleware import SlowAPIMiddleware

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.videos import router as videos_router
from app.services.minio_service import create_bucket
from services.api_gateway.app.core.middleware import limiter

from . import config

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):

    for _ in range(15):
        try:
            # Base.metadata.create_all(bind=engine)
            create_bucket()
            print("MinIO bucket ready")
            print("Database connected")
            break
        except Exception as e:
            print(f"Waiting for database: {e}")
            time.sleep(2)

    yield


app = FastAPI(title="StreamForge", lifespan=lifespan)

instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
).instrument(app)

instrumentator.expose(
    app,
    endpoint="/metrics",
    include_in_schema=False,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourfrontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(videos_router)

# @app.on_event("startup")
# async def _startup():
#     instrumentator.expose(app, endpoint="/metrics")


@lru_cache
def get_settings():
    return config.Settings()


@app.get("/")
def health():
    return {"status": "healthy", "rabbit_mq": os.getenv("RABBITMQ_HOST")}
