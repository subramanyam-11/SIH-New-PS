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
from app.api.v1.risk import router as risk_router
from app.api.v1.bottlenecks import router as bottlenecks_router
from app.api.v1.planner import router as planner_router
from app.api.v1.audit import router as audit_router
from app.api.v1.retention import router as retention_router
from app.api.v1.integration import router as integration_router
from app.services.scheduler import start_scheduler, stop_scheduler
from app.schemas import HealthCheckResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Security Auditing and Warning
    if settings.DEMO_MODE:
        print("\n" + "=" * 70)
        print("WARNING: DEMO_MODE is active (DEMO_MODE=True).")
        print("Demo login personas and fast-switch chips are enabled.")
        print("For production deployments, set DEMO_MODE=False.")
        print("=" * 70 + "\n")

    if "change-in-production" in settings.JWT_SECRET or len(settings.JWT_SECRET) < 32:
        print("\n" + "!" * 70)
        print("CRITICAL SECURITY NOTICE: JWT_SECRET appears to be default or insecure.")
        print("Generate a cryptographically secure 256-bit secret for production.")
        print("!" * 70 + "\n")

    # Startup: Launch background scheduler
    start_scheduler()
    yield
    # Shutdown: Stop scheduler
    stop_scheduler()


def create_app() -> FastAPI:
    application = FastAPI(
        title="AICTE Approval Workflow Automation API",
        description="Backend services for SIH26262: Integrated AICTE Approval Workflow, Compliance Monitoring and Alert Management System",
        version="1.0.0",
        docs_url="/docs" if settings.DEMO_MODE else None,
        redoc_url="/redoc" if settings.DEMO_MODE else None,
        openapi_url="/openapi.json" if settings.DEMO_MODE else None,
        lifespan=lifespan,
    )

    # CORS Middleware with strict origins from config
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With", "X-Idempotency-Key", "X-Signature", "X-Timestamp", "X-API-Key"],
    )

    # Security Headers Middleware
    @application.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' http://localhost:* http://127.0.0.1:*;"
        )
        return response

    @application.get("/health", response_model=HealthCheckResponse, tags=["Health"])
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
    @application.exception_handler(Exception)
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
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(config_router, prefix="/api/v1")
    application.include_router(lookup_router, prefix="/api/v1")
    application.include_router(applications_router, prefix="/api/v1")
    application.include_router(alerts_router, prefix="/api/v1")
    application.include_router(files_router, prefix="/api/v1")
    application.include_router(evc_router, prefix="/api/v1")
    application.include_router(undertakings_router, prefix="/api/v1")
    application.include_router(documents_router, prefix="/api/v1")
    application.include_router(reports_router, prefix="/api/v1")
    application.include_router(committee_router, prefix="/api/v1")
    application.include_router(holidays_router, prefix="/api/v1")
    application.include_router(risk_router, prefix="/api/v1")
    application.include_router(bottlenecks_router, prefix="/api/v1")
    application.include_router(planner_router, prefix="/api/v1")
    application.include_router(audit_router, prefix="/api/v1")
    application.include_router(retention_router, prefix="/api/v1")
    application.include_router(integration_router, prefix="/api/v1")

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
