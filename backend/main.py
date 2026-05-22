import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure structured logging is configured
from backend.core import logging as _logging
from backend.core.config import settings
from backend.api.routes import health, contracts

logger = logging.getLogger("qolyx.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info(
        "Initializing Qolyx REST Engine application lifespan",
        extra={"status": "starting", "environment": settings.ENVIRONMENT},
    )
    yield
    # Shutdown tasks
    logger.info(
        "Tearing down Qolyx REST Engine application lifespan",
        extra={"status": "stopping"},
    )


app = FastAPI(
    title="Qolyx API",
    description="REST Engine Ingress serving JSON APIs and health gates.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration targeting standard client ports dynamically
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    f"http://localhost:{settings.BACKEND_PORT}",
    f"http://127.0.0.1:{settings.BACKEND_PORT}",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints under canonical prefix /api
app.include_router(health.router, prefix="/api")
app.include_router(contracts.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Welcome to Qolyx API Ingress Engine."}
