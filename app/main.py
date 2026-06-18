from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import customers, daily_close, health, inventory, invoices, parser, provision, whatsapp
from app.config import BASE_DIR, UPLOADS_DIR
from app.db.store import init_db
from app.services.cron import daily_close_job, monthly_provision_job, run_daily_close, run_monthly_provision, start_scheduler, stop_scheduler


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    logger.info("Scheduler started: daily_close at 23:59, monthly_provision on day 1 at 08:00")
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Kede",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
    app.include_router(invoices.router, prefix="/api/v1", tags=["invoices"])
    app.include_router(daily_close.router, prefix="/api/v1", tags=["daily-close"])
    app.include_router(parser.router, prefix="/api/v1", tags=["parser"])
    app.include_router(inventory.router, prefix="/api/v1", tags=["inventory"])
    app.include_router(provision.router, prefix="/api/v1", tags=["provision"])
    app.include_router(whatsapp.router, prefix="/api/v1", tags=["whatsapp"])

    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

    frontend_dir = BASE_DIR / "frontend"
    frontend_dir.mkdir(exist_ok=True)
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")

    legacy_static_dir = BASE_DIR / "app" / "static"
    app.mount("/legacy", StaticFiles(directory=str(legacy_static_dir)), name="legacy-static")

    @app.get("/")
    async def root_redirect():
        return FileResponse(str(frontend_dir / "index.html"))

    @app.get("/report")
    async def provision_report():
        return FileResponse(str(frontend_dir / "report.html"))

    @app.get("/admin/cron/run-daily-close")
    async def run_daily_close_admin():
        await daily_close_job()
        return {"status": "daily_close_job scheduled"}

    @app.get("/admin/cron/run-monthly-provision")
    async def run_monthly_provision_admin():
        await monthly_provision_job()
        return {"status": "monthly_provision_job scheduled"}

    @app.post("/api/v1/admin/cron/daily-close")
    async def admin_daily_close(
        business_id: int | None = Query(default=None, ge=1),
        date: str | None = Query(default=None),
    ):
        try:
            return run_daily_close(business_id=business_id, close_date=date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/admin/cron/monthly-provision")
    async def admin_monthly_provision(
        business_id: int | None = Query(default=None, ge=1),
        month: str | None = Query(default=None),
    ):
        try:
            return run_monthly_provision(business_id=business_id, month=month)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


app = create_app()
