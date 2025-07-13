import pytest
from unittest.mock import patch, MagicMock

from src.main import main
from src.api.app import app

@patch('uvicorn.run')
@patch('src.main.get_config')
@patch('src.main.init_logging')
@patch('src.main.setup_signal_handlers')
@patch('argparse.ArgumentParser')
def test_main(mock_arg_parser, mock_setup_signals, mock_init_logging, mock_get_config, mock_run):
    """Test the main function."""
    # Mock command line arguments
    mock_args = MagicMock()
    mock_args.config = None
    mock_args.host = "127.0.0.1"
    mock_args.port = 8000
    mock_args.workers = 4
    mock_args.reload = True
    mock_args.debug = True
    mock_arg_parser.return_value.parse_args.return_value = mock_args

    # Mock config
    mock_config = MagicMock()
    mock_get_config.return_value = mock_config

    main()

    # Assertions
    mock_init_logging.assert_called_once()
    mock_setup_signals.assert_called_once()

    assert mock_config.server.host == "127.0.0.1"
    assert mock_config.server.port == 8000
    assert mock_config.server.workers == 4
    assert mock_config.development.reload is True
    assert mock_config.server.debug is True

    mock_run.assert_called_once_with(
        "src.api.app:app",
        host="127.0.0.1",
        port=8000,
        workers=1,  # Workers should be 1 when reload is True
        reload=True,
        log_config=None,
        access_log=False,
    )