from fastapi import FastAPI

from app.config import settings
from app.routers import resume, job, match

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.include_router(resume.router, prefix="/api/v1")
app.include_router(job.router, prefix="/api/v1")
app.include_router(match.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"project": settings.PROJECT_NAME, "version": settings.VERSION}
