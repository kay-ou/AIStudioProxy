# -*- coding: utf-8 -*-
"""
Tests for the configuration system.
"""

import os
from unittest.mock import patch

import pytest
import yaml

from aistudioproxy.utils.config import Config, get_config, load_config_from_file, ServerConfig, BrowserConfig

@pytest.fixture
def sample_config_dict():
    """Fixture for a sample configuration dictionary."""
    return {
        "server": {"host": "127.0.0.1", "port": 8000},
        "browser": {"headless": False},
    }

def test_config_loading_from_dict(sample_config_dict):
    """Test that the Config model can be loaded from a dictionary."""
    config = Config(**sample_config_dict)
    assert config.server.host == "127.0.0.1"
    assert config.server.port == 8000
    assert not config.browser.headless

@patch.dict(os.environ, {"SERVER__HOST": "0.0.0.0", "BROWSER__HEADLESS": "true"})
def test_config_loading_from_env_vars():
    """Test that the Config model can be loaded from environment variables."""
    config = get_config()
    assert config.server.host == "0.0.0.0"
    assert config.browser.headless

def test_load_config_from_yaml(tmp_path, sample_config_dict):
    """Test loading configuration from a YAML file."""
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(sample_config_dict, f)

    config = load_config_from_file(str(config_path))
    assert config.server.port == 8000
    assert not config.browser.headless

def test_config_validation():
    """Test that configuration validation works as expected."""
    with pytest.raises(ValueError, match="Server port and browser port cannot be the same"):
        config = Config()
        config.server.port = 9000
        config.browser.port = 9000
        config.validate_config()
