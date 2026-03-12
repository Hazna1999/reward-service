# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app with metadata
app = FastAPI(
    title=os.getenv('APP_NAME', 'Reward Decision Service'),
    description="""
    A low-latency microservice that returns deterministic reward outcomes for transactions.
    
    ## Features
    * 🎯 Deterministic reward decisions
    * 🔒 Idempotent request handling
    * ⚙️ Config-driven policy evaluation
    * ⚡ Cache-first design with Redis
    * 📊 Daily CAC cap enforcement
    * 👤 Persona-based multipliers
    """,
    version=os.getenv('VERSION', '1.0.0'),
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Reward Service Team",
        "email": os.getenv('CONTACT_EMAIL', 'team@example.com'),
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# Add CORS middleware if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv('ALLOWED_ORIGINS', '*').split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1", tags=["reward"])

@app.get("/", tags=["root"])
async def root():
    """Root endpoint with service information"""
    return {
        "service": "🎯 Reward Decision Service",
        "version": os.getenv('VERSION', '1.0.0'),
        "status": "running",
        "environment": os.getenv('ENVIRONMENT', 'development'),
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/v1/health",
        "endpoints": {
            "reward": "POST /api/v1/reward/decide",
            "health": "GET /api/v1/health"
        }
    }

@app.on_event("startup")
async def startup_event():
    """Log when application starts"""
    logger.info("🚀 Reward Decision Service started")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Redis: {'Connected' if cache.use_redis else 'In-memory fallback'}")

@app.on_event("shutdown")
async def shutdown_event():
    """Log when application shuts down"""
    logger.info("🛑 Reward Decision Service shutting down")