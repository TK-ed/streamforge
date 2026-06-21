import os
import time
from contextlib import asynccontextmanager
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest, make_asgi_app
from starlette.responses import Response

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.videos import router as videos_router
from app.core.rate_limit import close_rate_limiter, init_rate_limiter
from app.services.minio_service import create_bucket
from services.api_gateway.app.core.instrumentation import setup_tracing
from services.api_gateway.app.core.observability import setup_logging

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

    init_rate_limiter()

    yield

    await close_rate_limiter()


app = FastAPI(title="StreamForge", lifespan=lifespan)

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

# Logs -> OTel Collector -> Loki ; Traces -> OTel Collector -> Jaeger
setup_logging()
setup_tracing(app)


@lru_cache
def get_settings():
    return config.Settings()


app.mount("/metrics", make_asgi_app())


@app.get("/")
def health():
    return {"status": "healthy", "rabbit_mq": os.getenv("RABBITMQ_HOST")}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
