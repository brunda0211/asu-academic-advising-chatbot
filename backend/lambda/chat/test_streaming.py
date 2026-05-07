"""Tests for Task 18 — Bedrock converse_stream and SSE streaming.

Validates correctness properties P16–P23.
Uses unittest.mock to patch boto3 clients so no AWS credentials are needed.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Patch boto3 clients before importing the handler module
# ---------------------------------------------------------------------------
with patch('boto3.client', return_value=MagicMock()):
    import sys
    import os

    _chat_dir = os.path.join(os.path.dirname(__file__))
    if _chat_dir not in sys.path:
        sys.path.insert(0, _chat_dir)

    import index as handler  # type: ignore[import-untyped]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
REQUEST_ID = 'test-request-id-streaming'

SYSTEM_PROMPT = 'You are GUIDE, an AI academic advising assistant.'
USER_MESSAGE = 'What are the prerequisites for CSE 310?'
CITATIONS = ['s3://bucket/doc1.pdf', 's3://bucket/doc2.pdf']


def _make_stream_events(
    text_chunks: list[str],
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> list[dict[str, Any]]:
    """Build a list of converse_stream events."""
    events: list[dict[str, Any]] = []
    for chunk in text_chunks:
        events.append({
            'contentBlockDelta': {
                'delta': {'text': chunk},
            },
        })
    events.append({'messageStop': {'stopReason': 'end_turn'}})
    events.append({
        'metadata': {
            'usage': {
                'inputTokens': input_tokens,
                'outputTokens': output_tokens,
            },
        },
    })
    return events


def _make_valid_event() -> dict[str, Any]:
    """Build a valid API Gateway proxy event for end-to-end tests."""
    return {
        'body': json.dumps({
            'message': USER_MESSAGE,
            'session_id': 'session_1234567890123_abcdefghijk',
            'context': {
                'academic_year': 'Junior',
                'major': 'Computer Science',
                'advising_topic': 'Course Planning',
            },
        }),
    }


def _parse_sse_body(body: str) -> list[dict[str, Any]]:
    """Parse an SSE body string into a list of event payloads."""
    events = []
    for line in body.split('\n'):
        line = line.strip()
        if line.startswith('data: '):
            events.append(json.loads(line[6:]))
    return events


# ---------------------------------------------------------------------------
# 18.1 — converse_stream called with correct model ID (P16)
# ---------------------------------------------------------------------------
class TestModelIdCorrectness:
    """P16: Model ID Correctness — must use MODEL_ID env var."""

    def test_converse_stream_called_with_model_id(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        mock_client.converse_stream.assert_called_once()
        call_kwargs = mock_client.converse_stream.call_args[1]
        assert call_kwargs['modelId'] == handler.MODEL_ID

    def test_converse_stream_called_with_user_message(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        call_kwargs = mock_client.converse_stream.call_args[1]
        assert call_kwargs['messages'] == [
            {'role': 'user', 'content': [{'text': USER_MESSAGE}]},
        ]

    def test_converse_stream_called_with_system_prompt(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        call_kwargs = mock_client.converse_stream.call_args[1]
        assert call_kwargs['system'] == [{'text': SYSTEM_PROMPT}]


# ---------------------------------------------------------------------------
# 18.2 — Inference config from env vars (P17)
# ---------------------------------------------------------------------------
class TestInferenceConfig:
    """P17: Inference Config Bounds — maxTokens and temperature from env."""

    def test_inference_config_uses_env_values(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        call_kwargs = mock_client.converse_stream.call_args[1]
        config = call_kwargs['inferenceConfig']
        assert config['maxTokens'] == handler.MAX_TOKENS
        assert config['temperature'] == handler.TEMPERATURE

    def test_default_max_tokens_is_4096(self) -> None:
        assert handler.MAX_TOKENS == 4096

    def test_default_temperature_is_0_7(self) -> None:
        assert handler.TEMPERATURE == 0.7


# ---------------------------------------------------------------------------
# 18.3 — SSE format compliance (P18, P20)
# ---------------------------------------------------------------------------
class TestSseFormatCompliance:
    """P18: SSE Format Compliance, P20: Chunk Content Type."""

    def test_text_chunks_formatted_as_sse(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Based on', ' the ASU catalog,']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        events = _parse_sse_body(result['body'])
        text_events = [e for e in events if e['type'] == 'text-delta']
        assert len(text_events) == 2
        assert text_events[0]['content'] == 'Based on'
        assert text_events[1]['content'] == ' the ASU catalog,'

    def test_each_sse_line_starts_with_data_prefix(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        lines = [l for l in result['body'].split('\n') if l.strip()]
        for line in lines:
            assert line.startswith('data: '), f"Line does not start with 'data: ': {line}"

    def test_each_sse_event_ends_with_double_newline(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        # Each event should be separated by \n\n
        assert '\n\n' in result['body']

    def test_text_delta_events_have_correct_type(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['chunk1', 'chunk2']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        events = _parse_sse_body(result['body'])
        text_events = [e for e in events if e['type'] == 'text-delta']
        for event in text_events:
            assert 'content' in event
            assert isinstance(event['content'], str)


# ---------------------------------------------------------------------------
# 18.4 — Citations event (P19 partial)
# ---------------------------------------------------------------------------
class TestCitationsEvent:
    """Citations event emitted after text streaming."""

    def test_citations_event_emitted(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        events = _parse_sse_body(result['body'])
        citation_events = [e for e in events if e['type'] == 'citations']
        assert len(citation_events) == 1
        assert citation_events[0]['sources'] == CITATIONS

    def test_citations_event_after_text_events(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        events = _parse_sse_body(result['body'])
        types = [e['type'] for e in events]
        citation_idx = types.index('citations')
        # All text-delta events should come before citations
        for i, t in enumerate(types):
            if t == 'text-delta':
                assert i < citation_idx

    def test_empty_citations_list(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, [], REQUEST_ID)

        events = _parse_sse_body(result['body'])
        citation_events = [e for e in events if e['type'] == 'citations']
        assert len(citation_events) == 1
        assert citation_events[0]['sources'] == []


# ---------------------------------------------------------------------------
# 18.5 — Finish event with token usage (P19)
# ---------------------------------------------------------------------------
class TestFinishEvent:
    """P19: Stream Termination — finish event with usage stats."""

    def test_finish_event_emitted(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello'], input_tokens=1250, output_tokens=340),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        events = _parse_sse_body(result['body'])
        finish_events = [e for e in events if e['type'] == 'finish']
        assert len(finish_events) == 1
        assert finish_events[0]['usage'] == {
            'input_tokens': 1250,
            'output_tokens': 340,
        }

    def test_finish_event_is_last(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        events = _parse_sse_body(result['body'])
        assert events[-1]['type'] == 'finish'

    def test_event_order_text_citations_finish(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['A', 'B']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        events = _parse_sse_body(result['body'])
        types = [e['type'] for e in events]
        assert types == ['text-delta', 'text-delta', 'citations', 'finish']


# ---------------------------------------------------------------------------
# 18.6 — Mid-stream error handling (P21)
# ---------------------------------------------------------------------------
class TestMidStreamError:
    """P21: Stream Error Event — error mid-stream emits error SSE."""

    def test_mid_stream_error_emits_error_event(self) -> None:
        """Simulate an error during stream iteration."""
        def _failing_stream():
            yield {'contentBlockDelta': {'delta': {'text': 'partial'}}}
            raise RuntimeError('Connection lost')

        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _failing_stream(),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        assert result['statusCode'] == 200
        events = _parse_sse_body(result['body'])
        # Should have the partial text + error event
        types = [e['type'] for e in events]
        assert 'text-delta' in types
        assert 'error' in types

    def test_mid_stream_error_message_content(self) -> None:
        def _failing_stream():
            raise RuntimeError('Stream failed')
            yield  # noqa: unreachable — makes this a generator

        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _failing_stream(),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        events = _parse_sse_body(result['body'])
        error_events = [e for e in events if e['type'] == 'error']
        assert len(error_events) == 1
        assert 'message' in error_events[0]
        assert isinstance(error_events[0]['message'], str)

    def test_mid_stream_error_has_sse_headers(self) -> None:
        def _failing_stream():
            raise RuntimeError('fail')
            yield  # noqa

        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _failing_stream(),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        assert result['headers']['Content-Type'] == 'text/event-stream'
        assert 'Access-Control-Allow-Origin' in result['headers']


# ---------------------------------------------------------------------------
# 18.7 — Bedrock throttling (P23 partial)
# ---------------------------------------------------------------------------
class TestThrottlingHandling:
    """ThrottlingException → 429 with CORS headers."""

    def test_throttling_returns_429(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ConverseStream',
        )

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        assert result['statusCode'] == 429
        body = json.loads(result['body'])
        assert 'error' in body
        assert 'busy' in body['error'].lower() or 'try again' in body['error'].lower()

    def test_throttling_has_cors_headers(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ConverseStream',
        )

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        assert 'Access-Control-Allow-Origin' in result['headers']
        assert 'Access-Control-Allow-Methods' in result['headers']

    def test_throttling_has_json_content_type(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ConverseStream',
        )

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        assert result['headers']['Content-Type'] == 'application/json'


# ---------------------------------------------------------------------------
# Other Bedrock errors before streaming → 500
# ---------------------------------------------------------------------------
class TestBedrockPreStreamErrors:
    """Bedrock errors before streaming starts → 500 with CORS."""

    def test_access_denied_returns_500(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'ConverseStream',
        )

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body

    def test_generic_exception_returns_500(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.side_effect = RuntimeError('Unexpected')

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body

    def test_500_error_has_cors_headers(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.side_effect = RuntimeError('Unexpected')

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        assert 'Access-Control-Allow-Origin' in result['headers']
        assert 'Access-Control-Allow-Methods' in result['headers']


# ---------------------------------------------------------------------------
# 18.8 — SSE response headers (P23)
# ---------------------------------------------------------------------------
class TestSseHeaders:
    """P23: CORS Headers on All Responses + SSE-specific headers."""

    def test_success_response_has_sse_content_type(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        assert result['headers']['Content-Type'] == 'text/event-stream'

    def test_success_response_has_cache_control(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        assert result['headers']['Cache-Control'] == 'no-cache'

    def test_success_response_has_connection_keep_alive(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        assert result['headers']['Connection'] == 'keep-alive'

    def test_success_response_has_cors_headers(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        assert result['headers']['Access-Control-Allow-Origin'] == handler.CORS_ALLOWED_ORIGIN
        assert 'Access-Control-Allow-Headers' in result['headers']
        assert 'Access-Control-Allow-Methods' in result['headers']


# ---------------------------------------------------------------------------
# P22 — No empty streams
# ---------------------------------------------------------------------------
class TestNoEmptyStreams:
    """P22: No Empty Streams — must emit at least one text-delta."""

    def test_empty_stream_emits_fallback_text(self) -> None:
        mock_client = MagicMock()
        # Stream with only metadata, no text content
        mock_client.converse_stream.return_value = {
            'stream': [
                {'messageStop': {'stopReason': 'end_turn'}},
                {'metadata': {'usage': {'inputTokens': 10, 'outputTokens': 0}}},
            ],
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        events = _parse_sse_body(result['body'])
        text_events = [e for e in events if e['type'] == 'text-delta']
        assert len(text_events) >= 1
        assert text_events[0]['content']  # Non-empty content

    def test_empty_text_deltas_not_emitted(self) -> None:
        """Empty string text deltas should be skipped."""
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': [
                {'contentBlockDelta': {'delta': {'text': ''}}},
                {'contentBlockDelta': {'delta': {'text': 'actual content'}}},
                {'messageStop': {'stopReason': 'end_turn'}},
                {'metadata': {'usage': {'inputTokens': 10, 'outputTokens': 5}}},
            ],
        }

        with patch.object(handler, 'bedrock_runtime', mock_client):
            result = handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        events = _parse_sse_body(result['body'])
        text_events = [e for e in events if e['type'] == 'text-delta']
        assert len(text_events) == 1
        assert text_events[0]['content'] == 'actual content'


# ---------------------------------------------------------------------------
# Integration: stream_response wired into handle_chat_request
# ---------------------------------------------------------------------------
class TestStreamWiring:
    """Verify stream_response is called from handle_chat_request."""

    def test_valid_request_calls_stream_response(self) -> None:
        event = _make_valid_event()

        with patch.object(handler, 'retrieve_from_kb', return_value=('ctx', ['s3://x'])), \
             patch.object(handler, 'stream_response', return_value={
                 'statusCode': 200,
                 'headers': {'Content-Type': 'text/event-stream'},
                 'body': 'data: {"type": "finish"}\n\n',
             }) as mock_stream:
            handler.handle_chat_request(event, REQUEST_ID)

        mock_stream.assert_called_once()
        args = mock_stream.call_args
        # system_prompt, message, citations, request_id
        assert args[0][1] == USER_MESSAGE  # message
        assert args[0][2] == ['s3://x']    # citations
        assert args[0][3] == REQUEST_ID    # request_id

    def test_lambda_handler_returns_sse_for_valid_request(self) -> None:
        event = _make_valid_event()
        mock_context = MagicMock()
        mock_context.aws_request_id = 'req-stream-123'

        mock_bedrock = MagicMock()
        mock_bedrock.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello world']),
        }

        with patch.object(handler, 'retrieve_from_kb', return_value=('ctx', [])), \
             patch.object(handler, 'bedrock_runtime', mock_bedrock):
            result = handler.lambda_handler(event, mock_context)

        assert result['statusCode'] == 200
        assert result['headers']['Content-Type'] == 'text/event-stream'
        events = _parse_sse_body(result['body'])
        types = [e['type'] for e in events]
        assert 'text-delta' in types
        assert 'citations' in types
        assert 'finish' in types


# ---------------------------------------------------------------------------
# Logging — no PII (P32)
# ---------------------------------------------------------------------------
class TestStreamingNoPii:
    """P32: Streaming logs must not contain the user's message content."""

    def test_stream_start_log_does_not_contain_message(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.return_value = {
            'stream': _make_stream_events(['Hello']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_client), \
             patch.object(handler, 'log_event') as mock_log:
            handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        for log_call in mock_log.call_args_list:
            kwargs = log_call[1]
            for value in kwargs.values():
                if isinstance(value, str):
                    assert USER_MESSAGE not in value

    def test_throttle_log_does_not_contain_message(self) -> None:
        mock_client = MagicMock()
        mock_client.converse_stream.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ConverseStream',
        )

        with patch.object(handler, 'bedrock_runtime', mock_client), \
             patch.object(handler, 'log_event') as mock_log:
            handler.stream_response(SYSTEM_PROMPT, USER_MESSAGE, CITATIONS, REQUEST_ID)

        for log_call in mock_log.call_args_list:
            kwargs = log_call[1]
            for value in kwargs.values():
                if isinstance(value, str):
                    assert USER_MESSAGE not in value
