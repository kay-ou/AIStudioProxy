"""
Response formatting utilities.

This module provides functions to convert raw AI Studio responses into
OpenAI-compatible formats.
"""

import time
import uuid
from typing import Any, Dict

import tiktoken

from ..api.models import (
    ChatCompletionChoice,
    ChatCompletionResponse,
    Message,
    MessageRole,
    Usage,
)

# Initialize tokenizer
try:
    encoding = tiktoken.get_encoding("cl100k_base")
except Exception:
    encoding = None


def _count_tokens(text: str) -> int:
    """Counts tokens using tiktoken, with a fallback to word count."""
    if encoding:
        return len(encoding.encode(text))
    return len(text.split())


def format_non_streaming_response(
    raw_content: str, request_model: str, prompt: str
) -> ChatCompletionResponse:
    """
    Formats a raw text response into a ChatCompletionResponse object.

    Args:
        raw_content: The raw text content from the AI.
        request_model: The model used for the request.
        prompt: The user's prompt.

    Returns:
        A ChatCompletionResponse object.
    """
    request_id = str(uuid.uuid4())
    created_time = int(time.time())

    prompt_tokens = _count_tokens(prompt)
    completion_tokens = _count_tokens(raw_content)
    total_tokens = prompt_tokens + completion_tokens

    return ChatCompletionResponse(
        id=request_id,
        created=created_time,
        model=request_model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=Message(
                    role=MessageRole.ASSISTANT, content=raw_content, name=None
                ),
                finish_reason="stop",
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
    )


import json


def format_streaming_chunk(content_chunk: str, model: str, request_id: str) -> str:
    """
    Formats a content chunk into an OpenAI-compatible SSE string.

    Args:
        content_chunk: The chunk of text content.
        model: The model used for the request.
        request_id: The ID of the request.

    Returns:
        A string formatted as a Server-Sent Event.
    """
    chunk_data = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content_chunk},
                "finish_reason": None,
            }
        ],
    }
    return f"data: {json.dumps(chunk_data)}\n\n"


def format_initial_stream_chunk(model: str, request_id: str) -> str:
    """
    Formats the initial chunk for a streaming response with the role.
    """
    chunk_data = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant"},
                "finish_reason": None,
            }
        ],
    }
    return f"data: {json.dumps(chunk_data)}\n\n"


def format_final_stream_chunk(model: str, request_id: str) -> str:
    """
    Formats the final chunk for a streaming response.
    """
    chunk_data = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    return f"data: {json.dumps(chunk_data)}\n\n"
