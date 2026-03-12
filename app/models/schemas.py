# app/models/schemas.py
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

class RewardType(str, Enum):
    """Enum for reward types"""
    XP = "XP"
    CHECKOUT = "CHECKOUT"
    GOLD = "GOLD"

class RewardRequest(BaseModel):
    """API Request Schema"""
    txn_id: str = Field(..., description="Unique transaction ID", min_length=1, max_length=100)
    user_id: str = Field(..., description="User ID", min_length=1, max_length=100)
    merchant_id: str = Field(..., description="Merchant ID", min_length=1, max_length=100)
    amount: float = Field(..., description="Transaction amount in rupees", gt=0, le=1_000_000)
    txn_type: str = Field(..., description="Transaction type (PURCHASE, PAYMENT, etc.)", 
                          regex="^(PURCHASE|PAYMENT|REFUND|CANCELLATION)$")
    ts: datetime = Field(..., description="Transaction timestamp")
    
    @validator('amount')
    def validate_amount(cls, v):
        """Ensure amount is positive and reasonable"""
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 1_000_000:
            raise ValueError('Amount exceeds maximum limit')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "txn_id": "txn_123456",
                "user_id": "user_789",
                "merchant_id": "merchant_456",
                "amount": 1000.50,
                "txn_type": "PURCHASE",
                "ts": "2024-03-12T10:00:00"
            }
        }

class RewardResponse(BaseModel):
    """API Response Schema"""
    decision_id: str = Field(..., description="Unique decision ID (UUID)")
    policy_version: str = Field(..., description="Version of policy used")
    reward_type: RewardType = Field(..., description="Type of reward granted")
    reward_value: int = Field(..., description="Monetary value of reward (in rupees)", ge=0)
    xp: int = Field(..., description="XP points earned", ge=0)
    reason_codes: List[str] = Field(..., description="List of reason codes explaining the decision")
    meta: Dict[str, Any] = Field(..., description="Additional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "decision_id": "123e4567-e89b-12d3-a456-426614174000",
                "policy_version": "1.0.0",
                "reward_type": "GOLD",
                "reward_value": 50,
                "xp": 1000,
                "reason_codes": ["gold_selected", "under_cac_cap"],
                "meta": {
                    "persona": "RETURNING",
                    "multiplier": 1.5,
                    "processed_at": "2024-03-12T10:00:01"
                }
            }
        }