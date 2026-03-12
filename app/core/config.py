# app/core/config.py
import yaml
import os
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Loads configuration from YAML file"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        print(f"✅ Config loaded from {config_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load YAML config file"""
        try:
            if not Path(self.config_path).exists():
                raise FileNotFoundError(f"Config file not found: {self.config_path}")
            
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
                if not config:
                    raise ValueError("Config file is empty")
                return config
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            raise
        except Exception as e:
            logger.error(f"Config loading error: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value using dot notation"""
        try:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default
            return value
        except Exception as e:
            logger.warning(f"Error getting config key {key}: {e}")
            return default
    
    def get_persona_config(self, persona: str) -> Dict[str, Any]:
        """Get configuration for a specific persona"""
        return {
            'multiplier': self.get(f'personas.{persona}.multiplier', 1.0),
            'daily_cac_cap': self.get(f'personas.{persona}.daily_cac_cap', 100)
        }
    
    @property
    def policy_version(self) -> str:
        return self.get('policy_version', '1.0.0')
    
    @property
    def xp_per_rupee(self) -> int:
        return self.get('xp_per_rupee', 10)
    
    @property
    def max_xp_per_txn(self) -> int:
        return self.get('max_xp_per_txn', 1000)
    
    @property
    def reward_weights(self) -> Dict[str, float]:
        return self.get('reward_weights', {'XP': 0.5, 'CHECKOUT': 0.3, 'GOLD': 0.2})