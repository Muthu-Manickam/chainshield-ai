from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.assistant.router import router as assistant_router
from app.core.router import router as core_router
from app.knowledge.router import router as knowledge_router
from app.signals.router import router as signals_router

app = FastAPI(title="ChainShield AI")
for router in (core_router, signals_router, knowledge_router, assistant_router):
    app.include_router(router)


@app.exception_handler(ValueError)
def bad_input(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=400)
