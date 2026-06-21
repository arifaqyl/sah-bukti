from contextlib import asynccontextmanager
import logging

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.dependencies import BusinessContext, require_owner_context
from app.api.routes import auth, business_profile, businesses, customers, daily_close, demo, evidence, exports, health, inventory, invoices, month_end, parser, payment_proofs, payments, provision, reminders, review, whatsapp
from app.config import BASE_DIR, UPLOADS_DIR
from app.db.store import init_db
from app.services.cron import run_daily_close, run_monthly_provision, start_scheduler, stop_scheduler


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(
        title="Sah.Bukti",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    logger.info("Scheduler started: daily_close at 23:59, monthly_provision on day 1 at 08:00")
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(
        title="Sah.Bukti",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(businesses.router, prefix="/api/v1", tags=["businesses"])
    app.include_router(business_profile.router, prefix="/api/v1", tags=["business"])
    app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
    app.include_router(invoices.router, prefix="/api/v1", tags=["invoices"])
    app.include_router(daily_close.router, prefix="/api/v1", tags=["daily-close"])
    app.include_router(parser.router, prefix="/api/v1", tags=["parser"])
    app.include_router(demo.router, prefix="/api/v1", tags=["demo"])
    app.include_router(evidence.router, prefix="/api/v1", tags=["evidence"])
    app.include_router(inventory.router, prefix="/api/v1", tags=["inventory"])
    app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
    app.include_router(payment_proofs.router, prefix="/api/v1", tags=["payment-proofs"])
    app.include_router(reminders.router, prefix="/api/v1", tags=["reminders"])
    app.include_router(review.router, prefix="/api/v1", tags=["review"])
    app.include_router(exports.router, prefix="/api/v1", tags=["exports"])
    app.include_router(month_end.router, prefix="/api/v1", tags=["month-end"])
    app.include_router(provision.router, prefix="/api/v1", tags=["provision"])
    app.include_router(whatsapp.router, prefix="/api/v1", tags=["whatsapp"])

    frontend_dir = BASE_DIR / "frontend"
    frontend_dir.mkdir(exist_ok=True)
    frontend_assets_dir = frontend_dir / "assets"
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
    if frontend_assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_assets_dir)), name="frontend-assets")

    def resolve_frontend_asset(*candidates: str) -> Path:
        for candidate in candidates:
            frontend_path = frontend_dir / candidate
            if frontend_path.exists():
                return frontend_path
        raise HTTPException(status_code=404, detail="Page not found")

    @app.get("/frontend")
    @app.get("/frontend/")
    async def frontend_index():
        return RedirectResponse(url="/", status_code=307)

    @app.get("/frontend/{path:path}")
    async def frontend_spa(path: str):
        normalized = path.lstrip("/")
        return RedirectResponse(url=f"/{normalized}" if normalized else "/", status_code=307)

    @app.get("/")
    async def root_redirect():
        return FileResponse(str(resolve_frontend_asset("index.html")))

    @app.get("/report")
    async def provision_report():
        return FileResponse(str(resolve_frontend_asset("report.html", "readiness.html", "index.html")))

    @app.get("/pay.html")
    async def payment_page():
        return FileResponse(str(resolve_frontend_asset("pay.html")))

    @app.get("/favicon.png")
    async def favicon():
        return FileResponse(str(resolve_frontend_asset("favicon.png")))

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        if path == "legacy" or path.startswith("legacy/"):
            raise HTTPException(status_code=404, detail="Not Found")
        if path.startswith("api/") or path.startswith("health") or path.startswith("uploads/") or path.startswith("assets/") or path.startswith("admin/"):
            raise HTTPException(status_code=404, detail="Not Found")
        return FileResponse(str(resolve_frontend_asset("index.html")))

    @app.post("/api/v1/admin/cron/daily-close")
    async def admin_daily_close(
        date: str | None = Query(default=None),
        ctx: BusinessContext = Depends(require_owner_context),
    ):
        try:
            return run_daily_close(business_id=ctx.business_id, close_date=date)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/v1/admin/cron/monthly-provision")
    async def admin_monthly_provision(
        month: str | None = Query(default=None),
        ctx: BusinessContext = Depends(require_owner_context),
    ):
        try:
            return run_monthly_provision(business_id=ctx.business_id, month=month)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


app = create_app()
