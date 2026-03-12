# app/services/reward_service.py
import asyncio
import random
import uuid
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple
from app.core.config import ConfigLoader
from app.core.cache import CacheService
from app.services.persona_service import PersonaService

logger = logging.getLogger(__name__)

class RewardService:
    """Main reward decision service"""
    
    # Constants for better maintainability
    DEFAULT_TTL = 24
    REWARD_TYPES = {
        "CHECKOUT": "monetary",
        "GOLD": "monetary",
        "XP": "non_monetary"
    }
    
    def __init__(self, config: ConfigLoader, cache: CacheService, persona: PersonaService):
        self.config = config
        self.cache = cache
        self.persona = persona
        logger.info("RewardService initialized")
    
    def _idem_key(self, txn_id: str, user_id: str, merchant_id: str) -> str:
        """Generate idempotency key"""
        return f"idem:{txn_id}:{user_id}:{merchant_id}"
    
    def _cac_key(self, user_id: str) -> str:
        """Generate CAC tracking key for today"""
        return f"cac:{user_id}:{date.today().isoformat()}"
    
    def _last_reward_key(self, user_id: str) -> str:
        """Generate last reward tracking key"""
        return f"last_reward:{user_id}"
    
    async def calculate_xp(self, amount: float, persona: str) -> int:
        """XP = min(amount * xp_per_rupee * multiplier, max_xp_per_txn)"""
        try:
            xp_per_rupee = self.config.get('xp_per_rupee', 10)
            max_xp = self.config.get('max_xp_per_txn', 1000)
            multiplier = self.config.get(f'personas.{persona}.multiplier', 1.0)
            
            xp = amount * xp_per_rupee * multiplier
            result = min(int(xp), max_xp)
            
            logger.debug(f"XP calc: {amount} * {xp_per_rupee} * {multiplier} = {xp} → {result}")
            return result
        except Exception as e:
            logger.error(f"XP calculation error: {e}")
            return 0  # Safe fallback
    
    async def select_reward_type(self) -> str:
        """Select reward type based on weights"""
        try:
            weights = self.config.get('reward_weights', 
                                     {'XP': 0.5, 'CHECKOUT': 0.3, 'GOLD': 0.2})
            r = random.random()
            cumulative = 0
            
            for reward_type, weight in weights.items():
                cumulative += weight
                if r < cumulative:
                    logger.debug(f"Selected {reward_type} (rand={r:.2f})")
                    return reward_type
                    
            return "XP"  # Fallback
        except Exception as e:
            logger.error(f"Reward selection error: {e}")
            return "XP"
    
    async def check_cac_cap(self, user_id: str, persona: str, value: int) -> Tuple[bool, int]:
        """Check if under daily cap. Returns (is_under, current_total)"""
        try:
            cap = self.config.get(f'personas.{persona}.daily_cac_cap', 100)
            current = await self.cache.get(self._cac_key(user_id)) or 0
            new_total = current + value
            is_under = new_total <= cap
            
            logger.debug(f"CAC cap check: {current}+{value}={new_total}/{cap} → {'under' if is_under else 'over'}")
            return is_under, new_total
        except Exception as e:
            logger.error(f"CAC cap check error: {e}")
            return False, 0  # Fail safe - assume over cap
    
    async def calculate_monetary_value(self, reward_type: str, amount: float) -> int:
        """Calculate monetary reward value with min/max bounds"""
        try:
            if reward_type == "XP":
                return 0
            
            # Get percentage from config
            percentage_key = f'monetary_rewards.{reward_type.lower()}_percentage'
            percentage = self.config.get(percentage_key, 0.01 if reward_type == "CHECKOUT" else 0.005)
            
            # Calculate raw value
            raw_value = amount * percentage
            
            # Apply min/max bounds
            min_reward = self.config.get('monetary_rewards.min_reward_value', 1)
            max_reward = self.config.get('monetary_rewards.max_reward_value', 500)
            
            value = max(min_reward, min(int(raw_value) if raw_value >= 1 else min_reward, max_reward))
            
            logger.debug(f"{reward_type} value: {amount} * {percentage} = {raw_value} → {value}")
            return value
        except Exception as e:
            logger.error(f"Monetary value calculation error: {e}")
            return 0
    
    def _create_decision_base(self, txn_id: str, user_id: str, merchant_id: str,
                              amount: float, txn_type: str, ts: datetime,
                              persona: str, xp: int) -> Dict[str, Any]:
        """Create base decision structure"""
        return {
            "decision_id": str(uuid.uuid4()),
            "policy_version": self.config.get('policy_version', '1.0'),
            "xp": xp,
            "meta": {
                "persona": persona,
                "amount": amount,
                "txn_type": txn_type,
                "timestamp": ts.isoformat()
            }
        }
    
    async def make_decision(self, txn_id: str, user_id: str, merchant_id: str,
                           amount: float, txn_type: str, ts: datetime) -> Dict[str, Any]:
        
        try:
            # 1. Check idempotency
            idem_key = self._idem_key(txn_id, user_id, merchant_id)
            cached = await self.cache.get(idem_key)
            if cached:
                logger.info(f"Cache hit for {idem_key}")
                return cached
            
            # 2. Get persona
            persona = await self.persona.get_persona(user_id)

            # 3. Check excluded transaction types
            excluded_types = self.config.get('business_rules.excluded_txn_types', [])
            if txn_type in excluded_types:
                decision = self._create_decision_base(
                    txn_id, user_id, merchant_id, amount, txn_type, ts, persona, 0
                )
                decision.update({
                    "reward_type": "XP",
                    "reward_value": 0,
                    "reason_codes": ["NOT_QUALIFIED"],
                    "meta": {
                        **decision["meta"],
                        "message": f"Transaction type {txn_type} excluded"
                    }
                })
                
                # Cache and return
                ttl = self.config.get('cache.idempotency_ttl_hours', self.DEFAULT_TTL)
                await self.cache.set(idem_key, decision, ttl)
                return decision
            
            # 4. Calculate XP
            xp = await self.calculate_xp(amount, persona)
            
            # 5. Check feature flags
            prefer_xp = self.config.get('features.prefer_xp_mode', False)
            
            if prefer_xp:
                decision = self._create_decision_base(
                    txn_id, user_id, merchant_id, amount, txn_type, ts, persona, xp
                )
                decision.update({
                    "reward_type": "XP",
                    "reward_value": 0,
                    "reason_codes": ["prefer_xp_mode"]
                })
            else:
                # Select reward type
                reward_type = await self.select_reward_type()
                
                if reward_type == "XP":
                    decision = self._create_decision_base(
                        txn_id, user_id, merchant_id, amount, txn_type, ts, persona, xp
                    )
                    decision.update({
                        "reward_type": "XP",
                        "reward_value": 0,
                        "reason_codes": ["xp_selected"]
                    })
                else:
                    # Calculate monetary value
                    value = await self.calculate_monetary_value(reward_type, amount)
                    
                    # Check CAC cap
                    under_cap, new_total = await self.check_cac_cap(user_id, persona, value)
                    
                    decision = self._create_decision_base(
                        txn_id, user_id, merchant_id, amount, txn_type, ts, persona, xp
                    )
                    
                    if under_cap:
                        # Update CAC counter
                        await self.cache.increment(self._cac_key(user_id), value, 24)
                        
                        decision.update({
                            "reward_type": reward_type,
                            "reward_value": value,
                            "reason_codes": [f"{reward_type.lower()}_selected", "under_cac_cap"]
                        })
                    else:
                        # Cap exceeded - give XP instead
                        decision.update({
                            "reward_type": "XP",
                            "reward_value": 0,
                            "reason_codes": ["cac_cap_exceeded"]
                        })
            
            # 6. Cache for idempotency
            ttl = self.config.get('cache.idempotency_ttl_hours', self.DEFAULT_TTL)
            await self.cache.set(idem_key, decision, ttl)
            
            logger.info(f"New decision made: {decision['decision_id']} for user {user_id}")
            return decision
            
        except Exception as e:
            logger.error(f"Error making decision: {e}", exc_info=True)
            # Return safe fallback
            return {
                "decision_id": str(uuid.uuid4()),
                "policy_version": self.config.get('policy_version', '1.0'),
                "reward_type": "XP",
                "reward_value": 0,
                "xp": 0,
                "reason_codes": ["SYSTEM_ERROR"],
                "meta": {"error": str(e)}
            }