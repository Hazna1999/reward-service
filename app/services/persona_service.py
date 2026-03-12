# app/services/persona_service.py
import random
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class PersonaService:
    """Mock persona service using in-memory map (as required)"""
    
    # Persona distribution constants
    PERSONA_DISTRIBUTION = [
        (0.6, "NEW"),
        (0.3, "RETURNING"), 
        (0.1, "POWER")
    ]
    
    def __init__(self):
        # In-memory map of user personas
        self.user_personas: Dict[str, str] = {}
        print("✅ PersonaService initialized with in-memory map")
    
    async def get_persona(self, user_id: str) -> str:
        """Get persona for user - mocked as per assignment"""
        try:
            # Check in-memory map first
            if user_id in self.user_personas:
                return self.user_personas[user_id]
            
            # Mock new user with random assignment
            persona = self._assign_random_persona()
            
            # Store in in-memory map
            self.user_personas[user_id] = persona
            logger.debug(f"Assigned persona {persona} to user {user_id}")
            return persona
            
        except Exception as e:
            logger.error(f"Error getting persona for user {user_id}: {e}")
            return "NEW"  # Safe fallback
    
    def _assign_random_persona(self) -> str:
        """Assign random persona based on distribution"""
        r = random.random()
        cumulative = 0
        for prob, persona in self.PERSONA_DISTRIBUTION:
            cumulative += prob
            if r < cumulative:
                return persona
        return "NEW"  # Fallback