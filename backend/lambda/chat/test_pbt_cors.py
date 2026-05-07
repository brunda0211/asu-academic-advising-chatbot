"""Task 38 — Property-based tests for CORS compliance.

Uses hypothesis to verify CORS headers are present on every response type.
Validates Properties: P23
Requirements: NFR-CORS-1
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

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
REQUEST_ID = 'pbt-cors-request-id'

VALID_ACADEMIC_YEARS = ['Freshman', 'Sophomore', 'Junior', 'Senior', 'Graduate']
VALID_ADVISING_TOPICS = ['Course Planning', 'Degree Requirements', 'Academic Standing', 'General Advising']


def _assert_cors_headers(result: dict[str, Any]) -> None:
    """Assert that CORS headers are present on the response."""
    headers = result.get('headers', {})
    assert 'Access-Control-Allow-Origin' in headers, \
        f"Missing Access-Control-Allow-Origin in {headers}"
    assert 'Access-Control-Allow-Methods' in headers, \
        f"Missing Access-Control-Allow-Methods in {headers}"
    assert 'Access-Control-Allow-Headers' in headers, \
        f"Missing Access-Control-Allow-Headers in {headers}"
    assert headers['Access-Control-Allow-Origin'] == handler.CORS_ALLOWED_ORIGIN


def _make_stream_events(text: str = 'Hello') -> list[dict[str, Any]]:
    return [
        {'contentBlockDelta': {'delta': {'text': text}}},
        {'messageStop': {'stopReason': 'end_turn'}},
        {'metadata': {'usage': {'inputTokens': 10, 'outputTokens': 5}}},
    ]


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------
# Strategy for generating random request bodies (both valid and invalid)
valid_body_strategy = st.fixed_dictionaries({
    'message': st.text(min_size=1, max_size=2000).filter(lambda s: len(s.strip()) > 0),
    'session_id': st.text(min_size=33, max_size=100),
    'context': st.fixed_dictionaries({
        'academic_year': st.sampled_from(VALID_ACADEMIC_YEARS),
        'major': st.text(min_size=1, max_size=200).filter(lambda s: len(s.strip()) > 0),
        'advising_topic': st.sampled_from(VALID_ADVISING_TOPICS),
    }),
})

invalid_body_strategy = st.one_of(
    # Missing message
    st.fixed_dictionaries({
        'message': st.just(''),
        'session_id': st.text(min_size=33, max_size=50),
        'context': st.fixed_dictionaries({
            'academic_year': st.sampled_from(VALID_ACADEMIC_YEARS),
            'major': st.text(min_size=1, max_size=50).filter(lambda s: len(s.strip()) > 0),
            'advising_topic': st.sampled_from(VALID_ADVISING_TOPICS),
        }),
    }),
    # Message too long
    st.fixed_dictionaries({
        'message': st.text(min_size=2001, max_size=3000).filter(lambda s: len(s.strip()) > 2000),
        'session_id': st.text(min_size=33, max_size=50),
        'context': st.fixed_dictionaries({
            'academic_year': st.sampled_from(VALID_ACADEMIC_YEARS),
            'major': st.text(min_size=1, max_size=50).filter(lambda s: len(s.strip()) > 0),
            'advising_topic': st.sampled_from(VALID_ADVISING_TOPICS),
        }),
    }),
    # Short session_id
    st.fixed_dictionaries({
        'message': st.text(min_size=1, max_size=100).filter(lambda s: len(s.strip()) > 0),
        'session_id': st.text(min_size=0, max_size=32),
        'context': st.fixed_dictionaries({
            'academic_year': st.sampled_from(VALID_ACADEMIC_YEARS),
            'major': st.text(min_size=1, max_size=50).filter(lambda s: len(s.strip()) > 0),
            'advising_topic': st.sampled_from(VALID_ADVISING_TOPICS),
        }),
    }),
    # Invalid academic_year
    st.fixed_dictionaries({
        'message': st.text(min_size=1, max_size=100).filter(lambda s: len(s.strip()) > 0),
        'session_id': st.text(min_size=33, max_size=50),
        'context': st.fixed_dictionaries({
            'academic_year': st.text(min_size=1, max_size=50).filter(
                lambda s: s not in VALID_ACADEMIC_YEARS
            ),
            'major': st.text(min_size=1, max_size=50).filter(lambda s: len(s.strip()) > 0),
            'advising_topic': st.sampled_from(VALID_ADVISING_TOPICS),
        }),
    }),
    # Invalid advising_topic
    st.fixed_dictionaries({
        'message': st.text(min_size=1, max_size=100).filter(lambda s: len(s.strip()) > 0),
        'session_id': st.text(min_size=33, max_size=50),
        'context': st.fixed_dictionaries({
            'academic_year': st.sampled_from(VALID_ACADEMIC_YEARS),
            'major': st.text(min_size=1, max_size=50).filter(lambda s: len(s.strip()) > 0),
            'advising_topic': st.text(min_size=1, max_size=50).filter(
                lambda s: s not in VALID_ADVISING_TOPICS
            ),
        }),
    }),
    # Empty major
    st.fixed_dictionaries({
        'message': st.text(min_size=1, max_size=100).filter(lambda s: len(s.strip()) > 0),
        'session_id': st.text(min_size=33, max_size=50),
        'context': st.fixed_dictionaries({
            'academic_year': st.sampled_from(VALID_ACADEMIC_YEARS),
            'major': st.just(''),
            'advising_topic': st.sampled_from(VALID_ADVISING_TOPICS),
        }),
    }),
)


# ---------------------------------------------------------------------------
# 38.1 — Property 23: CORS Headers on All Responses
# Generate random valid and invalid requests, verify CORS headers present
# on every response
# Validates: Requirements NFR-CORS-1
# ---------------------------------------------------------------------------
class TestProperty23CorsHeadersOnAllResponses:
    """Property 23: CORS Headers on All Responses."""

    @settings(max_examples=100)
    @given(body=valid_body_strategy)
    def test_cors_headers_on_valid_requests(self, body: dict[str, Any]) -> None:
        # Property 23: CORS Headers on All Responses
        # Validates: Requirements NFR-CORS-1
        event = {'body': json.dumps(body)}
        mock_context = MagicMock()
        mock_context.aws_request_id = REQUEST_ID

        mock_bedrock = MagicMock()
        mock_bedrock.converse_stream.return_value = {
            'stream': _make_stream_events(),
        }

        mock_kb = MagicMock()
        mock_kb.retrieve.return_value = {'retrievalResults': []}

        with patch.object(handler, 'bedrock_runtime', mock_bedrock), \
             patch.object(handler, 'bedrock_agent_runtime', mock_kb):
            result = handler.lambda_handler(event, mock_context)

        _assert_cors_headers(result)

    @settings(max_examples=100)
    @given(body=invalid_body_strategy)
    def test_cors_headers_on_invalid_requests(self, body: dict[str, Any]) -> None:
        # Property 23: CORS Headers on All Responses
        # Validates: Requirements NFR-CORS-1
        event = {'body': json.dumps(body)}
        mock_context = MagicMock()
        mock_context.aws_request_id = REQUEST_ID

        mock_bedrock = MagicMock()
        mock_kb = MagicMock()

        with patch.object(handler, 'bedrock_runtime', mock_bedrock), \
             patch.object(handler, 'bedrock_agent_runtime', mock_kb):
            result = handler.lambda_handler(event, mock_context)

        _assert_cors_headers(result)

    @settings(max_examples=100)
    @given(body_str=st.one_of(
        st.just(''),
        st.just(None),
        st.just('not json{'),
        st.just('[]'),
        st.just('"string"'),
    ))
    def test_cors_headers_on_malformed_bodies(self, body_str: str | None) -> None:
        # Property 23: CORS Headers on All Responses — malformed bodies
        # Validates: Requirements NFR-CORS-1
        event: dict[str, Any] = {}
        if body_str is not None:
            event['body'] = body_str

        mock_context = MagicMock()
        mock_context.aws_request_id = REQUEST_ID

        with patch.object(handler, 'bedrock_runtime', MagicMock()), \
             patch.object(handler, 'bedrock_agent_runtime', MagicMock()):
            result = handler.lambda_handler(event, mock_context)

        _assert_cors_headers(result)

    @settings(max_examples=100)
    @given(body=valid_body_strategy)
    def test_cors_headers_on_500_errors(self, body: dict[str, Any]) -> None:
        # Property 23: CORS Headers on All Responses — server errors
        # Validates: Requirements NFR-CORS-1
        event = {'body': json.dumps(body)}
        mock_context = MagicMock()
        mock_context.aws_request_id = REQUEST_ID

        # Force an unhandled exception in handle_chat_request
        with patch.object(handler, 'handle_chat_request', side_effect=RuntimeError('boom')):
            result = handler.lambda_handler(event, mock_context)

        assert result['statusCode'] == 500
        _assert_cors_headers(result)
