# -*- coding: utf-8 -*-
"""
Tests for the logging system.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from aistudioproxy.utils.config import LogConfig
from aistudioproxy.utils.logger import _parse_size, setup_logger


@pytest.fixture
def mock_log_config():
    """Fixture for a mock log configuration."""
    return LogConfig(level="DEBUG", format="json", file_path=None)


def test_setup_logger(mock_log_config):
    """Test that the logger is set up correctly."""
    with patch("aistudioproxy.utils.logger.logging.getLogger") as mock_get_logger:
        logger = setup_logger(mock_log_config)
        assert logger is not None
        mock_get_logger.assert_called()


def test_parse_size():
    """Test the _parse_size function."""
    assert _parse_size("10B") == 10
    assert _parse_size("1KB") == 1024
    assert _parse_size("2.5MB") == int(2.5 * 1024 * 1024)
    assert _parse_size("1GB") == 1024**3
    assert _parse_size("invalid") == 10 * 1024 * 1024  # Default value


def test_logger_with_file_output(tmp_path, mock_log_config):
    """Test that the logger writes to a file when a path is provided."""
    log_file = tmp_path / "test.log"
    mock_log_config.file_path = str(log_file)

    with (
        patch(
            "aistudioproxy.utils.logger.logging.handlers.RotatingFileHandler"
        ) as mock_handler,
        patch("aistudioproxy.utils.logger.logging.getLogger") as mock_get_logger,
    ):

        # Mock the logger and its handlers to prevent conflicts with pytest's logging capture
        mock_logger = MagicMock()
        mock_logger.handlers = []
        mock_get_logger.return_value = mock_logger

        setup_logger(mock_log_config)
        mock_handler.assert_called_with(
            filename=log_file,
            maxBytes=10485760,  # Default 10MB
            backupCount=5,
            encoding="utf-8",
        )
