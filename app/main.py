from fastapi import FastAPI

from app.modules.auth.router import router as auth_router
from app.modules.onboarding.router import router as onboarding_router
from app.modules.jobs.router import router as jobs_router
from app.modules.matching.router import router as matching_router
from app.modules.interviews.router import router as interviews_router


app = FastAPI(
    title="AI Recruitment Platform",
    version="1.0.0",
    description="AI-powered recruitment platform with authentication, onboarding, job intelligence, matching, and structured interviews.",
)


app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(jobs_router)
app.include_router(matching_router)
app.include_router(interviews_router)


@app.get("/")
def root():
    return {
        "message": "AI Recruitment Platform API is running",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }