from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Form, UploadFile

from app.core import jobs
from app.core import schemas as core_schemas
from app.core.auth import CurrentUser, require_role
from app.core.config import settings
from app.core.db import DB
from app.knowledge import ingest, schemas, search

router = APIRouter(prefix="/api/knowledge")


@router.get("/search", response_model=schemas.SearchResult)
def search_guidance(q: str, db: DB, _: CurrentUser):
    return search.search(db, q)


@router.get("/documents", response_model=list[schemas.Document])
def list_documents(db: DB, _: CurrentUser):
    return search.list_documents(db)


@router.post("/documents", response_model=core_schemas.Job, dependencies=[require_role("admin")])
def upload_document(file: UploadFile, code: Annotated[str, Form()], title: Annotated[str, Form()],
                    origin: Annotated[str, Form()], background: BackgroundTasks, db: DB):
    path = settings.data_dir / "uploads" / Path(file.filename or code).name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(file.file.read())
    return jobs.start_job(db, background, "ingest", ingest.ingest_file, path, code, title, origin)

