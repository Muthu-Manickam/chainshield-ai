from fastapi import APIRouter, HTTPException, Response

from app.core import auth, jobs, schemas
from app.core.auth import AdminUser, CurrentUser
from app.core.db import DB

router = APIRouter(prefix="/api")


@router.post("/auth/login", response_model=schemas.User)
def login(data: schemas.LoginIn, response: Response, db: DB):
    user = auth.login(db, response, data.email, data.password)
    if not user:
        raise HTTPException(401, "Wrong email or password")
    return user


@router.post("/auth/logout", status_code=204)
def logout(response: Response):
    auth.logout(response)


@router.get("/auth/me", response_model=schemas.User)
def me(user: CurrentUser):
    return user


@router.get("/users", response_model=list[schemas.User])
def list_users(db: DB, _: AdminUser):
    return auth.list_users(db)


@router.post("/users", response_model=schemas.User)
def create_user(data: schemas.UserCreate, db: DB, admin: AdminUser):
    try:
        return auth.create_user(db, data, admin)
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@router.get("/users/audit", response_model=list[schemas.AuditEntry])
def list_audit(db: DB, _: AdminUser):
    return auth.list_audit(db)


@router.patch("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, data: schemas.UserUpdate, db: DB, admin: AdminUser):
    user = auth.update_user(db, user_id, data, admin)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.get("/jobs/{job_id}", response_model=schemas.Job)
def get_job(job_id: int, db: DB, _: CurrentUser):
    job = jobs.get_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/evals", response_model=list[schemas.EvalRun])
def list_evals(db: DB, _: CurrentUser, kind: str | None = None):
    return jobs.list_evals(db, kind)
