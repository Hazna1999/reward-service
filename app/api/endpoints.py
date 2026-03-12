# app/api/endpoints.py
from fastapi import APIRouter, HTTPException, status
from datetime import datetime
import logging
from app.services.reward_service import RewardService
from app.services.persona_service import PersonaService
from app.core.config import ConfigLoader
from app.core.cache import CacheService
from app.models.schemas import RewardRequest, RewardResponse

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services with better error handling
try:
    config = ConfigLoader()
    cache = CacheService()
    persona = PersonaService()
    reward_service = RewardService(config, cache, persona)
    logger.info("Services initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize services: {e}")
    raise

@router.post(
    "/reward/decide", 
    response_model=RewardResponse,
    status_code=status.HTTP_200_OK,
    summary="Make a reward decision",
    description="Process a transaction and return deterministic reward outcome"
)
async def decide_reward(request: RewardRequest):
    """
    Make reward decision for a transaction
    
    - **txn_id**: Unique transaction identifier
    - **user_id**: User making the transaction
    - **merchant_id**: Merchant where transaction occurred
    - **amount**: Transaction amount in rupees
    - **txn_type**: Type of transaction (PURCHASE, PAYMENT, etc.)
    - **ts**: Transaction timestamp
    """
    try:
        logger.info(f"Processing reward decision for transaction: {request.txn_id}")
        
        decision = await reward_service.make_decision(
            txn_id=request.txn_id,
            user_id=request.user_id,
            merchant_id=request.merchant_id,
            amount=request.amount,
            txn_type=request.txn_type,
            ts=request.ts
        )
        
        logger.info(f"Decision made: {decision['decision_id']} - Type: {decision['reward_type']}")
        return decision
        
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the service is running"
)
async def health():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "reward-decision-service"
    }

@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Check if service is ready to accept traffic"
)
async def ready():
    """Readiness check for Kubernetes/Docker"""
    # Add checks for dependencies (Redis, etc.)
    return {"status": "ready"}