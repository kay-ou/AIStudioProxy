import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.handler import RequestHandler
from src.api.models import ChatCompletionRequest, Message, MessageRole

@pytest.fixture
def mock_browser_manager():
    """Fixture for a mocked BrowserManager."""
    manager = MagicMock()
    manager.health_check = AsyncMock(return_value=True)
    return manager

@pytest.fixture
def request_handler(mock_browser_manager):
    """Fixture for a RequestHandler instance."""
    with patch('src.core.handler.get_config', return_value=MagicMock()), \
         patch('src.utils.logger.LoggerMixin.logger', new_callable=MagicMock) as mock_logger:
        handler = RequestHandler(browser_manager=mock_browser_manager)
        # Since we patched the mixin's logger, the instance's logger will be the mock
        yield handler

@pytest.fixture
def sample_request():
    """Fixture for a sample ChatCompletionRequest."""
    return ChatCompletionRequest(
        model="test-model",
        messages=[
            Message(role=MessageRole.USER, content="Hello, world!", name="test-user")
        ],
        temperature=0.7,
        top_p=1.0,
        max_tokens=100,
        stream=False,
        stop=None,
        presence_penalty=0.0,
        frequency_penalty=0.0,
        user="test-user"
    )

@pytest.mark.asyncio
async def test_handle_request_success(request_handler, sample_request):
    """Test successful handling of a non-streaming request."""
    with patch.object(request_handler, '_create_placeholder_response', new_callable=AsyncMock) as mock_create_response, \
         patch('asyncio.create_task') as mock_create_task:

        mock_create_response.return_value = MagicMock(id="response-123")
        
        response = await request_handler.handle_request(sample_request)

        assert response.id == "response-123"
        assert request_handler.get_active_requests_count() == 1
        
        request_id = list(request_handler.active_requests.keys())[0]
        assert request_handler.active_requests[request_id]["status"] == "completed"

        mock_create_response.assert_awaited_once()
        mock_create_task.assert_called_once()

@pytest.mark.asyncio
async def test_handle_request_exception(request_handler, sample_request):
    """Test exception handling during a non-streaming request."""
    with patch.object(request_handler, '_create_placeholder_response', new_callable=AsyncMock) as mock_create_response, \
         patch('asyncio.create_task') as mock_create_task:

        mock_create_response.side_effect = ValueError("Something went wrong")

        with pytest.raises(ValueError):
            await request_handler.handle_request(sample_request)

        assert request_handler.get_active_requests_count() == 1
        request_id = list(request_handler.active_requests.keys())[0]
        assert request_handler.active_requests[request_id]["status"] == "failed"
        
        request_handler.logger.error.assert_called_once()
        mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_handle_stream_request_success(request_handler, sample_request):
    """Test successful handling of a streaming request."""
    sample_request.stream = True
    
    with patch.object(request_handler, '_create_placeholder_stream') as mock_create_stream, \
         patch('asyncio.create_task') as mock_create_task:

        async def mock_stream_generator():
            yield "data: chunk1\n\n"
            yield "data: chunk2\n\n"

        mock_create_stream.return_value = mock_stream_generator()

        chunks = [chunk async for chunk in request_handler.handle_stream_request(sample_request)]

        assert len(chunks) == 2
        assert chunks[0] == "data: chunk1\n\n"
        assert request_handler.get_active_requests_count() == 1
        
        request_id = list(request_handler.active_requests.keys())[0]
        assert request_handler.active_requests[request_id]["status"] == "completed"

        mock_create_stream.assert_called_once()
        mock_create_task.assert_called_once()

@pytest.mark.asyncio
async def test_handle_stream_request_exception(request_handler, sample_request):
    """Test exception handling during a streaming request."""
    sample_request.stream = True

    with patch.object(request_handler, '_create_placeholder_stream') as mock_create_stream, \
         patch('asyncio.create_task') as mock_create_task:

        async def mock_stream_generator():
            raise ValueError("Stream error")
            yield # This yield is needed to make it an async generator

        mock_create_stream.return_value = mock_stream_generator()

        with pytest.raises(ValueError):
            async for _ in request_handler.handle_stream_request(sample_request):
                pass

        assert request_handler.get_active_requests_count() == 1
        request_id = list(request_handler.active_requests.keys())[0]
        assert request_handler.active_requests[request_id]["status"] == "failed"
        
        request_handler.logger.error.assert_called_once()
        mock_create_task.assert_called_once()

@pytest.mark.asyncio
async def test_health_check(request_handler, mock_browser_manager):
    """Test the health_check method."""
    # Test with healthy browser manager
    mock_browser_manager.health_check.return_value = True
    assert await request_handler.health_check() is True
    mock_browser_manager.health_check.assert_awaited_once()

    # Test with unhealthy browser manager
    mock_browser_manager.health_check.return_value = False
    assert await request_handler.health_check() is False

    # Test with no browser manager
    request_handler.browser_manager = None
    assert await request_handler.health_check() is True

    # Test with exception
    mock_browser_manager.health_check.side_effect = Exception("Browser error")
    request_handler.browser_manager = mock_browser_manager
    assert await request_handler.health_check() is False
    request_handler.logger.error.assert_called_once()

@pytest.mark.asyncio
async def test_request_tracking_and_cleanup(request_handler, sample_request):
    """Test request tracking, stats, and cleanup."""
    assert request_handler.get_active_requests_count() == 0
    assert request_handler.get_request_stats()["total_tracked"] == 0

    with patch.object(request_handler, '_create_placeholder_response', new_callable=AsyncMock), \
         patch('asyncio.sleep', new_callable=AsyncMock): # Patch sleep to speed up cleanup

        await request_handler.handle_request(sample_request)

        assert request_handler.get_active_requests_count() == 1
        stats = request_handler.get_request_stats()
        assert stats["total_tracked"] == 1
        assert stats["active_requests"] == 0 # It's completed, not processing

        # Manually trigger cleanup to test
        request_id = list(request_handler.active_requests.keys())[0]
        await request_handler._cleanup_request(request_id, delay=0)
        
        assert request_handler.get_active_requests_count() == 0
