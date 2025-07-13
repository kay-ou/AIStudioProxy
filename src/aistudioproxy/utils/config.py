"""
Configuration management for AIStudioProxy.

This module provides a centralized configuration system using Pydantic Settings
that supports environment variables, YAML files, and validation.
"""

from typing import List, Optional
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class ServerConfig(BaseSettings):
    """Server configuration settings."""
    
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=2048, ge=1, le=65535, description="Server port")
    workers: int = Field(default=1, ge=1, le=10, description="Number of worker processes")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    model_config = SettingsConfigDict(env_prefix="SERVER__")


class BrowserConfig(BaseSettings):
    """Browser automation configuration settings."""

    headless: bool = Field(default=True, description="Run browser in headless mode")
    port: int = Field(default=9222, ge=1024, le=65535, description="Browser debugging port")
    timeout: int = Field(default=30000, ge=1000, description="Browser operation timeout in ms")
    user_agent: Optional[str] = Field(default=None, description="Custom user agent string")
    viewport_width: int = Field(default=1920, ge=800, description="Browser viewport width")
    viewport_height: int = Field(default=1080, ge=600, description="Browser viewport height")
    initial_pool_size: int = Field(default=5, ge=1, le=50, description="Initial number of pages in the page pool")

    model_config = SettingsConfigDict(env_prefix="BROWSER__")


class AuthConfig(BaseSettings):
    """Authentication configuration settings."""

    enabled: bool = Field(default=True, description="Enable authentication")
    profile_path: Optional[str] = Field(default=None, description="Browser profile path")
    auto_login: bool = Field(default=True, description="Enable automatic login")
    session_timeout: int = Field(default=3600, ge=300, description="Session timeout in seconds")
    file_path: Optional[str] = Field(default=None, description="Path to the authentication file (e.g., cookies.json)")
    cookie_path: Optional[str] = Field(default=None, description="Cookie storage path")

    model_config = SettingsConfigDict(env_prefix="AUTH__")


class LogConfig(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format (json/text)")
    file_path: Optional[str] = Field(default=None, description="Log file path")
    max_size: str = Field(default="10MB", description="Maximum log file size")
    backup_count: int = Field(default=5, ge=1, description="Number of backup log files")
    
    @field_validator('level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    @field_validator('format')
    def validate_log_format(cls, v):
        valid_formats = ['json', 'text']
        if v.lower() not in valid_formats:
            raise ValueError(f'Log format must be one of: {valid_formats}')
        return v.lower()
    
    model_config = SettingsConfigDict(env_prefix="LOG__")


class PerformanceConfig(BaseSettings):
    """Performance configuration settings."""

    max_concurrent_requests: int = Field(default=50, ge=1, le=1000, description="Maximum concurrent requests")
    request_timeout: int = Field(default=60, ge=5, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Number of retry attempts")
    retry_delay: float = Field(default=1.0, ge=0.1, description="Retry delay in seconds")
    cleanup_delay: int = Field(default=300, ge=0, description="Delay in seconds before cleaning up request tracking")

    model_config = SettingsConfigDict(env_prefix="PERF__")


class SecurityConfig(BaseSettings):
    """Security configuration settings."""

    rate_limit: int = Field(default=100, ge=1, description="Rate limit per minute")
    cors_origins: str = Field(default="*", description="CORS allowed origins")
    allowed_hosts: str = Field(default="*", description="Allowed host patterns")

    model_config = SettingsConfigDict(env_prefix="SECURITY__")


class APIConfig(BaseSettings):
    """API specific configuration."""
    keys: List[str] = Field(default_factory=list, description="List of valid API keys")

    model_config = SettingsConfigDict(env_prefix="API__")


class MonitoringConfig(BaseSettings):
    """Monitoring configuration settings."""

    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, ge=1024, le=65535, description="Metrics server port")
    health_check_interval: int = Field(default=30, ge=5, description="Health check interval in seconds")

    model_config = SettingsConfigDict(env_prefix="MONITORING__")


class DevelopmentConfig(BaseSettings):
    """Development configuration settings."""

    reload: bool = Field(default=False, description="Enable auto-reload")
    debug_browser: bool = Field(default=False, description="Enable browser debugging")
    mock_responses: bool = Field(default=False, description="Use mock responses")

    model_config = SettingsConfigDict(env_prefix="DEV__")


class Config(BaseSettings):
    """Main configuration class that combines all configuration sections."""
    
    # Configuration sections
    server: ServerConfig = Field(default_factory=ServerConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    development: DevelopmentConfig = Field(default_factory=DevelopmentConfig)
    
    # Supported models list
    supported_models: List[str] = Field(
        default=[
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
        ],
        description="List of supported AI models"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
    )
    
    @classmethod
    def load_from_yaml(cls, yaml_path: str) -> "Config":
        """Load configuration from YAML file."""
        yaml_file = Path(yaml_path)
        if not yaml_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")
        
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
        
        return cls(**yaml_data)
    
    def save_to_yaml(self, yaml_path: str) -> None:
        """Save current configuration to YAML file."""
        yaml_file = Path(yaml_path)
        yaml_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, indent=2)
    
    def validate_config(self) -> None:
        """Validate the entire configuration."""
        # Custom validation logic can be added here
        if self.server.port == self.browser.port:
            raise ValueError("Server port and browser port cannot be the same")
        
        if self.server.port == self.monitoring.metrics_port:
            raise ValueError("Server port and metrics port cannot be the same")


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config


def reload_config() -> Config:
    """Reload the global configuration from environment variables."""
    global config
    config = Config()
    config.validate_config()
    return config


def load_config_from_file(config_path: str) -> Config:
    """Load configuration from a file and set it as global config."""
    global config
    
    if config_path.endswith('.yaml') or config_path.endswith('.yml'):
        config = Config.load_from_yaml(config_path)
    else:
        raise ValueError(f"Unsupported configuration file format: {config_path}")
    
    config.validate_config()
    return config
