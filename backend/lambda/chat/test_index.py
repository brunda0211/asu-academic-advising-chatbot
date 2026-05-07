"""Task 35 — Chat Lambda unit tests.

Validates Properties: P1–P6, P10, P11, P23, P31, P32
Requirements: FR-CHAT-1, FR-RAG-3, NFR-CORS-1, NFR-OBSERVABILITY-1, NFR-SECURITY-2
"""

from __future__ import annotations

import json
import io
import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

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
REQUEST_ID = 'test-request-id-index'


def _valid_body() -> dict[str, Any]:
    return {
        'message': 'What are the prerequisites for CSE 310?',
        'session_id': 'session_1234567890123_abcdefghijk',
        'context': {
            'academic_year': 'Junior',
            'major': 'Computer Science',
            'advising_topic': 'Course Planning',
        },
    }


def _make_event(body: dict[str, Any] | None = None) -> dict[str, Any]:
    if body is None:
        body = _valid_body()
    return {'body': json.dumps(body)}


def _make_stream_events(text_chunks: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for chunk in text_chunks:
        events.append({'contentBlockDelta': {'delta': {'text': chunk}}})
    events.append({'messageStop': {'stopReason': 'end_turn'}})
    events.append({'metadata': {'usage': {'inputTokens': 50, 'outputTokens': 25}}})
    return events


def _parse_sse_body(body: str) -> list[dict[str, Any]]:
    events = []
    for line in body.split('\n'):
        line = line.strip()
        if line.startswith('data: '):
            events.append(json.loads(line[6:]))
    return events


def _invoke_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Invoke lambda_handler with mocked Bedrock clients."""
    mock_context = MagicMock()
    mock_context.aws_request_id = REQUEST_ID

    mock_bedrock = MagicMock()
    mock_bedrock.converse_stream.return_value = {
        'stream': _make_stream_events(['Hello world']),
    }

    mock_kb = MagicMock()
    mock_kb.retrieve.return_value = {
        'retrievalResults': [
            {'content': {'text': 'Some doc'}, 'location': {'s3Location': {'uri': 's3://b/d.pdf'}}},
        ],
    }

    with patch.object(handler, 'bedrock_runtime', mock_bedrock), \
         patch.object(handler, 'bedrock_agent_runtime', mock_kb):
        return handler.lambda_handler(event, mock_context)


# ---------------------------------------------------------------------------
# 35.1 — Valid request returns 200 with SSE stream headers
# ---------------------------------------------------------------------------
class TestValidRequest:
    def test_valid_request_returns_200(self) -> None:
        result = _invoke_handler(_make_event())
        assert result['statusCode'] == 200

    def test_valid_request_has_sse_content_type(self) -> None:
        result = _invoke_handler(_make_event())
        assert result['headers']['Content-Type'] == 'text/event-stream'

    def test_valid_request_has_cache_control(self) -> None:
        result = _invoke_handler(_make_event())
        assert result['headers']['Cache-Control'] == 'no-cache'

    def test_valid_request_has_connection_keep_alive(self) -> None:
        result = _invoke_handler(_make_event())
        assert result['headers']['Connection'] == 'keep-alive'


# ---------------------------------------------------------------------------
# 35.2 — Missing message returns 400 with error body
# ---------------------------------------------------------------------------
class TestMissingMessage:
    def test_missing_message_returns_400(self) -> None:
        body = _valid_body()
        del body['message']
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 400

    def test_missing_message_has_error_body(self) -> None:
        body = _valid_body()
        del body['message']
        result = _invoke_handler(_make_event(body))
        response_body = json.loads(result['body'])
        assert 'error' in response_body

    def test_empty_message_returns_400(self) -> None:
        body = _valid_body()
        body['message'] = ''
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 400


# ---------------------------------------------------------------------------
# 35.3 — Message exceeding 2000 chars returns 400
# ---------------------------------------------------------------------------
class TestMessageTooLong:
    def test_message_2001_chars_returns_400(self) -> None:
        body = _valid_body()
        body['message'] = 'a' * 2001
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 400

    def test_message_2000_chars_returns_200(self) -> None:
        body = _valid_body()
        body['message'] = 'a' * 2000
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 200


# ---------------------------------------------------------------------------
# 35.4 — Invalid session_id (< 33 chars) returns 400
# ---------------------------------------------------------------------------
class TestInvalidSessionId:
    def test_short_session_id_returns_400(self) -> None:
        body = _valid_body()
        body['session_id'] = 'short_id'
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 400

    def test_32_char_session_id_returns_400(self) -> None:
        body = _valid_body()
        body['session_id'] = 'a' * 32
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 400

    def test_33_char_session_id_returns_200(self) -> None:
        body = _valid_body()
        body['session_id'] = 'a' * 33
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 200


# ---------------------------------------------------------------------------
# 35.5 — Invalid academic_year enum returns 400
# ---------------------------------------------------------------------------
class TestInvalidAcademicYear:
    def test_invalid_academic_year_returns_400(self) -> None:
        body = _valid_body()
        body['context']['academic_year'] = 'Postdoc'
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 400

    def test_lowercase_academic_year_returns_400(self) -> None:
        body = _valid_body()
        body['context']['academic_year'] = 'junior'
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 400


# ---------------------------------------------------------------------------
# 35.6 — Empty major returns 400
# ---------------------------------------------------------------------------
class TestEmptyMajor:
    def test_empty_major_returns_400(self) -> None:
        body = _valid_body()
        body['context']['major'] = ''
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 400

    def test_whitespace_only_major_returns_400(self) -> None:
        body = _valid_body()
        body['context']['major'] = '   '
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 400


# ---------------------------------------------------------------------------
# 35.7 — Invalid advising_topic enum returns 400
# ---------------------------------------------------------------------------
class TestInvalidAdvisingTopic:
    def test_invalid_topic_returns_400(self) -> None:
        body = _valid_body()
        body['context']['advising_topic'] = 'Financial Aid'
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 400

    def test_lowercase_topic_returns_400(self) -> None:
        body = _valid_body()
        body['context']['advising_topic'] = 'course planning'
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 400


# ---------------------------------------------------------------------------
# 35.8 — KB retrieval failure proceeds without context (no 500)
# ---------------------------------------------------------------------------
class TestKbRetrievalFailure:
    def test_kb_failure_does_not_return_500(self) -> None:
        mock_context = MagicMock()
        mock_context.aws_request_id = REQUEST_ID

        mock_bedrock = MagicMock()
        mock_bedrock.converse_stream.return_value = {
            'stream': _make_stream_events(['Response without KB']),
        }

        mock_kb = MagicMock()
        mock_kb.retrieve.side_effect = RuntimeError('KB unavailable')

        with patch.object(handler, 'bedrock_runtime', mock_bedrock), \
             patch.object(handler, 'bedrock_agent_runtime', mock_kb):
            result = handler.lambda_handler(_make_event(), mock_context)

        assert result['statusCode'] == 200

    def test_kb_failure_still_streams_response(self) -> None:
        mock_context = MagicMock()
        mock_context.aws_request_id = REQUEST_ID

        mock_bedrock = MagicMock()
        mock_bedrock.converse_stream.return_value = {
            'stream': _make_stream_events(['Fallback response']),
        }

        mock_kb = MagicMock()
        mock_kb.retrieve.side_effect = Exception('Service error')

        with patch.object(handler, 'bedrock_runtime', mock_bedrock), \
             patch.object(handler, 'bedrock_agent_runtime', mock_kb):
            result = handler.lambda_handler(_make_event(), mock_context)

        events = _parse_sse_body(result['body'])
        text_events = [e for e in events if e['type'] == 'text-delta']
        assert len(text_events) >= 1


# ---------------------------------------------------------------------------
# 35.9 — Empty KB retrieval results proceeds with empty context
# ---------------------------------------------------------------------------
class TestEmptyKbResults:
    def test_empty_kb_results_returns_200(self) -> None:
        mock_context = MagicMock()
        mock_context.aws_request_id = REQUEST_ID

        mock_bedrock = MagicMock()
        mock_bedrock.converse_stream.return_value = {
            'stream': _make_stream_events(['Response']),
        }

        mock_kb = MagicMock()
        mock_kb.retrieve.return_value = {'retrievalResults': []}

        with patch.object(handler, 'bedrock_runtime', mock_bedrock), \
             patch.object(handler, 'bedrock_agent_runtime', mock_kb):
            result = handler.lambda_handler(_make_event(), mock_context)

        assert result['statusCode'] == 200

    def test_empty_kb_results_includes_no_docs_note_in_prompt(self) -> None:
        mock_context = MagicMock()
        mock_context.aws_request_id = REQUEST_ID

        mock_bedrock = MagicMock()
        mock_bedrock.converse_stream.return_value = {
            'stream': _make_stream_events(['Response']),
        }

        mock_kb = MagicMock()
        mock_kb.retrieve.return_value = {'retrievalResults': []}

        with patch.object(handler, 'bedrock_runtime', mock_bedrock), \
             patch.object(handler, 'bedrock_agent_runtime', mock_kb):
            handler.lambda_handler(_make_event(), mock_context)

        # Verify system prompt contains the no-documents note
        call_kwargs = mock_bedrock.converse_stream.call_args[1]
        system_text = call_kwargs['system'][0]['text']
        assert handler.NO_DOCUMENTS_NOTE in system_text


# ---------------------------------------------------------------------------
# 35.10 — CORS headers present on all response types (success, 400, 500)
# ---------------------------------------------------------------------------
class TestCorsOnAllResponses:
    def test_cors_on_success_response(self) -> None:
        result = _invoke_handler(_make_event())
        assert 'Access-Control-Allow-Origin' in result['headers']
        assert 'Access-Control-Allow-Methods' in result['headers']
        assert 'Access-Control-Allow-Headers' in result['headers']

    def test_cors_on_400_response(self) -> None:
        body = _valid_body()
        body['message'] = ''
        result = _invoke_handler(_make_event(body))
        assert result['statusCode'] == 400
        assert 'Access-Control-Allow-Origin' in result['headers']
        assert 'Access-Control-Allow-Methods' in result['headers']

    def test_cors_on_500_response(self) -> None:
        mock_context = MagicMock()
        mock_context.aws_request_id = REQUEST_ID

        with patch.object(handler, 'handle_chat_request', side_effect=RuntimeError('boom')):
            result = handler.lambda_handler(_make_event(), mock_context)

        assert result['statusCode'] == 500
        assert 'Access-Control-Allow-Origin' in result['headers']
        assert 'Access-Control-Allow-Methods' in result['headers']

    def test_cors_origin_matches_env_var(self) -> None:
        result = _invoke_handler(_make_event())
        assert result['headers']['Access-Control-Allow-Origin'] == handler.CORS_ALLOWED_ORIGIN


# ---------------------------------------------------------------------------
# 35.11 — Structured JSON log output format
# ---------------------------------------------------------------------------
class TestStructuredLogging:
    def test_log_event_produces_json(self) -> None:
        log_stream = io.StringIO()
        test_handler = logging.StreamHandler(log_stream)
        handler.logger.addHandler(test_handler)

        try:
            handler.log_event('info', 'test_action', REQUEST_ID, extra_field='value')
            log_output = log_stream.getvalue()
            parsed = json.loads(log_output.strip())
            assert parsed['action'] == 'test_action'
            assert parsed['request_id'] == REQUEST_ID
            assert parsed['level'] == 'INFO'
            assert 'timestamp' in parsed
            assert parsed['extra_field'] == 'value'
        finally:
            handler.logger.removeHandler(test_handler)

    def test_log_event_includes_timestamp_iso_format(self) -> None:
        log_stream = io.StringIO()
        test_handler = logging.StreamHandler(log_stream)
        handler.logger.addHandler(test_handler)

        try:
            handler.log_event('info', 'ts_test', REQUEST_ID)
            log_output = log_stream.getvalue()
            parsed = json.loads(log_output.strip())
            # ISO 8601 format check
            assert 'T' in parsed['timestamp']
            assert '+' in parsed['timestamp'] or 'Z' in parsed['timestamp']
        finally:
            handler.logger.removeHandler(test_handler)


# ---------------------------------------------------------------------------
# 35.12 — No full message content appears in log output
# ---------------------------------------------------------------------------
class TestNoMessageInLogs:
    def test_validation_passed_log_has_no_message_content(self) -> None:
        event = _make_event()
        message_text = _valid_body()['message']

        with patch.object(handler, 'log_event') as mock_log, \
             patch.object(handler, 'retrieve_from_kb', return_value=('ctx', [])), \
             patch.object(handler, 'stream_response', return_value={
                 'statusCode': 200,
                 'headers': {'Content-Type': 'text/event-stream'},
                 'body': 'data: {"type":"finish"}\n\n',
             }):
            handler.handle_chat_request(event, REQUEST_ID)

        for call in mock_log.call_args_list:
            kwargs = call[1]
            for value in kwargs.values():
                if isinstance(value, str):
                    assert message_text not in value

    def test_kb_retrieval_log_has_no_message_content(self) -> None:
        message_text = 'What are the prerequisites for CSE 310?'

        mock_kb = MagicMock()
        mock_kb.retrieve.return_value = {'retrievalResults': []}

        with patch.object(handler, 'bedrock_agent_runtime', mock_kb), \
             patch.object(handler, 'log_event') as mock_log:
            handler.retrieve_from_kb(message_text, REQUEST_ID)

        for call in mock_log.call_args_list:
            kwargs = call[1]
            for value in kwargs.values():
                if isinstance(value, str):
                    assert message_text not in value

    def test_stream_log_has_no_message_content(self) -> None:
        message_text = 'Sensitive student question'

        mock_bedrock = MagicMock()
        mock_bedrock.converse_stream.return_value = {
            'stream': _make_stream_events(['Reply']),
        }

        with patch.object(handler, 'bedrock_runtime', mock_bedrock), \
             patch.object(handler, 'log_event') as mock_log:
            handler.stream_response('system prompt', message_text, [], REQUEST_ID)

        for call in mock_log.call_args_list:
            kwargs = call[1]
            for value in kwargs.values():
                if isinstance(value, str):
                    assert message_text not in value
