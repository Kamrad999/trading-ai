"""
Environment variable validation for production deployment.

Validates required environment variables and provides sensible defaults.
"""

import os
from typing import Dict, Any, Optional
from .logging import get_logger


class EnvironmentValidator:
    """Validates and manages environment variables."""
    
    def __init__(self) -> None:
        """Initialize environment validator."""
        self.logger = get_logger("env_validator")
        
        # Required environment variables
        self.required_vars = {
            "TRADING_AI_ENV": {
                "default": "development",
                "description": "Environment (development/staging/production)"
            },
            "TRADING_AI_LOG_LEVEL": {
                "default": "INFO",
                "description": "Logging level (DEBUG/INFO/WARNING/ERROR)"
            },
            "TRADING_AI_DATA_DIR": {
                "default": "./data",
                "description": "Data directory path"
            },
            "TRADING_AI_STATE_FILE": {
                "default": "./data/state.json",
                "description": "State file path"
            }
        }
        
        # Optional environment variables
        self.optional_vars = {
            "TRADING_AI_PORTFOLIO_SIZE": {
                "default": "25000.0",
                "description": "Portfolio size in USD"
            },
            "TRADING_AI_MAX_POSITION_SIZE": {
                "default": "0.02",
                "description": "Maximum position size as fraction of portfolio"
            },
            "TRADING_AI_DAILY_LOSS_LIMIT": {
                "default": "0.025",
                "description": "Daily loss limit as fraction of portfolio"
            },
            "TRADING_API_KEY": {
                "default": "",
                "description": "Trading API key (if applicable)"
            },
            "NEWS_API_KEY": {
                "default": "",
                "description": "News API key (if applicable)"
            }
        }
    
    def validate_environment(self) -> Dict[str, Any]:
        """Validate all environment variables."""
        validated_config = {}
        
        # Validate required variables
        for var_name, config in self.required_vars.items():
            value = os.getenv(var_name, config["default"])
            
            if not value and not config["default"]:
                raise ValueError(f"Required environment variable {var_name} is not set")
            
            validated_config[var_name] = value
            self.logger.debug(f"Environment variable {var_name} = {value}")
        
        # Validate optional variables
        for var_name, config in self.optional_vars.items():
            value = os.getenv(var_name, config["default"])
            validated_config[var_name] = value
            self.logger.debug(f"Optional environment variable {var_name} = {value}")
        
        # Validate specific values
        self._validate_specific_values(validated_config)
        
        self.logger.info("Environment validation completed successfully")
        return validated_config
    
    def _validate_specific_values(self, config: Dict[str, Any]) -> None:
        """Validate specific environment variable values."""
        # Validate environment
        valid_envs = ["development", "staging", "production"]
        if config["TRADING_AI_ENV"] not in valid_envs:
            raise ValueError(f"Invalid TRADING_AI_ENV: {config['TRADING_AI_ENV']}. Must be one of {valid_envs}")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if config["TRADING_AI_LOG_LEVEL"] not in valid_log_levels:
            raise ValueError(f"Invalid TRADING_AI_LOG_LEVEL: {config['TRADING_AI_LOG_LEVEL']}. Must be one of {valid_log_levels}")
        
        # Validate numeric values
        try:
            portfolio_size = float(config["TRADING_AI_PORTFOLIO_SIZE"])
            if portfolio_size <= 0:
                raise ValueError("TRADING_AI_PORTFOLIO_SIZE must be positive")
        except ValueError as e:
            raise ValueError(f"Invalid TRADING_AI_PORTFOLIO_SIZE: {e}")
        
        try:
            max_position = float(config["TRADING_AI_MAX_POSITION_SIZE"])
            if not 0 < max_position <= 1:
                raise ValueError("TRADING_AI_MAX_POSITION_SIZE must be between 0 and 1")
        except ValueError as e:
            raise ValueError(f"Invalid TRADING_AI_MAX_POSITION_SIZE: {e}")
        
        try:
            daily_loss = float(config["TRADING_AI_DAILY_LOSS_LIMIT"])
            if not 0 < daily_loss <= 1:
                raise ValueError("TRADING_AI_DAILY_LOSS_LIMIT must be between 0 and 1")
        except ValueError as e:
            raise ValueError(f"Invalid TRADING_AI_DAILY_LOSS_LIMIT: {e}")
        
        # Validate data directory
        data_dir = config["TRADING_AI_DATA_DIR"]
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir, exist_ok=True)
                self.logger.info(f"Created data directory: {data_dir}")
            except Exception as e:
                raise ValueError(f"Cannot create data directory {data_dir}: {e}")
        
        # Validate state file directory
        state_file = config["TRADING_AI_STATE_FILE"]
        state_dir = os.path.dirname(state_file)
        if not os.path.exists(state_dir):
            try:
                os.makedirs(state_dir, exist_ok=True)
                self.logger.info(f"Created state file directory: {state_dir}")
            except Exception as e:
                raise ValueError(f"Cannot create state file directory {state_dir}: {e}")
    
    def get_environment_summary(self) -> str:
        """Get a summary of current environment configuration."""
        config = self.validate_environment()
        
        summary = f"""
Environment Configuration Summary:
=====================================
Environment: {config['TRADING_AI_ENV']}
Log Level: {config['TRADING_AI_LOG_LEVEL']}
Data Directory: {config['TRADING_AI_DATA_DIR']}
State File: {config['TRADING_AI_STATE_FILE']}
Portfolio Size: ${config['TRADING_AI_PORTFOLIO_SIZE']}
Max Position Size: {float(config['TRADING_AI_MAX_POSITION_SIZE'])*100:.1f}%
Daily Loss Limit: {float(config['TRADING_AI_DAILY_LOSS_LIMIT'])*100:.1f}%
API Keys Configured: {'Yes' if config['TRADING_API_KEY'] else 'No'}
News API Key Configured: {'Yes' if config['NEWS_API_KEY'] else 'No'}
"""
        return summary


# Global environment validator instance
_env_validator = None

def get_env_validator() -> EnvironmentValidator:
    """Get the global environment validator instance."""
    global _env_validator
    if _env_validator is None:
        _env_validator = EnvironmentValidator()
    return _env_validator

def validate_environment() -> Dict[str, Any]:
    """Validate environment and return configuration."""
    return get_env_validator().validate_environment()
