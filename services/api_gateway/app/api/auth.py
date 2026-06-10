from app.core.security import create_access_token, verify_password
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.auth_service import create_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from services.api_gateway.app.services.minio_service import client
from shared.db.db import get_db
from shared.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user)


@router.get("/get")
async def get_video():
    # object_name = "uploads/60419178-dcb9-48ec-83a1-493487df7630/input.mp4"

    # destination_path = "/tmp/1/input.mp4"
    # os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    # bucket_name = "streamforge"

    # try:
    #     # 1. Check bucket
    #     if not client.bucket_exists(bucket_name):
    #         raise HTTPException(status_code=404, detail="Bucket does not exist")

    #     # 2. Check object exists (IMPORTANT for debugging)
    #     client.stat_object(bucket_name, object_name)

    #     # 3. Download file
    #     client.fget_object(bucket_name, object_name, destination_path)

    #     return {"message": "Download successful", "downloaded_to": destination_path}

    # except S3Error as e:
    #     raise HTTPException(status_code=404, detail=f"MinIO error: {str(e)}")

    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))

    # file = client.get_object(
    #     Bucket="streamforge",
    #     Key="uploads/60419178-dcb9-48ec-83a1-493487df7630/input.mp4",
    # )

    file = client.fget_object(
        bucket_name="streamforge",
        object_name="WIN_20251222_13_55_03_Pro.mp4",
        file_path="/tmp/input.mp4",
    )
    return file


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(db_user.id)})

    return {"access_token": token, "token_type": "bearer"}
