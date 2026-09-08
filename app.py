import os
import sys
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

api_key = os.getenv("TWELVE_DATA_API_KEY")
if not api_key:
    logger.warning("=" * 60)
    logger.warning("⚠️  WARNING: TWELVE_DATA_API_KEY not found!")
    logger.warning("⚠️  Running in FALLBACK/SYNTHETIC mode.")
    logger.warning("=" * 60)

from api.routes import router
from storage.database import init_db

app = FastAPI(
    title="AdaptiveSpread FX Pricing API",
    description="Real-time FX adaptive pricing using contextual bandits",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting AdaptiveSpread API...")
    logger.info(f"📊 Mode: {'LIVE DATA' if api_key else 'FALLBACK/SYNTHETIC'}")
    init_db()
    logger.info("✅ System ready!")


@app.get("/")
async def root():
    return {
        "service": "AdaptiveSpread",
        "status": "running",
        "version": "1.0.0",
        "mode": "LIVE" if api_key else "FALLBACK",
        "api_key_configured": bool(api_key),
        "docs": "/docs",
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy", "mode": "LIVE" if api_key else "FALLBACK"}


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("AdaptiveSpread FX Pricing System")
    logger.info("=" * 60)
    if api_key:
        logger.info("✅ TWELVE_DATA_API_KEY found - Using LIVE DATA")
    else:
        logger.info("⚠️  No API key - Using FALLBACK/SYNTHETIC DATA")
    logger.info("🌐 API: http://localhost:8000")
    logger.info("📚 Docs: http://localhost:8000/docs")
    logger.info("=" * 60)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
