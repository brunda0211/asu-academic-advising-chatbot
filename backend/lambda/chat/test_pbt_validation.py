"""Task 36 — Property-based tests for input validation.

Uses hypothesis to generate adversarial inputs and verify validation invariants.
Validates Properties: P1–P6
Requirements: FR-CHAT-1, FR-QUESTIONNAIRE-1, FR-SESSION-1
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
REQUEST_ID = 'pbt-validation-request-id'

VALID_ACADEMIC_YEARS = ['Freshman', 'Sophomore', 'Junior', 'Senior', 'Graduate']
VALID_ADVISING_TOPICS = ['Course Planning', 'Degree Requirements', 'Academic Standing', 'General Advising']


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


def _make_event(body: dict[str, Any]) -> dict[str, Any]:
    return {'body': json.dumps(body)}


# ---------------------------------------------------------------------------
# 36.1 — Property 1: Message Presence
# Generate empty/None messages, verify 400 and no Bedrock invocation
# Validates: Requirements FR-CHAT-1, NFR-SECURITY-2
# ---------------------------------------------------------------------------
class TestProperty1MessagePresence:
    """Property 1: Message Presence — empty/None messages must return 400."""

    @settings(max_examples=100, deadline=5000)
    @given(st.one_of(
        st.just(''),
        st.just(None),
        st.text(alphabet=' \t\n\r', min_size=1, max_size=50),
    ))
    def test_empty_or_none_messages_return_400(self, message: str | None) -> None:
        # Property 1: Message Presence
        # Validates: Requirements FR-CHAT-1, NFR-SECURITY-2
        body = _valid_body()
        body['message'] = message
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' in result
        assert result['statusCode'] == 400

    @settings(max_examples=100, deadline=5000)
    @given(st.one_of(
        st.just(''),
        st.just(None),
        st.text(alphabet=' \t\n\r', min_size=1, max_size=50),
    ))
    def test_empty_messages_never_invoke_bedrock(self, message: str | None) -> None:
        # Property 1: Message Presence — no Bedrock invocation on invalid input
        # Validates: Requirements FR-CHAT-1
        body = _valid_body()
        body['message'] = message
        event = _make_event(body)

        mock_context = MagicMock()
        mock_context.aws_request_id = REQUEST_ID

        mock_kb = MagicMock()
        mock_bedrock = MagicMock()

        with patch.object(handler, 'bedrock_agent_runtime', mock_kb), \
             patch.object(handler, 'bedrock_runtime', mock_bedrock):
            handler.lambda_handler(event, mock_context)

        mock_kb.retrieve.assert_not_called()
        mock_bedrock.converse_stream.assert_not_called()


# ---------------------------------------------------------------------------
# 36.2 — Property 2: Message Length Bound
# Generate strings > 2000 chars, verify 400
# Validates: Requirements FR-CHAT-1, NFR-SECURITY-2
# ---------------------------------------------------------------------------
class TestProperty2MessageLengthBound:
    """Property 2: Message Length Bound — messages > 2000 chars must return 400."""

    @settings(max_examples=100, deadline=5000)
    @given(st.text(min_size=2001, max_size=5000))
    def test_oversized_messages_return_400(self, message: str) -> None:
        # Property 2: Message Length Bound
        # Validates: Requirements FR-CHAT-1, NFR-SECURITY-2
        assume(len(message.strip()) > 2000)
        body = _valid_body()
        body['message'] = message
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' in result
        assert result['statusCode'] == 400


# ---------------------------------------------------------------------------
# 36.3 — Property 3: Session ID Format
# Generate strings < 33 chars, verify 400
# Validates: Requirements FR-SESSION-1
# ---------------------------------------------------------------------------
class TestProperty3SessionIdFormat:
    """Property 3: Session ID Format — session IDs < 33 chars must return 400."""

    @settings(max_examples=100, deadline=5000)
    @given(st.text(min_size=0, max_size=32))
    def test_short_session_ids_return_400(self, session_id: str) -> None:
        # Property 3: Session ID Format
        # Validates: Requirements FR-SESSION-1
        body = _valid_body()
        body['session_id'] = session_id
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' in result
        assert result['statusCode'] == 400


# ---------------------------------------------------------------------------
# 36.4 — Property 4: Academic Year Enum
# Generate strings not in allowed set, verify 400
# Validates: Requirements FR-QUESTIONNAIRE-1
# ---------------------------------------------------------------------------
class TestProperty4AcademicYearEnum:
    """Property 4: Academic Year Enum — invalid values must return 400."""

    @settings(max_examples=100, deadline=5000)
    @given(st.text(min_size=0, max_size=100))
    def test_invalid_academic_years_return_400(self, year: str) -> None:
        # Property 4: Academic Year Enum
        # Validates: Requirements FR-QUESTIONNAIRE-1
        assume(year not in VALID_ACADEMIC_YEARS)
        body = _valid_body()
        body['context']['academic_year'] = year
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' in result
        assert result['statusCode'] == 400


# ---------------------------------------------------------------------------
# 36.5 — Property 5: Major Field Presence
# Generate empty/oversized strings, verify 400
# Validates: Requirements FR-QUESTIONNAIRE-1
# ---------------------------------------------------------------------------
class TestProperty5MajorFieldPresence:
    """Property 5: Major Field Presence — empty or oversized majors must return 400."""

    @settings(max_examples=100, deadline=5000)
    @given(st.one_of(
        st.just(''),
        st.text(alphabet=' \t\n\r', min_size=1, max_size=50),
        st.text(min_size=201, max_size=500),
    ))
    def test_invalid_majors_return_400(self, major: str) -> None:
        # Property 5: Major Field Presence
        # Validates: Requirements FR-QUESTIONNAIRE-1
        # Empty/whitespace-only or oversized (> 200 chars after strip)
        is_empty = not major.strip()
        is_oversized = len(major.strip()) > 200
        assume(is_empty or is_oversized)

        body = _valid_body()
        body['context']['major'] = major
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' in result
        assert result['statusCode'] == 400


# ---------------------------------------------------------------------------
# 36.6 — Property 6: Advising Topic Enum
# Generate strings not in allowed set, verify 400
# Validates: Requirements FR-QUESTIONNAIRE-1
# ---------------------------------------------------------------------------
class TestProperty6AdvisingTopicEnum:
    """Property 6: Advising Topic Enum — invalid values must return 400."""

    @settings(max_examples=100, deadline=5000)
    @given(st.text(min_size=0, max_size=100))
    def test_invalid_advising_topics_return_400(self, topic: str) -> None:
        # Property 6: Advising Topic Enum
        # Validates: Requirements FR-QUESTIONNAIRE-1
        assume(topic not in VALID_ADVISING_TOPICS)
        body = _valid_body()
        body['context']['advising_topic'] = topic
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' in result
        assert result['statusCode'] == 400
