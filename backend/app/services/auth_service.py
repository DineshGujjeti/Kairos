"""
Auth business logic lives here, not in the route handlers. Route
functions (app/api/v1/auth/routes.py) should stay thin: parse request,
call a service function, return response. This split means the auth
logic can be unit-tested without spinning up FastAPI/TestClient at all.
"""
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import TokenType, create_token, hash_password, verify_password
from app.db.models.organization import Organization
from app.db.models.user import User, UserRole
from app.schemas.auth import Token
from app.schemas.user import UserCreate

logger = get_logger(__name__)


class AuthError(Exception):
    pass


def register_user(db: Session, payload: UserCreate) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise AuthError("A user with this email already exists")

    org = db.query(Organization).filter(Organization.name == payload.organization_name).first()
    if org is None:
        org = Organization(name=payload.organization_name)
        db.add(org)
        db.flush()  # assigns org.id without committing yet

    # First user in a brand-new organization is made Admin; this is a
    # deliberate, explainable default rather than requiring a manual
    # DB edit to get the first admin account for a new org.
    role = UserRole.ADMIN if not org.users else UserRole.VIEWER

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=role,
        org_id=org.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("user_registered", user_id=str(user.id), org_id=str(org.id), role=role.value)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthError("Incorrect email or password")
    if not user.is_active:
        raise AuthError("User account is disabled")
    return user


def issue_tokens(user: User) -> Token:
    access = create_token(str(user.id), TokenType.ACCESS, {"role": user.role.value})
    refresh = create_token(str(user.id), TokenType.REFRESH)
    return Token(access_token=access, refresh_token=refresh)
