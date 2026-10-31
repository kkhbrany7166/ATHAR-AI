"""FastAPI application. Run: .venv/bin/uvicorn athar.main:app --port 8710"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import professor, student, system
from .config import get_settings
from .db import init_db


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db()
        yield

    app = FastAPI(title="ATHAR API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=list(get_settings().cors_origins), allow_methods=["*"],
                       allow_headers=["*"])
    app.include_router(system.router)
    app.include_router(professor.router)
    app.include_router(student.router)

    return app


app = create_app()
