from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import auth as api_auth
from api import dashboard as api_dashboard
from api import internal as api_internal
from api import submission as api_submission
from api import form_management as api_form_management
from core.config import settings
from core.database import engine
from web import auth_web as web_auth
from web import dashboard as web_dashboard
from web import tenant_web
from web import form_management as web_form_management

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("startup", environment=settings.environment)
    yield
    await engine.dispose()
    logger.info("shutdown")


app = FastAPI(
    title="Doc Persona — Admin Portal",
    version="1.0.0",
    docs_url="/api/docs" if settings.environment == "development" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routers
app.include_router(api_auth.router)
app.include_router(api_dashboard.router)
app.include_router(api_submission.router)
app.include_router(api_internal.router)
app.include_router(api_form_management.router)

# Web (Jinja2) router
app.include_router(web_auth.router)
app.include_router(web_dashboard.router)
app.include_router(tenant_web.router)
app.include_router(web_form_management.router)

# Static assets
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    pass  # static dir optional during early dev
