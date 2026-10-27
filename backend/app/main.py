"""FastAPI app: routers, CORS and error handlers. Done."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import runs, workflows
from app.core.config import get_settings
from app.errors import CycleError, NotFound

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflows.router)
app.include_router(runs.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(NotImplementedError)
async def not_implemented(_: Request, exc: NotImplementedError):
    # Unfinished TODOs answer 501 and name the file to open next.
    return JSONResponse(status_code=501, content={"detail": f"TODO: {exc}"})


@app.exception_handler(NotFound)
async def not_found(_: Request, exc: NotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(CycleError)
async def cycle(_: Request, exc: CycleError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})
