from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from datetime import datetime

from app.core.config import settings
from app.api.routes import router as api_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Recommendation Engine...")
    
    from app.services.ml.inference_service import get_inference_service
    await get_inference_service()
    
    yield
    # Shutdown
    logger.info("Shutting down Recommendation Engine...")

app = FastAPI(
    title="Recommendation Engine API",
    description="Netflix-Scale Recommendation Platform",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "connected",
            "redis": "connected",
            "kafka": "connected",
            "qdrant": "connected",
            "mlflow": "connected"
        }
    }

@app.get("/")
async def root():
    return {
        "message": "Recommendation Engine API",
        "docs": "/docs",
        "health": "/health"
    }
