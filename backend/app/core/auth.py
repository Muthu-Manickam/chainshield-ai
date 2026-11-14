from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, Response
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import DB
from app.core.models import AuditLog, User
from app.core.schemas import UserCreate, UserUpdate

COOKIE = "cs_session"
SESSION_HOURS = 12
hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return hasher.verify(password, password_hash)


def login(db: Session, response: Response, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return None
    expires = datetime.now(UTC) + timedelta(hours=SESSION_HOURS)
    token = jwt.encode({"sub": str(user.id), "exp": expires}, settings.jwt_secret, algorithm="HS256")
    response.set_cookie(COOKIE, token, max_age=SESSION_HOURS * 3600, httponly=True, samesite="lax")
    return user


def logout(response: Response) -> None:
    response.delete_cookie(COOKIE)


def current_user(db: DB, token: Annotated[str | None, Cookie(alias=COOKIE)] = None) -> User:
    try:
        user_id = int(jwt.decode(token or "", settings.jwt_secret, algorithms=["HS256"])["sub"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Not logged in")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "Not logged in")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_role(*roles: str):
    def check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Not allowed for your role")
        return user

    return Depends(check)


AdminUser = Annotated[User, require_role("admin")]
SupervisorUser = Annotated[User, require_role("supervisor", "admin")]


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


def create_user(db: Session, data: UserCreate, actor: User | None) -> User:
    if db.scalar(select(User).where(User.email == data.email)):
        raise ValueError("Email already registered")
    user = User(email=data.email, password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    db.flush()
    record_audit(db, actor, "create", "user", user.id, {"email": user.email, "role": user.role})
    db.commit()
    return user


def update_user(db: Session, user_id: int, data: UserUpdate, actor: User) -> User | None:
    user = db.get(User, user_id)
    if not user:
        return None
    changes = data.model_dump(exclude_none=True)
    if "password" in changes:
        user.password_hash = hash_password(changes.pop("password"))
    for field, value in changes.items():
        setattr(user, field, value)
    record_audit(db, actor, "update", "user", user.id, changes)
    db.commit()
    return user


def record_audit(db: Session, user: User | None, action: str, entity: str, entity_id, detail: dict | None = None):
    """Adds the audit row to the caller's transaction; the caller commits."""
    db.add(AuditLog(user_id=user.id if user else None, action=action, entity=entity,
                    entity_id=None if entity_id is None else str(entity_id), detail=detail))


def list_audit(db: Session, limit: int = 200) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)))
