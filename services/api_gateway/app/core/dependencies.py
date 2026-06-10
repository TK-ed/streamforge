from app.config import settings
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from shared.db.db import get_db
from shared.models.user import User

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
security = HTTPBearer()
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM


def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    print("TOKEN:", token)

    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])

        print("PAYLOAD:", payload)

        user_id = payload.get("sub")

        print("USER_ID:", user_id)

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except JWTError as e:
        print("JWT ERROR:", e)
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == int(user_id)).first()

    print("USER:", user)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
