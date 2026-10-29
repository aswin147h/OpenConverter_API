from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as jobs_router

app = FastAPI(
    title="OpenConvert API",
    version="0.1.0",
    description="Privacy-first conversion API for images and PDFs.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)


@app.get("/")
def root():
    return {"name": "OpenConvert API", "status": "ok"}
