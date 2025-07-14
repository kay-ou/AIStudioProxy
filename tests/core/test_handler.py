import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest
from fastapi import HTTPException

from aistudioproxy.api.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Message,
    MessageRole,
    Usage,
)
from aistudioproxy.browser.manager import BrowserManager
from aistudioproxy.core.handler import RequestHandler


@pytest.fixture
def mock_browser_manager():
    """
    Provides a precisely configured mock for the BrowserManager using create_autospec.
    This ensures that the mock's API matches the real BrowserManager, preventing
    errors from incorrect mock setups (e.g., awaiting a sync method).
    """
    # Use create_autospec to create a mock that mirrors the BrowserManager's interface
    mock = create_autospec(BrowserManager, instance=True)

    # is_running is a synchronous method, so it's mocked with a simple return value.
    mock.is_running.return_value = True

    # health_check is an async method, so its mock needs to be awaitable.
    mock.health_check = AsyncMock(return_value=True)

    # get_page and release_page are async and part of the page pool mechanism.
    mock_page = AsyncMock()
    mock.get_page = AsyncMock(return_value=mock_page)
    mock.release_page = AsyncMock()

    return mock


from aistudioproxy.browser.page_controller import PageController


@pytest.fixture
def mock_page_controller():
    """Fixture for a mocked PageController using autospec."""
    mock = create_autospec(PageController, instance=True)
    mock.switch_model = AsyncMock()
    mock.send_message = AsyncMock()
    mock.wait_for_response = AsyncMock(return_value="Mocked AI response")
    mock.is_error_response = AsyncMock(return_value=None)

    async def mock_stream_generator():
        yield "Hello "
        yield "world"

    mock.start_streaming_response = MagicMock(return_value=mock_stream_generator())
    return mock


@pytest.fixture
async def request_handler(mock_browser_manager, mock_page_controller):
    """Fixture for a RequestHandler instance with mocked dependencies."""
    mock_config = MagicMock()
    mock_config.performance.max_concurrent_requests = 10
    mock_config.performance.cleanup_delay = 0

    with (
        patch("aistudioproxy.core.handler.get_config", return_value=mock_config),
        patch("aistudioproxy.utils.logger.LoggerMixin.logger", new_callable=MagicMock),
        patch(
            "aistudioproxy.core.handler.PageController",
            return_value=mock_page_controller,
        ),
    ):
        handler = RequestHandler(browser_manager=mock_browser_manager)
        yield handler
        # Teardown logic is no longer needed here as we are not running real tasks


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
        user="test-user",
    )


@pytest.mark.asyncio
async def test_handle_request_success(
    request_handler, sample_request, mock_page_controller
):
    """Test successful handling of a non-streaming request with browser automation."""
    with (
        patch(
            "aistudioproxy.core.handler.format_non_streaming_response"
        ) as mock_format_response,
        patch.object(
            request_handler, "_cleanup_request", new_callable=AsyncMock
        ) as mock_cleanup,
    ):

        mock_response_obj = ChatCompletionResponse(
            id="response-123",
            created=12345,
            model=sample_request.model,
            choices=[],
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )
        mock_format_response.return_value = mock_response_obj

        response = await request_handler.handle_request(sample_request)

        assert response.id != "response-123"
        assert isinstance(response.id, str)

        mock_page_controller.switch_model.assert_awaited_once_with(sample_request.model)
        mock_page_controller.send_message.assert_awaited_once_with("Hello, world!")
        mock_page_controller.wait_for_response.assert_awaited_once()
        mock_page_controller.is_error_response.assert_awaited_once()
        mock_format_response.assert_called_once_with(
            "Mocked AI response", sample_request.model, "Hello, world!"
        )

        # Allow the event loop to run the cleanup task
        await asyncio.sleep(0)
        mock_cleanup.assert_awaited_once()


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
async def test_handle_request_ai_studio_error(
    request_handler, sample_request, mock_page_controller
):
    """Test handling request when AI Studio returns an error."""
    mock_page_controller.is_error_response.return_value = "Something went wrong"
    with pytest.raises(HTTPException) as exc_info:
        await request_handler.handle_request(sample_request)
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_handle_request_exception(
    request_handler, sample_request, mock_page_controller
):
    """Test exception handling during a non-streaming request."""
    with patch.object(
        request_handler, "_cleanup_request", new_callable=AsyncMock
    ) as mock_cleanup:
        mock_page_controller.send_message.side_effect = ValueError(
            "Something went wrong"
        )
        with pytest.raises(ValueError):
            await request_handler.handle_request(sample_request)
        assert request_handler.get_active_requests_count() == 1
        request_id = list(request_handler.active_requests.keys())[0]
        assert request_handler.active_requests[request_id]["status"] == "failed"
        request_handler.logger.error.assert_called_once()

        # Allow the event loop to run the cleanup task
        await asyncio.sleep(0)
        mock_cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_stream_request_success(
    request_handler, sample_request, mock_page_controller
):
    """Test successful handling of a streaming request."""
    sample_request.stream = True

    with patch.object(request_handler, "_cleanup_request", new_callable=AsyncMock):
        chunks = [
            chunk
            async for chunk in request_handler.handle_stream_request(sample_request)
        ]

        assert len(chunks) == 5  # initial, "Hello ", "world", final, [DONE]

        # Verify calls that should now happen in streaming mode
        mock_page_controller.switch_model.assert_awaited_once_with(sample_request.model)
        mock_page_controller.send_message.assert_awaited_once_with("Hello, world!")
        mock_page_controller.start_streaming_response.assert_called_once()
        mock_page_controller.is_error_response.assert_awaited_once()

        # Verify chunk content
        initial_chunk = json.loads(chunks[0].replace("data: ", ""))
        assert initial_chunk["choices"][0]["delta"]["role"] == "assistant"

        chunk1 = json.loads(chunks[1].replace("data: ", ""))
        assert chunk1["choices"][0]["delta"]["content"] == "Hello "

        chunk2 = json.loads(chunks[2].replace("data: ", ""))
        assert chunk2["choices"][0]["delta"]["content"] == "world"

        final_chunk = json.loads(chunks[3].replace("data: ", ""))
        assert final_chunk["choices"][0]["finish_reason"] == "stop"

        assert chunks[4] == "data: [DONE]\n\n"


@pytest.mark.asyncio
async def test_handle_stream_request_exception(
    request_handler, sample_request, mock_page_controller
):
    """Test exception handling during a streaming request."""
    sample_request.stream = True

    # Simulate an error during streaming
    async def error_generator():
        yield "this part works"
        raise HTTPException(status_code=500, detail="AI Studio exploded")

    mock_page_controller.start_streaming_response.return_value = error_generator()

    with patch.object(request_handler, "_cleanup_request", new_callable=AsyncMock):
        chunks = [
            chunk
            async for chunk in request_handler.handle_stream_request(sample_request)
        ]

        # We should get initial, one content chunk, one error chunk, and DONE
        assert len(chunks) == 4

        error_chunk_data = json.loads(chunks[2].replace("data: ", ""))
        assert error_chunk_data["error"]["message"] == "AI Studio exploded"

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
async def test_request_tracking_and_cleanup(
    request_handler, sample_request, mock_page_controller
):
    """Test request tracking, stats, and cleanup."""
    assert request_handler.get_active_requests_count() == 0
    with patch(
        "aistudioproxy.core.handler.format_non_streaming_response"
    ) as mock_format_response:

        mock_format_response.return_value = ChatCompletionResponse(
            id="response-123",
            created=12345,
            model=sample_request.model,
            choices=[],
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

        # Call the handler
        await request_handler.handle_request(sample_request)

        # Check that the request is tracked
        assert request_handler.get_active_requests_count() == 1
        request_id = list(request_handler.active_requests.keys())[0]

        # Allow the event loop to run the cleanup task
        await asyncio.sleep(0)

        # After cleanup, the request should be gone
        assert request_handler.get_active_requests_count() == 0


@pytest.mark.asyncio
async def test_handle_stream_request_browser_not_running(
    request_handler, sample_request
):
    """Test stream request when browser is not running."""
    sample_request.stream = True
    request_handler.browser_manager.is_running.return_value = False

    with patch.object(request_handler, "_cleanup_request", new_callable=AsyncMock):
        chunks = [
            chunk
            async for chunk in request_handler.handle_stream_request(sample_request)
        ]
        assert len(chunks) == 2
        error_data = json.loads(chunks[0].replace("data: ", ""))
        assert "Browser is not running" in error_data["error"]["message"]
        assert chunks[1] == "data: [DONE]\n\n"


@pytest.mark.asyncio
async def test_handle_stream_request_no_page(request_handler, sample_request):
    """Test stream request when no page is available."""
    sample_request.stream = True
    request_handler.browser_manager.get_page.return_value = None

    with patch.object(request_handler, "_cleanup_request", new_callable=AsyncMock):
        chunks = [
            chunk
            async for chunk in request_handler.handle_stream_request(sample_request)
        ]
        assert len(chunks) == 2
        error_data = json.loads(chunks[0].replace("data: ", ""))
        assert "No available page in browser" in error_data["error"]["message"]
        assert chunks[1] == "data: [DONE]\n\n"


@pytest.mark.asyncio
async def test_handle_stream_request_ai_studio_error(
    request_handler, sample_request, mock_page_controller
):
    """Test stream request that results in an AI Studio error after streaming."""
    sample_request.stream = True
    mock_page_controller.is_error_response.return_value = "Post-stream error"

    with patch.object(request_handler, "_cleanup_request", new_callable=AsyncMock):
        chunks = [
            chunk
            async for chunk in request_handler.handle_stream_request(sample_request)
        ]

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
        "status": "processing",
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


@pytest.mark.asyncio
async def test_concurrency_limit(request_handler, sample_request, mock_page_controller):
    """Test that the request handler respects the concurrency limit."""
    # Set a low concurrency limit for the test
    request_handler.semaphore = asyncio.Semaphore(2)

    running_tasks = 0
    max_concurrent_tasks = 0
    task_started_event = asyncio.Event()

    async def long_running_task(*args, **kwargs):
        nonlocal running_tasks, max_concurrent_tasks
        running_tasks += 1
        max_concurrent_tasks = max(max_concurrent_tasks, running_tasks)
        await task_started_event.wait()
        running_tasks -= 1
        return "Mocked AI response"

    # We need to use an AsyncMock here to properly handle the await
    mock_page_controller.wait_for_response = AsyncMock(side_effect=long_running_task)

    # Start more tasks than the concurrency limit
    tasks = [
        asyncio.create_task(request_handler.handle_request(sample_request))
        for _ in range(5)
    ]

    # Allow some time for tasks to hit the semaphore
    await asyncio.sleep(0.01)
    assert max_concurrent_tasks == 2
    assert running_tasks == 2

    # Allow the next batch of tasks to run
    task_started_event.set()
    await asyncio.sleep(0.01)
    # The original 2 tasks are finishing, and the next 2 are starting
    assert max_concurrent_tasks == 2

    # Allow all tasks to complete
    await asyncio.gather(*tasks)

    # The max concurrency should never have been exceeded
    assert max_concurrent_tasks == 2
