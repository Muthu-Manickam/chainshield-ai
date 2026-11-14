from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from app.assistant import chat, investigation, rules, schemas
from app.core.auth import AdminUser, CurrentUser, SupervisorUser
from app.core.db import DB

router = APIRouter(prefix="/api")
SSE = "text/event-stream"


@router.get("/investigations", response_model=list[schemas.Investigation])
def list_investigations(db: DB, _: CurrentUser):
    return investigation.list_investigations(db)


@router.post("/investigations", response_model=schemas.Investigation)
def start_investigation(data: schemas.InvestigationIn, background: BackgroundTasks, db: DB, user: CurrentUser):
    return investigation.start(db, background, data.incident_id, data.scope, user)


@router.get("/investigations/stats")
def investigation_stats(db: DB, _: CurrentUser):
    return investigation.investigation_stats(db)


@router.get("/investigations/{investigation_id}", response_model=schemas.InvestigationDetail)
def get_investigation(investigation_id: int, db: DB, _: CurrentUser):
    detail = investigation.get_investigation(db, investigation_id)
    if not detail:
        raise HTTPException(404, "Investigation not found")
    return detail


@router.get("/investigations/{investigation_id}/stream")
def stream_investigation(investigation_id: int, _: CurrentUser):
    return StreamingResponse(investigation.stream_steps(investigation_id), media_type=SSE)


@router.post("/investigations/{investigation_id}/actions/{action_id}/decision", response_model=schemas.Action)
def decide(investigation_id: int, action_id: int, data: schemas.DecisionIn, background: BackgroundTasks, db: DB,
           user: SupervisorUser):
    action = investigation.decide(db, investigation_id, action_id, data.decision, user, background)
    if not action:
        raise HTTPException(404, "Action not found")
    return action


@router.post("/chat")
def send_chat(data: schemas.ChatIn, db: DB, user: CurrentUser):
    return StreamingResponse(chat.answer(db, user, data.session_id, data.message), media_type=SSE)


@router.get("/chat/{session_id}", response_model=list[schemas.ChatMessage])
def chat_history(session_id: str, db: DB, _: CurrentUser):
    return chat.history(db, session_id)


@router.get("/rules", response_model=list[schemas.ActionRule])
def list_rules(db: DB, _: CurrentUser):
    return rules.list_rules(db)


@router.put("/rules/{rule_id}", response_model=schemas.ActionRule)
def update_rule(rule_id: int, data: schemas.RuleUpdate, db: DB, admin: AdminUser):
    rule = rules.update_rule(db, rule_id, data, admin)
    if not rule:
        raise HTTPException(404, "Rule not found")
    return rule
