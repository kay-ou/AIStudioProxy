import asyncio
import time
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from src.core.handler import RequestHandler
from src.api.models import ChatCompletionRequest, Message, MessageRole, ChatCompletionResponse, Usage

@pytest.fixture
def mock_browser_manager():
    """Fixture for a mocked BrowserManager."""
    manager = MagicMock()
    manager.health_check = AsyncMock(return_value=True)
    manager.is_running = MagicMock(return_value=True)
    mock_page = MagicMock()
    manager.get_page = MagicMock(return_value=mock_page)
    return manager

@pytest.fixture
def mock_page_controller():
    """Fixture for a mocked PageController."""
    controller = MagicMock()
    controller.switch_model = AsyncMock()
    controller.send_message = AsyncMock()
    controller.wait_for_response = AsyncMock(return_value="Mocked AI response")
    controller.is_error_response = AsyncMock(return_value=None)
    
    async def mock_stream_generator():
        yield "Hello "
        yield "world"

    controller.start_streaming_response = MagicMock(return_value=mock_stream_generator())
    return controller

@pytest.fixture
def request_handler(mock_browser_manager):
    """Fixture for a RequestHandler instance."""
    with patch('src.core.handler.get_config', return_value=MagicMock()), \
         patch('src.utils.logger.LoggerMixin.logger', new_callable=MagicMock) as mock_logger:
        handler = RequestHandler(browser_manager=mock_browser_manager)
        yield handler

@pytest.fixture
def sample_request():
    """Fixture for a sample ChatCompletionRequest."""
    return ChatCompletionRequest(
        model="test-model",
        messages=[
            Message(role=MessageRole.USER, content="Hello, world!", name="test-user")
        ],
        stream=False,
        temperature=0.7,
        top_p=1.0,
        max_tokens=100,
        stop=None,
        presence_penalty=0.0,
        frequency_penalty=0.0,
        user="test-user"
    )

@pytest.mark.asyncio
async def test_handle_request_success(request_handler, sample_request, mock_page_controller):
    """Test successful handling of a non-streaming request with browser automation."""
    with patch('src.core.handler.PageController', return_value=mock_page_controller), \
         patch('src.core.handler.format_non_streaming_response') as mock_format_response, \
         patch('asyncio.create_task') as mock_create_task:

        mock_response_obj = ChatCompletionResponse(
            id="response-123",
            created=12345,
            model=sample_request.model,
            choices=[],
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        )
        mock_format_response.return_value = mock_response_obj

        response = await request_handler.handle_request(sample_request)

        assert response.id != "response-123"
        assert isinstance(response.id, str)
        
        mock_page_controller.switch_model.assert_awaited_once_with(sample_request.model)
        mock_page_controller.send_message.assert_awaited_once_with("Hello, world!")
        mock_page_controller.wait_for_response.assert_awaited_once()
        mock_page_controller.is_error_response.assert_awaited_once()
        mock_format_response.assert_called_once_with("Mocked AI response", sample_request.model, "Hello, world!")
        mock_create_task.assert_called_once()

@pytest.mark.asyncio
async def test_handle_request_browser_not_running(request_handler, sample_request):
    """Test handling request when browser is not running."""
    request_handler.browser_manager.is_running.return_value = False
    with pytest.raises(HTTPException) as exc_info:
        await request_handler.handle_request(sample_request)
    assert exc_info.value.status_code == 503

@pytest.mark.asyncio
async def test_handle_request_no_page_available(request_handler, sample_request):
    """Test handling request when no page is available."""
    request_handler.browser_manager.get_page.return_value = None
    with pytest.raises(HTTPException) as exc_info:
        await request_handler.handle_request(sample_request)
    assert exc_info.value.status_code == 503

@pytest.mark.asyncio
async def test_handle_request_ai_studio_error(request_handler, sample_request, mock_page_controller):
    """Test handling request when AI Studio returns an error."""
    mock_page_controller.is_error_response.return_value = "Something went wrong"
    with patch('src.core.handler.PageController', return_value=mock_page_controller), \
         pytest.raises(HTTPException) as exc_info:
        await request_handler.handle_request(sample_request)
    assert exc_info.value.status_code == 500

@pytest.mark.asyncio
async def test_handle_request_exception(request_handler, sample_request, mock_page_controller):
    """Test exception handling during a non-streaming request."""
    with patch('src.core.handler.PageController', return_value=mock_page_controller), \
         patch('src.core.handler.asyncio.create_task') as mock_create_task:
        mock_page_controller.send_message.side_effect = ValueError("Something went wrong")
        with pytest.raises(ValueError):
            await request_handler.handle_request(sample_request)
        assert request_handler.get_active_requests_count() == 1
        request_id = list(request_handler.active_requests.keys())[0]
        assert request_handler.active_requests[request_id]["status"] == "failed"
        request_handler.logger.error.assert_called_once()
        mock_create_task.assert_called_once()

@pytest.mark.asyncio
async def test_handle_stream_request_success(request_handler, sample_request, mock_page_controller):
    """Test successful handling of a streaming request."""
    sample_request.stream = True
    
    with patch('src.core.handler.PageController', return_value=mock_page_controller), \
         patch('src.core.handler.asyncio.create_task'):
        
        chunks = [chunk async for chunk in request_handler.handle_stream_request(sample_request)]

        assert len(chunks) == 5  # initial, "Hello ", "world", final, [DONE]
        
        # Verify calls that should now happen in streaming mode
        mock_page_controller.switch_model.assert_awaited_once_with(sample_request.model)
        mock_page_controller.send_message.assert_awaited_once_with("Hello, world!")
        mock_page_controller.start_streaming_response.assert_called_once()
        mock_page_controller.is_error_response.assert_awaited_once()

        # Verify chunk content
        initial_chunk = json.loads(chunks[0].replace("data: ", ""))
        assert initial_chunk['choices'][0]['delta']['role'] == 'assistant'
        
        chunk1 = json.loads(chunks[1].replace("data: ", ""))
        assert chunk1['choices'][0]['delta']['content'] == 'Hello '
        
        chunk2 = json.loads(chunks[2].replace("data: ", ""))
        assert chunk2['choices'][0]['delta']['content'] == 'world'

        final_chunk = json.loads(chunks[3].replace("data: ", ""))
        assert final_chunk['choices'][0]['finish_reason'] == 'stop'
        
        assert chunks[4] == "data: [DONE]\n\n"

@pytest.mark.asyncio
async def test_handle_stream_request_exception(request_handler, sample_request, mock_page_controller):
    """Test exception handling during a streaming request."""
    sample_request.stream = True
    
    # Simulate an error during streaming
    async def error_generator():
        yield "this part works"
        raise HTTPException(status_code=500, detail="AI Studio exploded")
        
    mock_page_controller.start_streaming_response.return_value = error_generator()

    with patch('src.core.handler.PageController', return_value=mock_page_controller), \
         patch('src.core.handler.asyncio.create_task'):
        
        chunks = [chunk async for chunk in request_handler.handle_stream_request(sample_request)]
        
        # We should get initial, one content chunk, one error chunk, and DONE
        assert len(chunks) == 4
        
        error_chunk_data = json.loads(chunks[2].replace("data: ", ""))
        assert error_chunk_data['error']['message'] == "AI Studio exploded"
        
        assert chunks[3] == "data: [DONE]\n\n"
        
        # Check that the request status is marked as failed
        request_id = list(request_handler.active_requests.keys())[0]
        assert request_handler.active_requests[request_id]["status"] == "failed"

@pytest.mark.asyncio
async def test_health_check(request_handler, mock_browser_manager):
    """Test the health_check method."""
    mock_browser_manager.health_check.return_value = True
    assert await request_handler.health_check() is True
    mock_browser_manager.health_check.return_value = False
    assert await request_handler.health_check() is False
    request_handler.browser_manager = None
    assert await request_handler.health_check() is True
    request_handler.browser_manager = mock_browser_manager
    mock_browser_manager.health_check.side_effect = Exception("Browser error")
    assert await request_handler.health_check() is False

@pytest.mark.asyncio
async def test_request_tracking_and_cleanup(request_handler, sample_request, mock_page_controller):
    """Test request tracking, stats, and cleanup."""
    assert request_handler.get_active_requests_count() == 0
    with patch('src.core.handler.PageController', return_value=mock_page_controller), \
         patch('src.core.handler.format_non_streaming_response') as mock_format_response, \
         patch('src.core.handler.asyncio.create_task') as mock_create_task:
        
        mock_format_response.return_value = ChatCompletionResponse(
            id="response-123", created=12345, model=sample_request.model, choices=[],
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        )
        
        # Call the handler
        await request_handler.handle_request(sample_request)
        
        # Check that the request is tracked
        assert request_handler.get_active_requests_count() == 1
        request_id = list(request_handler.active_requests.keys())[0]
        
        # Check that cleanup task was created
        mock_create_task.assert_called_once()

        # Manually call cleanup to test its logic without actual sleep
        await request_handler._cleanup_request(request_id, delay=0)
        assert request_handler.get_active_requests_count() == 0


@pytest.mark.asyncio
async def test_handle_stream_request_browser_not_running(request_handler, sample_request):
    """Test stream request when browser is not running."""
    sample_request.stream = True
    request_handler.browser_manager.is_running.return_value = False
    
    with patch('src.core.handler.asyncio.create_task'):
        chunks = [chunk async for chunk in request_handler.handle_stream_request(sample_request)]
        assert len(chunks) == 2
        error_data = json.loads(chunks[0].replace("data: ", ""))
        assert "Browser is not running" in error_data["error"]["message"]
        assert chunks[1] == "data: [DONE]\n\n"

@pytest.mark.asyncio
async def test_handle_stream_request_no_page(request_handler, sample_request):
    """Test stream request when no page is available."""
    sample_request.stream = True
    request_handler.browser_manager.get_page.return_value = None
    
    with patch('src.core.handler.asyncio.create_task'):
        chunks = [chunk async for chunk in request_handler.handle_stream_request(sample_request)]
        assert len(chunks) == 2
        error_data = json.loads(chunks[0].replace("data: ", ""))
        assert "No available page in browser" in error_data["error"]["message"]
        assert chunks[1] == "data: [DONE]\n\n"

@pytest.mark.asyncio
async def test_handle_stream_request_ai_studio_error(request_handler, sample_request, mock_page_controller):
    """Test stream request that results in an AI Studio error after streaming."""
    sample_request.stream = True
    mock_page_controller.is_error_response.return_value = "Post-stream error"
    
    with patch('src.core.handler.PageController', return_value=mock_page_controller), \
         patch('src.core.handler.asyncio.create_task'):
        chunks = [chunk async for chunk in request_handler.handle_stream_request(sample_request)]
        
        # initial, chunk1, chunk2, error, final, DONE
        assert len(chunks) == 5
        error_data = json.loads(chunks[3].replace("data: ", ""))
        assert "Post-stream error" in error_data["error"]["message"]
        assert chunks[4] == "data: [DONE]\n\n"

@pytest.mark.asyncio
async def test_get_request_stats(request_handler, sample_request):
    """Test the get_request_stats method."""
    # 1. No requests
    stats = request_handler.get_request_stats()
    assert stats["active_requests"] == 0
    assert stats["total_tracked"] == 0
    assert stats["average_duration"] == 0

    # 2. One active request
    request_id = "test-req-1"
    request_handler.active_requests[request_id] = {
        "start_time": time.time() - 10,
        "model": "test-model",
        "status": "processing"
    }
    stats = request_handler.get_request_stats()
    assert stats["active_requests"] == 1
    assert stats["total_tracked"] == 1
    assert stats["average_duration"] > 9

    # 3. One completed request
    request_handler.active_requests[request_id]["status"] = "completed"
    stats = request_handler.get_request_stats()
    assert stats["active_requests"] == 0
    assert stats["total_tracked"] == 1
