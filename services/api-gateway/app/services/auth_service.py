from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from fastapi import HTTPException
from sqlalchemy.orm import Session


def create_user(db: Session, user_data: UserCreate):
    existing_user = db.query(User).filter(User.email == user_data.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(email=user_data.email, password_hash=hash_password(user_data.password))

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
