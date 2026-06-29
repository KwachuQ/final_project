import time

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import UserModel, get_db
from app.schemas import TokenResponse, UserRegister, UserResponse
from app.settings import get_settings

router = APIRouter(prefix="/auth")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    existing = db.query(UserModel).filter(UserModel.username == payload.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    user = UserModel(
        username=payload.username,
        password_hash=pwd_context.hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(user_id=user.id, username=user.username)


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT token."""
    user = db.query(UserModel).filter(UserModel.username == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = jwt.encode(
        {
            "sub": user.id,
            "exp": int(time.time()) + 3600,  # 1 hour
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return TokenResponse(access_token=token, token_type="bearer")