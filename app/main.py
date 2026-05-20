from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import calendar, copilot, documents, health
from app.core.config import settings

app = FastAPI(
    title="Academic Context API",
    description=(
        "Data and tool layer for the Microsoft Copilot Studio Academic Planning Agent. "
        "Copilot Studio is the brain; this API serves structured context and executes approved actions."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(copilot.router, prefix="/copilot", tags=["Copilot"])
app.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])


@app.get("/")
def root():
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }
