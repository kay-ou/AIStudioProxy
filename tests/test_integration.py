# -*- coding: utf-8 -*-
"""
AIStudioProxy Integration Tests
"""
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

# 标记整个文件中的所有测试都为集成测试
pytestmark = pytest.mark.integration


async def test_chat_completions_endpoint(
    async_client: AsyncClient,
    mock_request_handler: AsyncMock,
    mock_completion_response: dict,
    sample_chat_request: dict,
):
    """
    测试 /v1/chat/completions 端点是否能成功调用请求处理器并返回预期的响应。
    这是一个基础的集成测试，验证了从API路由到核心处理逻辑的连通性。
    """
    # 安排 mock_request_handler 在被调用时返回一个预设的成功响应
    mock_request_handler.handle_request.return_value = mock_completion_response

    # 发送 API 请求
    response = await async_client.post(
        "/v1/chat/completions",
        json=sample_chat_request,
        headers={"Authorization": "Bearer test-key"},
    )

    # 断言响应状态码
    assert response.status_code == 200

    # 断言响应内容与 mock 的返回值一致
    response_data = response.json()
    assert response_data == mock_completion_response

    # 验证 handle_request 方法确实被调用了一次
    mock_request_handler.handle_request.assert_called_once()


async def test_full_request_flow_with_mocked_browser(
    integration_client: AsyncClient,
    sample_chat_request: dict,
    monkeypatch,
):
    """
    测试一个完整的端到端请求流程，只 mock 掉底层的浏览器交互。

    这个测试验证了以下流程：
    1. API 路由接收请求。
    2. RequestHandler 正确处理请求。
    3. PageController 被调用以执行页面操作。
    4. 响应被正确格式化并返回。
    """
    # 模拟的来自 AI Studio 的原始响应
    mock_raw_response = "This is a mocked response from AI Studio."

    # 使用 monkeypatch 来 mock PageController 的 wait_for_response 方法
    # 这是与真实浏览器交互的最底层环节
    mock_wait = AsyncMock(return_value=mock_raw_response)
    monkeypatch.setattr(
        "aistudioproxy.core.handler.PageController.wait_for_response", mock_wait
    )

    # 我们还需要 mock 其他几个 PageController 的方法，因为它们也会被调用
    monkeypatch.setattr(
        "aistudioproxy.core.handler.PageController.switch_model", AsyncMock()
    )
    monkeypatch.setattr(
        "aistudioproxy.core.handler.PageController.send_message", AsyncMock()
    )
    monkeypatch.setattr(
        "aistudioproxy.core.handler.PageController.is_error_response",
        AsyncMock(return_value=None),
    )

    # 发送 API 请求
    response = await integration_client.post(
        "/v1/chat/completions",
        json=sample_chat_request,
        headers={"Authorization": "Bearer test-key"},
    )

    # 断言响应成功
    assert response.status_code == 200
    response_data = response.json()

    # 断言响应内容符合预期的格式，并且包含了我们 mock 的原始响应
    assert response_data["object"] == "chat.completion"
    assert response_data["model"] == sample_chat_request["model"]
    assert len(response_data["choices"]) == 1
    choice = response_data["choices"][0]
    assert choice["message"]["role"] == "assistant"
    assert choice["message"]["content"] == mock_raw_response
    assert choice["finish_reason"] == "stop"

    # 验证 mock 的方法被正确调用
    mock_wait.assert_called_once()
