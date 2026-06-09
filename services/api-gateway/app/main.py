import os
import time
from contextlib import asynccontextmanager
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.db.database import Base, engine

from . import config

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):

    for _ in range(15):
        try:
            Base.metadata.create_all(bind=engine)
            print("Database connected")
            break
        except Exception as e:
            print(f"Waiting for database: {e}")
            time.sleep(2)

    yield


app = FastAPI(title="StreamForge", lifespan=lifespan)


app.include_router(auth_router)
app.include_router(users_router)


@lru_cache
def get_settings():
    return config.Settings()


@app.get("/")
def health():
    return {"status": "healthy", "rabbit_mq": os.getenv("RABBITMQ_HOST")}
