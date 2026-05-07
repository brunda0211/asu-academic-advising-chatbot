"""Tests for Task 15 — request validation in the Chat Lambda handler.

Validates correctness properties P1–P6 and P32 (No PII in Logs).
Uses unittest.mock to patch boto3 clients so no AWS credentials are needed.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Patch boto3 clients before importing the handler module so module-level
# client creation doesn't require real AWS credentials.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _patch_boto3(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('KNOWLEDGE_BASE_ID', 'test-kb-id')
    monkeypatch.setenv('MODEL_ID', 'us.amazon.nova-lite-v1:0')
    monkeypatch.setenv('CORS_ALLOWED_ORIGIN', 'http://localhost:3000')


def _import_handler():
    """Import (or reimport) the handler module with patched boto3."""
    with patch('boto3.client', return_value=MagicMock()):
        import importlib
        import backend.lambda_.chat.index as mod  # noqa: N813
        importlib.reload(mod)
        return mod


# We import once at module level with patching for convenience.
with patch('boto3.client', return_value=MagicMock()):
    # Python doesn't allow 'lambda' as a package name, so we use importlib.
    import importlib
    import sys
    import os

    # Add the lambda/chat directory to sys.path so we can import index directly.
    _chat_dir = os.path.join(os.path.dirname(__file__))
    if _chat_dir not in sys.path:
        sys.path.insert(0, _chat_dir)

    import index as handler  # type: ignore[import-untyped]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
REQUEST_ID = 'test-request-id-12345'


def _make_event(body: dict[str, Any] | str | None = None) -> dict[str, Any]:
    """Build a minimal API Gateway proxy event."""
    event: dict[str, Any] = {}
    if body is not None:
        event['body'] = body if isinstance(body, str) else json.dumps(body)
    return event


def _valid_body() -> dict[str, Any]:
    """Return a fully valid request body."""
    return {
        'message': 'What are the prerequisites for CSE 310?',
        'session_id': 'session_1234567890123_abcdefghijk',
        'context': {
            'academic_year': 'Junior',
            'major': 'Computer Science',
            'advising_topic': 'Course Planning',
        },
    }


def _assert_error(response: dict[str, Any], status: int, fragment: str) -> None:
    """Assert the response is an error with the expected status and message fragment."""
    assert response['statusCode'] == status
    body = json.loads(response['body'])
    assert 'error' in body
    assert fragment.lower() in body['error'].lower(), (
        f"Expected '{fragment}' in error message, got: {body['error']}"
    )
    # P23: CORS headers must be present on all error responses
    assert 'Access-Control-Allow-Origin' in response['headers']
    assert 'Access-Control-Allow-Methods' in response['headers']


# ---------------------------------------------------------------------------
# 15.1 — Parse JSON body
# ---------------------------------------------------------------------------
class TestParseBody:
    """P1 partial: body must be present and valid JSON."""

    def test_missing_body_returns_400(self) -> None:
        result = handler.validate_request({}, REQUEST_ID)
        _assert_error(result, 400, 'body is required')

    def test_empty_string_body_returns_400(self) -> None:
        result = handler.validate_request({'body': ''}, REQUEST_ID)
        _assert_error(result, 400, 'body is required')

    def test_none_body_returns_400(self) -> None:
        result = handler.validate_request({'body': None}, REQUEST_ID)
        _assert_error(result, 400, 'body is required')

    def test_invalid_json_returns_400(self) -> None:
        result = handler.validate_request({'body': 'not json{'}, REQUEST_ID)
        _assert_error(result, 400, 'valid JSON')

    def test_json_array_returns_400(self) -> None:
        result = handler.validate_request({'body': '[]'}, REQUEST_ID)
        _assert_error(result, 400, 'JSON object')

    def test_json_string_returns_400(self) -> None:
        result = handler.validate_request({'body': '"hello"'}, REQUEST_ID)
        _assert_error(result, 400, 'JSON object')


# ---------------------------------------------------------------------------
# 15.2 — Validate message field (P1, P2)
# ---------------------------------------------------------------------------
class TestMessageValidation:
    """P1: Message Presence, P2: Message Length Bound."""

    def test_missing_message_returns_400(self) -> None:
        body = _valid_body()
        del body['message']
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'Message is required')

    def test_empty_message_returns_400(self) -> None:
        body = _valid_body()
        body['message'] = ''
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'Message is required')

    def test_whitespace_only_message_returns_400(self) -> None:
        body = _valid_body()
        body['message'] = '   \t\n  '
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'Message is required')

    def test_non_string_message_returns_400(self) -> None:
        body = _valid_body()
        body['message'] = 12345
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'Message is required')

    def test_message_at_max_length_passes(self) -> None:
        body = _valid_body()
        body['message'] = 'a' * 2000
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' not in result

    def test_message_exceeds_max_length_returns_400(self) -> None:
        body = _valid_body()
        body['message'] = 'a' * 2001
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'exceeds maximum length')

    def test_message_trimmed_before_length_check(self) -> None:
        """Whitespace padding should not count toward the 2000-char limit."""
        body = _valid_body()
        body['message'] = '  ' + 'a' * 2000 + '  '
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' not in result

    def test_message_is_stripped_in_output(self) -> None:
        body = _valid_body()
        body['message'] = '  hello world  '
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert result['message'] == 'hello world'


# ---------------------------------------------------------------------------
# 15.3 — Validate session_id (P3)
# ---------------------------------------------------------------------------
class TestSessionIdValidation:
    """P3: Session ID Format — missing or < 33 chars → 400."""

    def test_missing_session_id_returns_400(self) -> None:
        body = _valid_body()
        del body['session_id']
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'session_id')

    def test_short_session_id_returns_400(self) -> None:
        body = _valid_body()
        body['session_id'] = 'short'
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'session_id')

    def test_session_id_exactly_32_chars_returns_400(self) -> None:
        body = _valid_body()
        body['session_id'] = 'a' * 32
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'session_id')

    def test_session_id_exactly_33_chars_passes(self) -> None:
        body = _valid_body()
        body['session_id'] = 'a' * 33
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' not in result

    def test_non_string_session_id_returns_400(self) -> None:
        body = _valid_body()
        body['session_id'] = 12345
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'session_id')


# ---------------------------------------------------------------------------
# 15.4 — Validate context.academic_year (P4)
# ---------------------------------------------------------------------------
class TestAcademicYearValidation:
    """P4: Academic Year Enum."""

    @pytest.mark.parametrize('year', [
        'Freshman', 'Sophomore', 'Junior', 'Senior', 'Graduate',
    ])
    def test_valid_academic_years_pass(self, year: str) -> None:
        body = _valid_body()
        body['context']['academic_year'] = year
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' not in result

    @pytest.mark.parametrize('year', [
        'freshman', 'JUNIOR', 'senior', 'grad', 'Postdoc', '', None, 123,
    ])
    def test_invalid_academic_years_return_400(self, year: Any) -> None:
        body = _valid_body()
        body['context']['academic_year'] = year
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'academic_year')

    def test_missing_academic_year_returns_400(self) -> None:
        body = _valid_body()
        del body['context']['academic_year']
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'academic_year')


# ---------------------------------------------------------------------------
# 15.5 — Validate context.major (P5)
# ---------------------------------------------------------------------------
class TestMajorValidation:
    """P5: Major Field Presence — empty or > 200 chars → 400."""

    def test_missing_major_returns_400(self) -> None:
        body = _valid_body()
        del body['context']['major']
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'Major is required')

    def test_empty_major_returns_400(self) -> None:
        body = _valid_body()
        body['context']['major'] = ''
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'Major is required')

    def test_whitespace_only_major_returns_400(self) -> None:
        body = _valid_body()
        body['context']['major'] = '   '
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'Major is required')

    def test_major_at_max_length_passes(self) -> None:
        body = _valid_body()
        body['context']['major'] = 'A' * 200
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' not in result

    def test_major_exceeds_max_length_returns_400(self) -> None:
        body = _valid_body()
        body['context']['major'] = 'A' * 201
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'Major exceeds maximum length')

    def test_major_is_stripped_in_output(self) -> None:
        body = _valid_body()
        body['context']['major'] = '  Computer Science  '
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert result['context']['major'] == 'Computer Science'

    def test_non_string_major_returns_400(self) -> None:
        body = _valid_body()
        body['context']['major'] = 42
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'Major is required')


# ---------------------------------------------------------------------------
# 15.6 — Validate context.advising_topic (P6)
# ---------------------------------------------------------------------------
class TestAdvisingTopicValidation:
    """P6: Advising Topic Enum."""

    @pytest.mark.parametrize('topic', [
        'Course Planning', 'Degree Requirements',
        'Academic Standing', 'General Advising',
    ])
    def test_valid_topics_pass(self, topic: str) -> None:
        body = _valid_body()
        body['context']['advising_topic'] = topic
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' not in result

    @pytest.mark.parametrize('topic', [
        'course planning', 'DEGREE REQUIREMENTS', 'Other', '', None, 0,
    ])
    def test_invalid_topics_return_400(self, topic: Any) -> None:
        body = _valid_body()
        body['context']['advising_topic'] = topic
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'advising_topic')

    def test_missing_advising_topic_returns_400(self) -> None:
        body = _valid_body()
        del body['context']['advising_topic']
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'advising_topic')


# ---------------------------------------------------------------------------
# 15.4–15.6 — Missing context object
# ---------------------------------------------------------------------------
class TestContextObjectValidation:
    """Context must be a dict."""

    def test_missing_context_returns_400(self) -> None:
        body = _valid_body()
        del body['context']
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'Context object is required')

    def test_non_dict_context_returns_400(self) -> None:
        body = _valid_body()
        body['context'] = 'not a dict'
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'Context object is required')

    def test_null_context_returns_400(self) -> None:
        body = _valid_body()
        body['context'] = None
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        _assert_error(result, 400, 'Context object is required')


# ---------------------------------------------------------------------------
# 15.7 — CORS headers on all error responses (P23)
# ---------------------------------------------------------------------------
class TestCorsOnErrors:
    """P23: Every error response must include CORS headers."""

    def test_body_missing_error_has_cors(self) -> None:
        result = handler.validate_request({}, REQUEST_ID)
        assert result['headers']['Access-Control-Allow-Origin'] == 'http://localhost:3000'

    def test_invalid_json_error_has_cors(self) -> None:
        result = handler.validate_request({'body': '{'}, REQUEST_ID)
        assert 'Access-Control-Allow-Origin' in result['headers']

    def test_message_error_has_cors(self) -> None:
        body = _valid_body()
        body['message'] = ''
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'Access-Control-Allow-Origin' in result['headers']


# ---------------------------------------------------------------------------
# 15.8 — Logging: no PII (P32)
# ---------------------------------------------------------------------------
class TestNoPiiInLogs:
    """P32: Validation logs must not contain the user's message content."""

    def test_validation_passed_logs_length_not_content(self) -> None:
        """After successful validation, handle_chat_request logs message_length."""
        body = _valid_body()
        event = _make_event(body)

        with patch.object(handler, 'log_event') as mock_log:
            handler.handle_chat_request(event, REQUEST_ID)

        # Find the validation_passed log call
        passed_calls = [
            c for c in mock_log.call_args_list
            if c[0][1] == 'validation_passed'
        ]
        assert len(passed_calls) == 1
        kwargs = passed_calls[0][1]  # keyword args
        assert 'message_length' in kwargs
        # The actual message text must NOT appear in any kwarg value
        for value in kwargs.values():
            if isinstance(value, str):
                assert body['message'] not in value


# ---------------------------------------------------------------------------
# Happy path — full valid request
# ---------------------------------------------------------------------------
class TestHappyPath:
    """Valid request passes validation and returns parsed body."""

    def test_valid_request_returns_parsed_body(self) -> None:
        body = _valid_body()
        result = handler.validate_request(_make_event(body), REQUEST_ID)
        assert 'statusCode' not in result
        assert result['message'] == body['message']
        assert result['session_id'] == body['session_id']
        assert result['context']['academic_year'] == 'Junior'
        assert result['context']['major'] == 'Computer Science'
        assert result['context']['advising_topic'] == 'Course Planning'

    def test_handle_chat_request_returns_200_for_valid_input(self) -> None:
        body = _valid_body()
        event = _make_event(body)
        result = handler.handle_chat_request(event, REQUEST_ID)
        assert result['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in result['headers']

    def test_lambda_handler_returns_200_for_valid_input(self) -> None:
        body = _valid_body()
        event = _make_event(body)
        mock_context = MagicMock()
        mock_context.aws_request_id = 'req-123'
        result = handler.lambda_handler(event, mock_context)
        assert result['statusCode'] == 200

    def test_lambda_handler_returns_400_for_invalid_input(self) -> None:
        event = _make_event({'message': ''})
        mock_context = MagicMock()
        mock_context.aws_request_id = 'req-456'
        result = handler.lambda_handler(event, mock_context)
        assert result['statusCode'] == 400
        assert 'Access-Control-Allow-Origin' in result['headers']
