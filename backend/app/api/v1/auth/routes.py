from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import TokenType, create_token, decode_token
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import Token, TokenRefreshRequest
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import AuthError, authenticate_user, issue_tokens, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return register_user(db, payload)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm is the standard FastAPI convention for
    # login endpoints -- it also makes the Swagger "Authorize" button
    # work out of the box, which is worth the minor payload-shape quirk.
    try:
        user = authenticate_user(db, form_data.username, form_data.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    return issue_tokens(user)


@router.post("/refresh", response_model=Token)
def refresh(payload: TokenRefreshRequest, db: Session = Depends(get_db)):
    claims = decode_token(payload.refresh_token)
    if claims is None or claims.get("type") != TokenType.REFRESH.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    import uuid

    user = db.get(User, uuid.UUID(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer valid")

    return issue_tokens(user)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
