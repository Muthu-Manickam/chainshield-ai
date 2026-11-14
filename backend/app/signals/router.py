from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.core import schemas as core_schemas
from app.core.auth import AdminUser, CurrentUser
from app.core.db import DB
from app.signals import incidents, orders, registry, schemas

router = APIRouter(prefix="/api")


@router.get("/orders", response_model=core_schemas.Page[schemas.OrderRow])
def search_orders(filters: Annotated[schemas.OrderFilter, Query()], db: DB, _: CurrentUser,
                  page: int = 1, page_size: int = 50):
    rows, total = orders.search_orders(db, filters, page, page_size)
    return {"items": rows, "total": total}


@router.get("/orders/stats", response_model=schemas.OrderStats)
def order_stats(db: DB, _: CurrentUser):
    return orders.order_stats(db)


@router.get("/orders/{order_id}", response_model=schemas.OrderDetail)
def get_order(order_id: int, db: DB, _: CurrentUser):
    order = orders.get_order(db, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.get("/incidents", response_model=core_schemas.Page[schemas.Incident])
def search_incidents(db: DB, _: CurrentUser, status: str | None = None, label: str | None = None, page: int = 1):
    rows, total = incidents.search_incidents(db, status, label, page)
    return {"items": rows, "total": total}


@router.post("/incidents", response_model=schemas.Incident)
def add_incident(data: schemas.IncidentIn, db: DB, user: CurrentUser):
    try:
        return incidents.add_manual(db, data.text, user)
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@router.post("/incidents/release", response_model=list[schemas.Incident])
def release_incidents(data: schemas.ReleaseIn, db: DB, _: CurrentUser):
    return incidents.release(db, data.count)


@router.post("/incidents/release-gold")
def release_gold(db: DB, admin: AdminUser):
    return {"reviewed": incidents.release_gold(db, admin)}


@router.get("/incidents/stats", response_model=schemas.IncidentStats)
def incident_stats(db: DB, _: CurrentUser):
    return incidents.incident_stats(db)


@router.post("/incidents/{incident_id}/review", response_model=schemas.Incident)
def review_incident(incident_id: int, data: schemas.ReviewIn, db: DB, user: CurrentUser):
    try:
        incident = incidents.review(db, incident_id, data.label, user)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not incident:
        raise HTTPException(404, "Incident not found")
    return incident


@router.get("/models", response_model=list[schemas.ModelVersion])
def list_models(db: DB, _: CurrentUser, task: str | None = None):
    return registry.list_versions(db, task)


@router.post("/models/release-batch")
def release_batch(data: schemas.ReleaseBatchIn, db: DB, admin: AdminUser):
    return {"released": registry.release_batch(db, data.block, admin)}


@router.post("/models/retrain", response_model=core_schemas.Job)
def retrain(data: schemas.RetrainIn, background: BackgroundTasks, db: DB, admin: AdminUser):
    return registry.start_retrain(db, background, data.task, data.family, admin)


@router.post("/models/{version_id}/promote", response_model=schemas.ModelVersion)
def promote(version_id: int, background: BackgroundTasks, db: DB, admin: AdminUser):
    version = registry.promote(db, version_id, admin, background)
    if not version:
        raise HTTPException(404, "Model version not found")
    return version
