from fastapi import APIRouter, Depends, Header

from app.core.dependencies import get_current_user, security
from shared.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}


@router.get("/test")
def test(authorization: str = Header(None)):
    return {"auth": authorization}


@router.get("/debug-token")
def debug_token(token: str = Depends(security)):
    return {"token": token}
