from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading
import time
from contextlib import asynccontextmanager

from app.api.routes import router as jobs_router
from app import config
from app.storage.job_store import cleanup as cleanup_jobs
from app.storage.job_store import initialize as initialize_job_store


def _cleanup_loop() -> None:
    while True:
        cleanup_jobs(config.RETENTION_SECONDS)
        time.sleep(300)


@asynccontextmanager
async def lifespan(application: FastAPI):
    initialize_job_store()
    cleanup_jobs(config.RETENTION_SECONDS)
    threading.Thread(target=_cleanup_loop, daemon=True).start()
    yield


app = FastAPI(
    title="OpenConvert API",
    version="0.1.0",
    description="Privacy-first conversion API for images and PDFs.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)

@app.get("/")
def root():
    return {"name": "OpenConvert API", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}
