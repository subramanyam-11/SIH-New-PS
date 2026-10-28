from datetime import datetime
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine
from contextlib import asynccontextmanager
from app.api.v1.auth import router as auth_router
from app.api.v1.config import router as config_router
from app.api.v1.lookup import router as lookup_router
from app.api.v1.applications import router as applications_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.files import router as files_router
from app.api.v1.evc import router as evc_router
from app.api.v1.undertakings import router as undertakings_router
from app.api.v1.documents import router as documents_router
from app.api.v1.reports import router as reports_router
from app.api.v1.committee import router as committee_router
from app.api.v1.holidays import router as holidays_router
from app.services.scheduler import start_scheduler, stop_scheduler
from app.schemas import HealthCheckResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch background scheduler
    start_scheduler()
    yield
    # Shutdown: Stop scheduler
    stop_scheduler()


app = FastAPI(
    title="AICTE Approval Workflow Automation API",
    description="Backend services for SIH26262: Integrated AICTE Approval Workflow, Compliance Monitoring and Alert Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
def health_check():
    db_status = "healthy"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return HealthCheckResponse(
        status="ok" if db_status == "healthy" else "degraded",
        database=db_status,
        environment=settings.ENVIRONMENT,
        demo_mode=settings.DEMO_MODE,
        timestamp=datetime.utcnow()
    )


# Standard Error Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# API Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(config_router, prefix="/api/v1")
app.include_router(lookup_router, prefix="/api/v1")
app.include_router(applications_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(evc_router, prefix="/api/v1")
app.include_router(undertakings_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(committee_router, prefix="/api/v1")
app.include_router(holidays_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
