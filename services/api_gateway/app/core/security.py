from datetime import datetime, timedelta

from app.config import settings
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM


def hash_password(password: str):
    print(password)
    print(len(password))
    print(pwd_context.hash(password))

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    payload = data.copy()

    payload["exp"] = datetime.utcnow() + timedelta(hours=24)

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
