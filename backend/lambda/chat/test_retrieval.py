"""Tests for Task 16 — KB retrieval logic in the Chat Lambda handler.

Validates correctness properties P7–P12 and P32 (No PII in Logs).
Uses unittest.mock to patch boto3 clients so no AWS credentials are needed.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Patch boto3 clients before importing the handler module so module-level
# client creation doesn't require real AWS credentials.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _patch_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('KNOWLEDGE_BASE_ID', 'test-kb-id')
    monkeypatch.setenv('MODEL_ID', 'us.amazon.nova-lite-v1:0')
    monkeypatch.setenv('CORS_ALLOWED_ORIGIN', 'http://localhost:3000')
    monkeypatch.setenv('NUM_KB_RESULTS', '5')


# Import handler with patched boto3
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
REQUEST_ID = 'test-request-id-retrieval'


def _make_retrieval_result(
    text: str,
    uri: str = '',
) -> dict[str, Any]:
    """Build a single KB retrieval result dict."""
    result: dict[str, Any] = {
        'content': {'text': text},
        'location': {},
    }
    if uri:
        result['location'] = {
            's3Location': {'uri': uri},
        }
    return result


def _make_retrieve_response(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a mock retrieve() API response."""
    return {'retrievalResults': results}


# ---------------------------------------------------------------------------
# 16.1 — Call bedrock_agent_runtime.retrieve() with correct params (P7)
# ---------------------------------------------------------------------------
class TestRetrievalInvocation:
    """P7: Retrieval Invocation — must invoke KB Retrieve API."""

    def test_retrieve_called_with_knowledge_base_id(self) -> None:
        mock_client = MagicMock()
        mock_client.retrieve.return_value = _make_retrieve_response([])

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            handler.retrieve_from_kb('test query', REQUEST_ID)

        mock_client.retrieve.assert_called_once()
        call_kwargs = mock_client.retrieve.call_args[1]
        assert call_kwargs['knowledgeBaseId'] == handler.KNOWLEDGE_BASE_ID

    def test_retrieve_called_with_user_message_as_query(self) -> None:
        mock_client = MagicMock()
        mock_client.retrieve.return_value = _make_retrieve_response([])
        message = 'What are the prerequisites for CSE 310?'

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            handler.retrieve_from_kb(message, REQUEST_ID)

        call_kwargs = mock_client.retrieve.call_args[1]
        assert call_kwargs['retrievalQuery'] == {'text': message}


# ---------------------------------------------------------------------------
# 16.2 — Request NUM_KB_RESULTS results (P8)
# ---------------------------------------------------------------------------
class TestRetrievalResultCount:
    """P8: Retrieval Result Count — must request exactly NUM_KB_RESULTS."""

    def test_retrieve_requests_num_kb_results(self) -> None:
        mock_client = MagicMock()
        mock_client.retrieve.return_value = _make_retrieve_response([])

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            handler.retrieve_from_kb('test', REQUEST_ID)

        call_kwargs = mock_client.retrieve.call_args[1]
        config = call_kwargs['retrievalConfiguration']
        num_results = config['vectorSearchConfiguration']['numberOfResults']
        assert num_results == handler.NUM_KB_RESULTS

    def test_default_num_kb_results_is_5(self) -> None:
        assert handler.NUM_KB_RESULTS == 5


# ---------------------------------------------------------------------------
# 16.3 — Extract text content and join with double newlines (P9)
# ---------------------------------------------------------------------------
class TestTextExtraction:
    """P9: Context Injection — retrieved text must be extracted and joined."""

    def test_single_result_text_extracted(self) -> None:
        mock_client = MagicMock()
        results = [_make_retrieval_result('Document chunk 1')]
        mock_client.retrieve.return_value = _make_retrieve_response(results)

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            context, _ = handler.retrieve_from_kb('test', REQUEST_ID)

        assert context == 'Document chunk 1'

    def test_multiple_results_joined_with_double_newlines(self) -> None:
        mock_client = MagicMock()
        results = [
            _make_retrieval_result('Chunk A'),
            _make_retrieval_result('Chunk B'),
            _make_retrieval_result('Chunk C'),
        ]
        mock_client.retrieve.return_value = _make_retrieve_response(results)

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            context, _ = handler.retrieve_from_kb('test', REQUEST_ID)

        assert context == 'Chunk A\n\nChunk B\n\nChunk C'

    def test_empty_text_chunks_are_skipped(self) -> None:
        mock_client = MagicMock()
        results = [
            _make_retrieval_result('Chunk A'),
            _make_retrieval_result(''),
            _make_retrieval_result('Chunk C'),
        ]
        mock_client.retrieve.return_value = _make_retrieve_response(results)

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            context, _ = handler.retrieve_from_kb('test', REQUEST_ID)

        assert context == 'Chunk A\n\nChunk C'

    def test_missing_content_key_handled(self) -> None:
        mock_client = MagicMock()
        results = [{'location': {}}]  # No 'content' key
        mock_client.retrieve.return_value = _make_retrieve_response(results)

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            context, _ = handler.retrieve_from_kb('test', REQUEST_ID)

        assert context == ''


# ---------------------------------------------------------------------------
# 16.4 — Extract S3 source URIs for citations (P12)
# ---------------------------------------------------------------------------
class TestCitationExtraction:
    """P12: Citation Extraction — S3 source URIs must be extracted."""

    def test_s3_uris_extracted_from_results(self) -> None:
        mock_client = MagicMock()
        results = [
            _make_retrieval_result('Chunk A', 's3://bucket/doc1.pdf'),
            _make_retrieval_result('Chunk B', 's3://bucket/doc2.pdf'),
        ]
        mock_client.retrieve.return_value = _make_retrieve_response(results)

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            _, citations = handler.retrieve_from_kb('test', REQUEST_ID)

        assert citations == ['s3://bucket/doc1.pdf', 's3://bucket/doc2.pdf']

    def test_duplicate_uris_are_deduplicated(self) -> None:
        mock_client = MagicMock()
        results = [
            _make_retrieval_result('Chunk A', 's3://bucket/doc1.pdf'),
            _make_retrieval_result('Chunk B', 's3://bucket/doc1.pdf'),
            _make_retrieval_result('Chunk C', 's3://bucket/doc2.pdf'),
        ]
        mock_client.retrieve.return_value = _make_retrieve_response(results)

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            _, citations = handler.retrieve_from_kb('test', REQUEST_ID)

        assert citations == ['s3://bucket/doc1.pdf', 's3://bucket/doc2.pdf']

    def test_missing_location_handled(self) -> None:
        mock_client = MagicMock()
        results = [_make_retrieval_result('Chunk A')]  # No URI
        mock_client.retrieve.return_value = _make_retrieve_response(results)

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            _, citations = handler.retrieve_from_kb('test', REQUEST_ID)

        assert citations == []

    def test_empty_uri_skipped(self) -> None:
        mock_client = MagicMock()
        results = [
            _make_retrieval_result('Chunk A', ''),
            _make_retrieval_result('Chunk B', 's3://bucket/doc.pdf'),
        ]
        mock_client.retrieve.return_value = _make_retrieve_response(results)

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            _, citations = handler.retrieve_from_kb('test', REQUEST_ID)

        assert citations == ['s3://bucket/doc.pdf']


# ---------------------------------------------------------------------------
# 16.5 — Handle empty retrieval results gracefully (P10)
# ---------------------------------------------------------------------------
class TestEmptyRetrievalHandling:
    """P10: Empty Retrieval Graceful Handling — zero results must not cause error."""

    def test_empty_results_returns_empty_context(self) -> None:
        mock_client = MagicMock()
        mock_client.retrieve.return_value = _make_retrieve_response([])

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            context, citations = handler.retrieve_from_kb('test', REQUEST_ID)

        assert context == ''
        assert citations == []

    def test_missing_retrieval_results_key_returns_empty(self) -> None:
        mock_client = MagicMock()
        mock_client.retrieve.return_value = {}  # No 'retrievalResults' key

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            context, citations = handler.retrieve_from_kb('test', REQUEST_ID)

        assert context == ''
        assert citations == []

    def test_empty_results_logs_info(self) -> None:
        mock_client = MagicMock()
        mock_client.retrieve.return_value = _make_retrieve_response([])

        with patch.object(handler, 'bedrock_agent_runtime', mock_client), \
             patch.object(handler, 'log_event') as mock_log:
            handler.retrieve_from_kb('test query', REQUEST_ID)

        # Find the kb_retrieval_empty log call
        empty_calls = [
            c for c in mock_log.call_args_list
            if len(c[0]) >= 2 and c[0][1] == 'kb_retrieval_empty'
        ]
        assert len(empty_calls) == 1
        assert empty_calls[0][0][0] == 'info'  # level is INFO


# ---------------------------------------------------------------------------
# 16.6 — Handle retrieval exceptions (P11)
# ---------------------------------------------------------------------------
class TestRetrievalExceptionHandling:
    """P11: Retrieval Failure Resilience — exceptions caught, logged, proceed."""

    def test_exception_returns_empty_context(self) -> None:
        mock_client = MagicMock()
        mock_client.retrieve.side_effect = Exception('KB unavailable')

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            context, citations = handler.retrieve_from_kb('test', REQUEST_ID)

        assert context == ''
        assert citations == []

    def test_exception_does_not_raise(self) -> None:
        mock_client = MagicMock()
        mock_client.retrieve.side_effect = RuntimeError('Connection timeout')

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            # Should not raise
            context, citations = handler.retrieve_from_kb('test', REQUEST_ID)

        assert isinstance(context, str)
        assert isinstance(citations, list)

    def test_exception_logs_error(self) -> None:
        mock_client = MagicMock()
        mock_client.retrieve.side_effect = Exception('Service error')

        with patch.object(handler, 'bedrock_agent_runtime', mock_client), \
             patch.object(handler, 'log_event') as mock_log:
            handler.retrieve_from_kb('test query', REQUEST_ID)

        # Find the kb_retrieval_failed log call
        error_calls = [
            c for c in mock_log.call_args_list
            if len(c[0]) >= 2 and c[0][1] == 'kb_retrieval_failed'
        ]
        assert len(error_calls) == 1
        assert error_calls[0][0][0] == 'error'  # level is ERROR

    def test_boto_client_error_handled(self) -> None:
        """Simulate a botocore ClientError."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.retrieve.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Denied'}},
            'Retrieve',
        )

        with patch.object(handler, 'bedrock_agent_runtime', mock_client):
            context, citations = handler.retrieve_from_kb('test', REQUEST_ID)

        assert context == ''
        assert citations == []


# ---------------------------------------------------------------------------
# P32 — No PII in Logs
# ---------------------------------------------------------------------------
class TestNoPiiInRetrievalLogs:
    """P32: Retrieval logs must not contain the user's message content."""

    def test_success_log_contains_length_not_message(self) -> None:
        mock_client = MagicMock()
        message = 'What are the prerequisites for CSE 310?'
        results = [_make_retrieval_result('Some text', 's3://bucket/doc.pdf')]
        mock_client.retrieve.return_value = _make_retrieve_response(results)

        with patch.object(handler, 'bedrock_agent_runtime', mock_client), \
             patch.object(handler, 'log_event') as mock_log:
            handler.retrieve_from_kb(message, REQUEST_ID)

        # Check all log calls — none should contain the full message
        for log_call in mock_log.call_args_list:
            kwargs = log_call[1]
            for value in kwargs.values():
                if isinstance(value, str):
                    assert message not in value
            # Should have message_length instead
            if len(log_call[0]) >= 2 and log_call[0][1] == 'kb_retrieval_success':
                assert 'message_length' in kwargs
                assert kwargs['message_length'] == len(message)

    def test_error_log_contains_length_not_message(self) -> None:
        mock_client = MagicMock()
        message = 'Sensitive student question about grades'
        mock_client.retrieve.side_effect = Exception('fail')

        with patch.object(handler, 'bedrock_agent_runtime', mock_client), \
             patch.object(handler, 'log_event') as mock_log:
            handler.retrieve_from_kb(message, REQUEST_ID)

        for log_call in mock_log.call_args_list:
            kwargs = log_call[1]
            for value in kwargs.values():
                if isinstance(value, str):
                    assert message not in value


# ---------------------------------------------------------------------------
# Integration: retrieve_from_kb wired into handle_chat_request
# ---------------------------------------------------------------------------
class TestRetrievalWiring:
    """Verify retrieve_from_kb is called from handle_chat_request."""

    def _make_valid_event(self) -> dict[str, Any]:
        return {
            'body': json.dumps({
                'message': 'What are the prerequisites for CSE 310?',
                'session_id': 'session_1234567890123_abcdefghijk',
                'context': {
                    'academic_year': 'Junior',
                    'major': 'Computer Science',
                    'advising_topic': 'Course Planning',
                },
            }),
        }

    def test_retrieve_from_kb_called_for_valid_request(self) -> None:
        event = self._make_valid_event()

        with patch.object(handler, 'retrieve_from_kb', return_value=('ctx', ['s3://x'])) as mock_retrieve:
            handler.handle_chat_request(event, REQUEST_ID)

        mock_retrieve.assert_called_once_with(
            'What are the prerequisites for CSE 310?',
            REQUEST_ID,
        )

    def test_retrieve_not_called_for_invalid_request(self) -> None:
        event = {'body': json.dumps({'message': ''})}

        with patch.object(handler, 'retrieve_from_kb') as mock_retrieve:
            handler.handle_chat_request(event, REQUEST_ID)

        mock_retrieve.assert_not_called()
