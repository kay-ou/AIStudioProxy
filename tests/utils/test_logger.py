"""
Tests for logging system.

This module contains unit tests for the structured logging system.
"""

import json
import logging
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.logger import (
    setup_logger,
    get_logger,
    init_logging,
    LoggerMixin,
    _parse_size,
    _configure_stdlib_logging,
    _configure_structlog,
)
from src.utils.config import LogConfig


@pytest.mark.unit
class TestParseSize:
    """Test size parsing utility."""
    
    def test_parse_bytes(self):
        """Test parsing byte values."""
        assert _parse_size("1024") == 1024
        assert _parse_size("1024B") == 1024
        assert _parse_size("1024 B") == 1024
    
    def test_parse_kilobytes(self):
        """Test parsing kilobyte values."""
        assert _parse_size("1KB") == 1024
        assert _parse_size("2KB") == 2048
        assert _parse_size("1.5KB") == int(1.5 * 1024)
    
    def test_parse_megabytes(self):
        """Test parsing megabyte values."""
        assert _parse_size("1MB") == 1024 * 1024
        assert _parse_size("10MB") == 10 * 1024 * 1024
        assert _parse_size("2.5MB") == int(2.5 * 1024 * 1024)
    
    def test_parse_gigabytes(self):
        """Test parsing gigabyte values."""
        assert _parse_size("1GB") == 1024 * 1024 * 1024
        assert _parse_size("2GB") == 2 * 1024 * 1024 * 1024
    
    def test_parse_invalid(self):
        """Test parsing invalid size strings."""
        # Should return default value (10MB) for invalid input
        assert _parse_size("invalid") == 10 * 1024 * 1024
        assert _parse_size("") == 10 * 1024 * 1024
        assert _parse_size("XYZGB") == 10 * 1024 * 1024


@pytest.mark.unit
class TestLoggerSetup:
    """Test logger setup and configuration."""
    
    def test_setup_logger_default(self):
        """Test logger setup with default configuration."""
        log_config = LogConfig()
        logger = setup_logger(log_config)
        
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')
    
    def test_setup_logger_with_file(self):
        """Test logger setup with file output."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            log_file = f.name
        
        try:
            log_config = LogConfig(
                level="DEBUG",
                format="json",
                file_path=log_file,
                max_size="1MB",
                backup_count=3
            )
            
            logger = setup_logger(log_config)
            logger.info("Test message")
            
            # Check that log file was created
            assert Path(log_file).exists()
            
            # Check log content
            with open(log_file, 'r') as f:
                log_content = f.read()
                assert "Test message" in log_content
        finally:
            Path(log_file).unlink(missing_ok=True)
    
    def test_setup_logger_text_format(self):
        """Test logger setup with text format."""
        log_config = LogConfig(format="text")
        logger = setup_logger(log_config)
        
        # Should not raise any exceptions
        logger.info("Test text format")
    
    @patch('src.utils.logger.logging.getLogger')
    def test_configure_stdlib_logging(self, mock_get_logger):
        """Test standard library logging configuration."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        log_config = LogConfig(level="DEBUG")
        _configure_stdlib_logging(log_config)
        
        mock_logger.setLevel.assert_called_with(logging.DEBUG)
        mock_logger.handlers.clear.assert_called_once()
        assert mock_logger.addHandler.called
    
    @patch('structlog.configure')
    def test_configure_structlog(self, mock_configure):
        """Test structlog configuration."""
        log_config = LogConfig(format="json")
        _configure_structlog(log_config)
        
        mock_configure.assert_called_once()
        call_args = mock_configure.call_args[1]
        assert 'processors' in call_args
        assert 'context_class' in call_args
        assert 'logger_factory' in call_args


@pytest.mark.unit
class TestLoggerMixin:
    """Test LoggerMixin functionality."""
    
    def test_logger_property(self):
        """Test logger property access."""
        class TestClass(LoggerMixin):
            pass
        
        obj = TestClass()
        logger = obj.logger
        
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
    
    def test_log_method_call(self):
        """Test method call logging."""
        class TestClass(LoggerMixin):
            def test_method(self, arg1, arg2=None):
                self.log_method_call("test_method", arg1=arg1, arg2=arg2)
        
        obj = TestClass()
        
        # Should not raise any exceptions
        obj.test_method("value1", arg2="value2")
    
    def test_log_method_result(self):
        """Test method result logging."""
        class TestClass(LoggerMixin):
            def test_method(self):
                result = "test_result"
                self.log_method_result("test_method", result=result)
                return result
        
        obj = TestClass()
        result = obj.test_method()
        
        assert result == "test_result"
    
    def test_log_error(self):
        """Test error logging."""
        class TestClass(LoggerMixin):
            def test_method(self):
                try:
                    raise ValueError("Test error")
                except Exception as e:
                    self.log_error(e, context={"method": "test_method"})
        
        obj = TestClass()
        
        # Should not raise any exceptions
        obj.test_method()


@pytest.mark.unit
class TestLoggerFunctions:
    """Test logger utility functions."""
    
    def test_get_logger(self):
        """Test get_logger function."""
        logger = get_logger("test_logger")
        
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
    
    def test_get_logger_no_name(self):
        """Test get_logger without name."""
        logger = get_logger()
        
        assert logger is not None
    
    def test_init_logging(self):
        """Test init_logging function."""
        logger = init_logging()
        
        assert logger is not None
        assert hasattr(logger, 'info')


@pytest.mark.integration
class TestLoggingIntegration:
    """Integration tests for logging system."""
    
    def test_full_logging_flow(self):
        """Test complete logging flow."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as f:
            log_file = f.name
        
        try:
            # Setup logger with file output
            log_config = LogConfig(
                level="INFO",
                format="json",
                file_path=log_file
            )
            
            logger = setup_logger(log_config)
            
            # Log various message types
            logger.info("Info message", key="value")
            logger.warning("Warning message", count=42)
            logger.error("Error message", error_code=500)
            
            # Read and verify log file
            with open(log_file, 'r') as f:
                log_lines = f.readlines()
            
            assert len(log_lines) >= 3
            
            # Parse JSON log entries
            for line in log_lines:
                if line.strip():
                    log_entry = json.loads(line.strip())
                    assert 'timestamp' in log_entry
                    assert 'level' in log_entry
                    assert 'event' in log_entry
        finally:
            Path(log_file).unlink(missing_ok=True)
    
    def test_logger_mixin_integration(self):
        """Test LoggerMixin in realistic scenario."""
        class ServiceClass(LoggerMixin):
            def __init__(self):
                self.counter = 0
            
            def process_request(self, request_id: str):
                self.log_method_call("process_request", request_id=request_id)
                
                try:
                    # Simulate processing
                    self.counter += 1
                    result = f"processed_{self.counter}"
                    
                    self.log_method_result("process_request", result=result)
                    return result
                    
                except Exception as e:
                    self.log_error(e, context={"request_id": request_id})
                    raise
        
        service = ServiceClass()
        
        # Should work without exceptions
        result1 = service.process_request("req_001")
        result2 = service.process_request("req_002")
        
        assert result1 == "processed_1"
        assert result2 == "processed_2"
    
    def test_concurrent_logging(self):
        """Test logging under concurrent access."""
        import threading
        import time
        
        logger = get_logger("concurrent_test")
        results = []
        
        def log_worker(worker_id: int):
            for i in range(10):
                logger.info(f"Worker {worker_id} message {i}", worker_id=worker_id, message_id=i)
                time.sleep(0.01)  # Small delay
            results.append(f"worker_{worker_id}_done")
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=log_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All workers should complete
        assert len(results) == 3
        assert "worker_0_done" in results
        assert "worker_1_done" in results
        assert "worker_2_done" in results
