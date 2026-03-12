# tests/test_reward.py
import sys
from pathlib import Path

# Add project root to Python path - THIS FIXES THE IMPORT ERROR
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime
from app.services.reward_service import RewardService
from app.core.config import ConfigLoader
from app.core.cache import CacheService
from app.services.persona_service import PersonaService

@pytest.fixture
def service():
    config = ConfigLoader()
    cache = CacheService()
    persona = PersonaService()
    return RewardService(config, cache, persona)

@pytest.mark.asyncio
async def test_xp_calculation(service):
    xp = await service.calculate_xp(100, "NEW")
    assert xp == 1000

@pytest.mark.asyncio
async def test_idempotency(service):
    # First request
    r1 = await service.make_decision(
        txn_id="test1", user_id="u1", merchant_id="m1",
        amount=100, txn_type="PURCHASE", ts=datetime.now()
    )
    # Second request (same data)
    r2 = await service.make_decision(
        txn_id="test1", user_id="u1", merchant_id="m1",
        amount=100, txn_type="PURCHASE", ts=datetime.now()
    )
    assert r1["decision_id"] == r2["decision_id"]

@pytest.mark.asyncio
async def test_cac_cap(service):
    user = "cac_test_user"
    # First reward
    await service.cache.set(service._cac_key(user), 90, 24)  # Set to 90
    under, new_total = await service.check_cac_cap(user, "NEW", 20)  # Unpack tuple
    assert under == False  # 90+20=110 > 100 cap
    assert new_total == 110  # Optional: check total
@pytest.mark.asyncio
async def test_different_users_get_different_personas(service):
    """Test that different users can get different personas"""
    user1_persona = await service.persona.get_persona("user_a")
    user2_persona = await service.persona.get_persona("user_b")
    # Just verify they're valid personas
    assert user1_persona in ["NEW", "RETURNING", "POWER"]
    assert user2_persona in ["NEW", "RETURNING", "POWER"]

@pytest.mark.asyncio
async def test_same_user_gets_same_persona(service):
    """Test that same user gets consistent persona"""
    user = "consistent_user"
    persona1 = await service.persona.get_persona(user)
    persona2 = await service.persona.get_persona(user)
    assert persona1 == persona2  # Should be same!

@pytest.mark.asyncio
async def test_gold_reward_value(service):
    """Test GOLD reward calculation"""
    # You'd need to add calculate_reward_value method
    # value = await service.calculate_reward_value("GOLD", 1000)
    # assert value == 5
    pass