"""
Tests for configuration management.

This module contains unit tests for the configuration system.
"""

import os
import tempfile
import pytest
from pathlib import Path

from src.utils.config import (
    Config,
    ServerConfig,
    BrowserConfig,
    AuthConfig,
    LogConfig,
    get_config,
    reload_config,
    load_config_from_file,
)


@pytest.mark.unit
class TestServerConfig:
    """Test server configuration."""
    
    def test_default_values(self):
        """Test default server configuration values."""
        config = ServerConfig()
        
        assert config.host == "0.0.0.0"
        assert config.port == 2048
        assert config.workers == 1
        assert config.debug is False
    
    def test_environment_variables(self):
        """Test server configuration from environment variables."""
        # Set environment variables
        os.environ["SERVER__HOST"] = "127.0.0.1"
        os.environ["SERVER__PORT"] = "3000"
        os.environ["SERVER__WORKERS"] = "4"
        os.environ["SERVER__DEBUG"] = "true"
        
        try:
            config = ServerConfig()
            
            assert config.host == "127.0.0.1"
            assert config.port == 3000
            assert config.workers == 4
            assert config.debug is True
        finally:
            # Clean up environment variables
            for key in ["SERVER__HOST", "SERVER__PORT", "SERVER__WORKERS", "SERVER__DEBUG"]:
                os.environ.pop(key, None)
    
    def test_port_validation(self):
        """Test port validation."""
        with pytest.raises(ValueError):
            ServerConfig(port=0)  # Too low
        
        with pytest.raises(ValueError):
            ServerConfig(port=70000)  # Too high


@pytest.mark.unit
class TestBrowserConfig:
    """Test browser configuration."""
    
    def test_default_values(self):
        """Test default browser configuration values."""
        config = BrowserConfig()
        
        assert config.headless is True
        assert config.port == 9222
        assert config.timeout == 30000
        assert config.user_agent is None
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080
    
    def test_viewport_validation(self):
        """Test viewport size validation."""
        with pytest.raises(ValueError):
            BrowserConfig(viewport_width=500)  # Too small
        
        with pytest.raises(ValueError):
            BrowserConfig(viewport_height=400)  # Too small


@pytest.mark.unit
class TestLogConfig:
    """Test logging configuration."""
    
    def test_default_values(self):
        """Test default log configuration values."""
        config = LogConfig()
        
        assert config.level == "INFO"
        assert config.format == "json"
        assert config.file_path is None
        assert config.max_size == "10MB"
        assert config.backup_count == 5
    
    def test_log_level_validation(self):
        """Test log level validation."""
        # Valid levels should work
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LogConfig(level=level)
            assert config.level == level
        
        # Invalid level should raise error
        with pytest.raises(ValueError):
            LogConfig(level="INVALID")
    
    def test_log_format_validation(self):
        """Test log format validation."""
        # Valid formats should work
        for fmt in ["json", "text"]:
            config = LogConfig(format=fmt)
            assert config.format == fmt
        
        # Invalid format should raise error
        with pytest.raises(ValueError):
            LogConfig(format="invalid")


@pytest.mark.unit
class TestMainConfig:
    """Test main configuration class."""
    
    def test_default_configuration(self):
        """Test default configuration creation."""
        config = Config()
        
        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.browser, BrowserConfig)
        assert isinstance(config.auth, AuthConfig)
        assert isinstance(config.log, LogConfig)
        assert isinstance(config.supported_models, list)
        assert len(config.supported_models) > 0
    
    def test_supported_models(self):
        """Test supported models list."""
        config = Config()
        
        expected_models = [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
        ]
        
        for model in expected_models:
            assert model in config.supported_models
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = Config()
        
        # Should not raise any exception with default values
        config.validate_config()
        
        # Test port conflict validation
        config.server.port = 9222
        config.browser.port = 9222
        
        with pytest.raises(ValueError, match="Server port and browser port cannot be the same"):
            config.validate_config()


@pytest.mark.unit
class TestConfigLoading:
    """Test configuration loading from files."""
    
    def test_load_from_yaml(self):
        """Test loading configuration from YAML file."""
        yaml_content = """
server:
  host: "localhost"
  port: 8080
  workers: 2
  debug: true

browser:
  headless: false
  timeout: 60000

log:
  level: "DEBUG"
  format: "text"

supported_models:
  - "gemini-2.5-pro"
  - "gemini-1.5-pro"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name
        
        try:
            config = Config.load_from_yaml(yaml_path)
            
            assert config.server.host == "localhost"
            assert config.server.port == 8080
            assert config.server.workers == 2
            assert config.server.debug is True
            assert config.browser.headless is False
            assert config.browser.timeout == 60000
            assert config.log.level == "DEBUG"
            assert config.log.format == "text"
            assert len(config.supported_models) == 2
        finally:
            os.unlink(yaml_path)
    
    def test_load_from_nonexistent_file(self):
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError):
            Config.load_from_yaml("/nonexistent/file.yaml")
    
    def test_save_to_yaml(self):
        """Test saving configuration to YAML file."""
        config = Config()
        config.server.host = "test-host"
        config.server.port = 9999
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_path = f.name
        
        try:
            config.save_to_yaml(yaml_path)
            
            # Load it back and verify
            loaded_config = Config.load_from_yaml(yaml_path)
            assert loaded_config.server.host == "test-host"
            assert loaded_config.server.port == 9999
        finally:
            os.unlink(yaml_path)


@pytest.mark.unit
class TestGlobalConfig:
    """Test global configuration functions."""
    
    def test_get_config(self):
        """Test getting global configuration."""
        config = get_config()
        assert isinstance(config, Config)
    
    def test_reload_config(self):
        """Test reloading global configuration."""
        # Set an environment variable
        os.environ["SERVER__PORT"] = "7777"
        
        try:
            config = reload_config()
            assert config.server.port == 7777
        finally:
            os.environ.pop("SERVER__PORT", None)
    
    def test_load_config_from_file(self):
        """Test loading global config from file."""
        yaml_content = """
server:
  port: 5555
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name
        
        try:
            config = load_config_from_file(yaml_path)
            assert config.server.port == 5555
        finally:
            os.unlink(yaml_path)
    
    def test_load_config_unsupported_format(self):
        """Test loading config from unsupported file format."""
        with pytest.raises(ValueError, match="Unsupported configuration file format"):
            load_config_from_file("config.json")


@pytest.mark.integration
class TestConfigIntegration:
    """Integration tests for configuration system."""
    
    def test_environment_override(self):
        """Test that environment variables override defaults."""
        # Set multiple environment variables
        env_vars = {
            "SERVER__HOST": "integration-test",
            "SERVER__PORT": "8888",
            "BROWSER__HEADLESS": "false",
            "LOG__LEVEL": "DEBUG",
        }
        
        for key, value in env_vars.items():
            os.environ[key] = value
        
        try:
            config = Config()
            
            assert config.server.host == "integration-test"
            assert config.server.port == 8888
            assert config.browser.headless is False
            assert config.log.level == "DEBUG"
        finally:
            for key in env_vars:
                os.environ.pop(key, None)
    
    def test_yaml_override_environment(self):
        """Test that YAML file can override environment variables."""
        # Set environment variable
        os.environ["SERVER__PORT"] = "9999"
        
        yaml_content = """
server:
  port: 1111
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name
        
        try:
            config = Config.load_from_yaml(yaml_path)
            # YAML should override environment
            assert config.server.port == 1111
        finally:
            os.unlink(yaml_path)
            os.environ.pop("SERVER__PORT", None)
