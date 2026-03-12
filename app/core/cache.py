# app/core/cache.py
import redis
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
import logging

# Add logging
logger = logging.getLogger(__name__)

class CacheService:
    """Cache with Redis + in-memory fallback (as required)"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.in_memory_cache: Dict[str, tuple] = {}  # Type hint tuple
        self.use_redis = False
        
        # Try Redis
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            self.use_redis = True
            print("✅ Using Redis cache")
        except redis.ConnectionError as e:  # Specific exception
            logger.warning(f"Redis unavailable: {e}, using in-memory cache")
            print("⚠️ Redis unavailable, using in-memory cache")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from cache"""
        try:
            if self.use_redis:
                val = await asyncio.to_thread(self.redis_client.get, key)
                return json.loads(val) if val else None
            else:
                if key in self.in_memory_cache:
                    exp, val = self.in_memory_cache[key]
                    if datetime.now() < exp:
                        return val
                    del self.in_memory_cache[key]
                return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None  # Graceful degradation
    
    async def set(self, key: str, value: Any, ttl_hours: int = 24):
        """Set in cache with TTL"""
        try:
            if self.use_redis:
                await asyncio.to_thread(
                    self.redis_client.setex,
                    key,
                    timedelta(hours=ttl_hours),
                    json.dumps(value, default=str)  # Handle datetime
                )
            else:
                expiry = datetime.now() + timedelta(hours=ttl_hours)
                self.in_memory_cache[key] = (expiry, value)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
    
    async def increment(self, key: str, amount: int = 1, ttl_hours: int = 24) -> int:
        """Increment counter"""
        try:
            if self.use_redis:
                pipe = self.redis_client.pipeline()
                pipe.incrby(key, amount)
                pipe.expire(key, timedelta(hours=ttl_hours))
                return pipe.execute()[0]
            else:
                current = await self.get(key) or 0
                new = current + amount
                await self.set(key, new, ttl_hours)
                return new
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0  # Fail safe