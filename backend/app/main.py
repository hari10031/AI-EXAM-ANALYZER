from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401 — ensure models are registered before create_all
from .config import get_settings
from .db import Base, engine, ensure_phase03_columns
from .routes import router
from .routes_analysis import router as analysis_router
from .routes_predict import router as predict_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_phase03_columns(engine)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AI Exam Paper Predictor",
    description="Phases 02–04 — ingestion, analysis & prediction. See Implementations/Implmentation-01.md.",
    version="0.4.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin
        for origin in [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            get_settings().frontend_url,
        ]
        if origin
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(analysis_router)
app.include_router(predict_router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
