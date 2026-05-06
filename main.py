"""OSETA — Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from routes import articles, sectors, predictions, health, correlations
from services.database import engine
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events. Schema managed by Alembic — no create_all here."""
    yield
    await engine.dispose()


app = FastAPI(
    title="OSETA API",
    description="Observatory for Strategic Emerging Technologies & Analytics",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics — expose /metrics
Instrumentator().instrument(app).expose(app)

# Routers
app.include_router(health.router, tags=["health"])
app.include_router(articles.router, prefix="/articles", tags=["articles"])
app.include_router(sectors.router, prefix="/sectors", tags=["sectors"])
app.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
app.include_router(correlations.router)
