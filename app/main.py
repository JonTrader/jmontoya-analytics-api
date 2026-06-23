from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.routers import dashboard, events, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: clean up database connections on shutdown."""
    yield
    await engine.dispose()


app = FastAPI(
    title="JMontoya Analytics API",
    description="Analytics ingestion and dashboard backend for jmontoya.dev",
    version="0.1.0",
    lifespan=lifespan,
)


# Configure CORS.
# Supports a single "*" or a comma-separated list of origins.
if settings.cors_origins == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers.
app.include_router(health.router)
app.include_router(events.router)
app.include_router(dashboard.router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"message": "JMontoya Analytics API — see /docs for API documentation"}
