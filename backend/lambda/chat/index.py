"""
Chat Lambda handler — ASU Academic Advising Chatbot (GUIDE).

Phase 2 implementation: handler scaffolding with structured logging,
module-level AWS clients, and thin handler pattern.

Tasks 15–19 will implement validation, retrieval, prompt construction,
streaming, and CORS helper logic.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Module-level AWS clients (reused across warm invocations per backend-standards.md)
# Task 14.1
# ---------------------------------------------------------------------------
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
bedrock_runtime = boto3.client('bedrock-runtime')

# ---------------------------------------------------------------------------
# Environment variables — read at module level using os.environ.get()
# Task 14.2
# ---------------------------------------------------------------------------
KNOWLEDGE_BASE_ID: str | None = os.environ.get('KNOWLEDGE_BASE_ID')
MODEL_ID: str | None = os.environ.get('MODEL_ID')
NUM_KB_RESULTS: int = int(os.environ.get('NUM_KB_RESULTS', '5'))
MAX_TOKENS: int = int(os.environ.get('MAX_TOKENS', '4096'))
TEMPERATURE: float = float(os.environ.get('TEMPERATURE', '0.7'))
CORS_ALLOWED_ORIGIN: str = os.environ.get('CORS_ALLOWED_ORIGIN', 'http://localhost:3000')
LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')

# ---------------------------------------------------------------------------
# Structured JSON logger — Task 14.3
# Validates Property P31 (Lambda Structured Logging)
# ---------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)


def log_event(
    level: str,
    action: str,
    request_id: str,
    **extra: Any,
) -> None:
    """Emit a structured JSON log entry.

    Every entry includes ``timestamp`` (ISO 8601), ``level``, ``action``, and
    ``request_id``.  Additional keyword arguments are merged into the payload.

    Property P32 (No PII in Logs) — callers must never pass full message
    content; use a length indicator or truncated hash instead.
    """
    entry: dict[str, Any] = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'level': level.upper(),
        'action': action,
        'request_id': request_id,
    }
    entry.update(extra)

    log_method = getattr(logger, level.lower(), logger.info)
    log_method(json.dumps(entry))


# ---------------------------------------------------------------------------
# CORS helper — Task 14.4 (also refined in Task 19)
# Validates Property P23 (CORS Headers on All Responses)
# ---------------------------------------------------------------------------

def build_cors_headers() -> dict[str, str]:
    """Return CORS headers using the configured allowed origin."""
    return {
        'Access-Control-Allow-Origin': CORS_ALLOWED_ORIGIN,
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
    }


# ---------------------------------------------------------------------------
# System Prompt Template — Task 17
# Validates Properties: P13 (Student Context Inclusion), P14 (System Prompt Structure),
#   P15 (No User Input in Instructions)
# Requirements: FR-QUESTIONNAIRE-2, FR-CHAT-2, NFR-SECURITY-3
#
# Security note (P15): User-provided values are injected ONLY into the named
# placeholders in the "Student Context" section.  The instruction text contains
# no placeholders and is therefore immune to format-string injection.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_TEMPLATE: str = """\
You are GUIDE, an AI academic advising assistant for Arizona State University (ASU).
You help students with academic advising questions using official ASU academic documents.

## Student Context
- Academic Year: {academic_year}
- Major: {major}
- Advising Topic: {advising_topic}

## Instructions
1. Answer questions using ONLY the retrieved ASU documents below.
2. If the documents do not contain relevant information, say so clearly.
   Do not fabricate course numbers, prerequisites, policies, or deadlines.
3. Tailor your response to the student's academic year and major.
4. Be concise, specific, and cite the source document when possible.
5. For course planning questions, mention prerequisites and co-requisites.
6. For degree requirement questions, reference the specific catalog year.
7. If the student asks something outside academic advising, politely redirect.

## Retrieved ASU Documents
{retrieved_context}"""

NO_DOCUMENTS_NOTE: str = 'No documents were retrieved for this query.'


# ---------------------------------------------------------------------------
# Validation constants — Task 15
# ---------------------------------------------------------------------------
MAX_MESSAGE_LENGTH: int = 2000
MIN_SESSION_ID_LENGTH: int = 33
MAX_MAJOR_LENGTH: int = 200

VALID_ACADEMIC_YEARS: frozenset[str] = frozenset({
    'Freshman', 'Sophomore', 'Junior', 'Senior', 'Graduate',
})

VALID_ADVISING_TOPICS: frozenset[str] = frozenset({
    'Course Planning', 'Degree Requirements', 'Academic Standing', 'General Advising',
})


# ---------------------------------------------------------------------------
# Request validation — Task 15
# Validates Properties: P1–P6 (Input Validation), P32 (No PII in Logs)
# Requirements: FR-CHAT-1, FR-QUESTIONNAIRE-1, FR-SESSION-1, NFR-SECURITY-2, NFR-SECURITY-3
# ---------------------------------------------------------------------------

def _build_error_response(status_code: int, error_message: str) -> dict[str, Any]:
    """Build an API Gateway error response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            **build_cors_headers(),
        },
        'body': json.dumps({'error': error_message}),
    }


def validate_request(
    event: dict[str, Any],
    request_id: str,
) -> dict[str, Any] | dict[str, Any]:
    """Parse and validate the incoming chat request.

    Returns the parsed body dict on success, or an API Gateway error response
    dict on failure.  Callers distinguish the two by checking for a
    ``statusCode`` key (present only in error responses).

    Property P32 — logs field name and reason only, never message content.
    """
    # --- 15.1: Parse JSON body ---
    raw_body: str | None = event.get('body')
    if not raw_body:
        log_event('warning', 'validation_failed', request_id,
                  field='body', reason='missing')
        return _build_error_response(400, 'Request body is required')

    try:
        body: dict[str, Any] = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError):
        log_event('warning', 'validation_failed', request_id,
                  field='body', reason='invalid_json')
        return _build_error_response(400, 'Request body must be valid JSON')

    if not isinstance(body, dict):
        log_event('warning', 'validation_failed', request_id,
                  field='body', reason='not_an_object')
        return _build_error_response(400, 'Request body must be a JSON object')

    # --- 15.2: Validate message ---
    message: Any = body.get('message')
    if not isinstance(message, str) or not message.strip():
        log_event('warning', 'validation_failed', request_id,
                  field='message', reason='missing_or_empty')
        return _build_error_response(400, 'Message is required')

    if len(message.strip()) > MAX_MESSAGE_LENGTH:
        log_event('warning', 'validation_failed', request_id,
                  field='message', reason='exceeds_max_length',
                  length=len(message.strip()))
        return _build_error_response(400, 'Message exceeds maximum length')

    # Normalise whitespace for downstream consumers
    body['message'] = message.strip()

    # --- 15.3: Validate session_id ---
    session_id: Any = body.get('session_id')
    if not isinstance(session_id, str) or len(session_id) < MIN_SESSION_ID_LENGTH:
        log_event('warning', 'validation_failed', request_id,
                  field='session_id', reason='missing_or_too_short',
                  min_length=MIN_SESSION_ID_LENGTH)
        return _build_error_response(400, 'Invalid session_id format')

    # --- 15.4–15.6: Validate context object ---
    context: Any = body.get('context')
    if not isinstance(context, dict):
        log_event('warning', 'validation_failed', request_id,
                  field='context', reason='missing_or_invalid')
        return _build_error_response(400, 'Context object is required')

    # 15.4: academic_year
    academic_year: Any = context.get('academic_year')
    if academic_year not in VALID_ACADEMIC_YEARS:
        log_event('warning', 'validation_failed', request_id,
                  field='context.academic_year', reason='invalid_value')
        return _build_error_response(400, 'Invalid academic_year value')

    # 15.5: major
    major: Any = context.get('major')
    if not isinstance(major, str) or not major.strip():
        log_event('warning', 'validation_failed', request_id,
                  field='context.major', reason='missing_or_empty')
        return _build_error_response(400, 'Major is required')

    if len(major.strip()) > MAX_MAJOR_LENGTH:
        log_event('warning', 'validation_failed', request_id,
                  field='context.major', reason='exceeds_max_length',
                  length=len(major.strip()))
        return _build_error_response(400, 'Major exceeds maximum length')

    # Normalise whitespace
    context['major'] = major.strip()

    # 15.6: advising_topic
    advising_topic: Any = context.get('advising_topic')
    if advising_topic not in VALID_ADVISING_TOPICS:
        log_event('warning', 'validation_failed', request_id,
                  field='context.advising_topic', reason='invalid_value')
        return _build_error_response(400, 'Invalid advising_topic value')

    return body


# ---------------------------------------------------------------------------
# KB Retrieval — Task 16
# Validates Properties: P7 (Retrieval Invocation), P8 (Retrieval Result Count),
#   P9 (Context Injection), P10 (Empty Retrieval Graceful Handling),
#   P11 (Retrieval Failure Resilience), P12 (Citation Extraction)
# Requirements: FR-RAG-1, FR-RAG-2, FR-RAG-3, NFR-RELIABILITY-1
# ---------------------------------------------------------------------------

def retrieve_from_kb(message: str, request_id: str) -> tuple[str, list[str]]:
    """Retrieve relevant documents from the Bedrock Knowledge Base.

    Calls ``bedrock_agent_runtime.retrieve()`` with the user's message as the
    retrieval query and returns extracted text context and S3 source URIs.

    Args:
        message: The user's chat message used as the retrieval query.
        request_id: Lambda request ID for structured logging.

    Returns:
        A tuple of ``(context_string, citations_list)`` where:
        - ``context_string`` is the retrieved text chunks joined with double
          newlines, or an empty string if no results / on error.
        - ``citations_list`` is a list of S3 URIs extracted from result
          metadata, or an empty list if none available / on error.

    Property P11 — this function never raises.  All exceptions are caught,
    logged at ERROR level, and the function returns empty context.
    Property P32 — never logs the full user message; logs message length only.
    """
    try:
        # 16.1 + 16.2: Call retrieve() with knowledgeBaseId and numberOfResults
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={'text': message},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': NUM_KB_RESULTS,
                },
            },
        )

        retrieval_results: list[dict[str, Any]] = response.get('retrievalResults', [])

        # 16.5: Handle empty results gracefully
        if not retrieval_results:
            log_event('info', 'kb_retrieval_empty', request_id,
                      message_length=len(message),
                      num_results=0)
            return '', []

        # 16.3: Extract text content and join with double newlines
        text_chunks: list[str] = []
        for result in retrieval_results:
            content = result.get('content', {})
            text = content.get('text', '')
            if text:
                text_chunks.append(text)

        context_string = '\n\n'.join(text_chunks)

        # 16.4: Extract S3 source URIs from result metadata
        citations: list[str] = []
        for result in retrieval_results:
            location = result.get('location', {})
            s3_location = location.get('s3Location', {})
            uri = s3_location.get('uri', '')
            if uri and uri not in citations:
                citations.append(uri)

        log_event('info', 'kb_retrieval_success', request_id,
                  message_length=len(message),
                  num_results=len(retrieval_results),
                  num_text_chunks=len(text_chunks),
                  num_citations=len(citations))

        return context_string, citations

    except Exception:
        # 16.6: Handle retrieval exceptions — log error, proceed with empty context
        log_event('error', 'kb_retrieval_failed', request_id,
                  message_length=len(message))
        return '', []


# ---------------------------------------------------------------------------
# Prompt Construction — Task 17
# Validates Properties: P13 (Student Context Inclusion), P14 (System Prompt Structure),
#   P15 (No User Input in Instructions)
# Requirements: FR-QUESTIONNAIRE-2, FR-CHAT-2, NFR-SECURITY-3
# ---------------------------------------------------------------------------

def build_system_prompt(context: dict[str, str], retrieved_context: str) -> str:
    """Build the system prompt from student context and retrieved documents.

    Injects ``academic_year``, ``major``, and ``advising_topic`` from the
    validated *context* dict into the ``## Student Context`` section of the
    template, and places *retrieved_context* into the
    ``## Retrieved ASU Documents`` section.

    Args:
        context: Validated request context with keys ``academic_year``,
            ``major``, and ``advising_topic``.
        retrieved_context: Text chunks retrieved from the Bedrock Knowledge
            Base, joined with double newlines.  May be empty.

    Returns:
        The fully constructed system prompt string.

    Security (P15): User-provided values are substituted ONLY into the named
    placeholders inside the Student Context block.  The instruction text is
    static and contains no placeholders, so user input can never appear there.
    """
    effective_context: str = (
        retrieved_context if retrieved_context.strip() else NO_DOCUMENTS_NOTE
    )

    return SYSTEM_PROMPT_TEMPLATE.format(
        academic_year=context['academic_year'],
        major=context['major'],
        advising_topic=context['advising_topic'],
        retrieved_context=effective_context,
    )


# ---------------------------------------------------------------------------
# Streaming Response — Task 18
# Validates Properties: P16 (Model ID Correctness), P17 (Inference Config Bounds),
#   P18 (SSE Format Compliance), P19 (Stream Termination), P20 (Chunk Content Type),
#   P21 (Stream Error Event), P22 (No Empty Streams), P23 (CORS Headers on All Responses)
# Requirements: FR-CHAT-3, FR-STREAM-1, FR-STREAM-2, NFR-CORS-1
# ---------------------------------------------------------------------------

def _build_sse_headers() -> dict[str, str]:
    """Return response headers for an SSE stream response."""
    return {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        **build_cors_headers(),
    }


def _format_sse_event(payload: dict[str, Any]) -> str:
    """Format a single SSE data line: ``data: {json}\n\n``."""
    return f'data: {json.dumps(payload)}\n\n'


def stream_response(
    system_prompt: str,
    message: str,
    citations: list[str],
    request_id: str,
) -> dict[str, Any]:
    """Call Bedrock converse_stream and build an SSE response body.

    Since REST API V1 does not support true chunked streaming from Lambda,
    all SSE events are collected into a single response body string.

    Args:
        system_prompt: Fully constructed system prompt with student context
            and retrieved documents.
        message: The user's chat message.
        citations: List of S3 source URIs from KB retrieval.
        request_id: Lambda request ID for structured logging.

    Returns:
        API Gateway response dict with SSE-formatted body.
    """
    try:
        # 18.1 + 18.2: Call converse_stream with model ID and inference config
        log_event('info', 'bedrock_stream_start', request_id,
                  model_id=MODEL_ID,
                  max_tokens=MAX_TOKENS,
                  temperature=TEMPERATURE)

        response = bedrock_runtime.converse_stream(
            modelId=MODEL_ID,
            messages=[{'role': 'user', 'content': [{'text': message}]}],
            system=[{'text': system_prompt}],
            inferenceConfig={
                'maxTokens': MAX_TOKENS,
                'temperature': TEMPERATURE,
            },
        )

        # 18.3: Iterate over stream events and collect SSE chunks
        sse_body_parts: list[str] = []
        usage: dict[str, int] = {'input_tokens': 0, 'output_tokens': 0}
        has_text_content = False

        try:
            for event in response.get('stream', []):
                # Text content delta
                if 'contentBlockDelta' in event:
                    delta = event['contentBlockDelta'].get('delta', {})
                    text = delta.get('text', '')
                    if text:
                        has_text_content = True
                        sse_body_parts.append(
                            _format_sse_event({'type': 'text-delta', 'content': text})
                        )

                # Token usage metadata
                elif 'metadata' in event:
                    meta_usage = event['metadata'].get('usage', {})
                    usage['input_tokens'] = meta_usage.get('inputTokens', 0)
                    usage['output_tokens'] = meta_usage.get('outputTokens', 0)

        except Exception:
            # 18.6: Error mid-stream — emit error SSE event before closing
            log_event('error', 'bedrock_stream_error_midstream', request_id)
            sse_body_parts.append(
                _format_sse_event({
                    'type': 'error',
                    'message': 'An error occurred while generating the response',
                })
            )
            return {
                'statusCode': 200,
                'headers': _build_sse_headers(),
                'body': ''.join(sse_body_parts),
            }

        # P22: Guarantee non-empty stream — if no text was produced, emit a notice
        if not has_text_content:
            sse_body_parts.append(
                _format_sse_event({
                    'type': 'text-delta',
                    'content': 'I was unable to generate a response. Please try again.',
                })
            )

        # 18.4: Emit citations event
        sse_body_parts.append(
            _format_sse_event({'type': 'citations', 'sources': citations})
        )

        # 18.5: Emit finish event with token usage
        sse_body_parts.append(
            _format_sse_event({'type': 'finish', 'usage': usage})
        )

        log_event('info', 'bedrock_stream_complete', request_id,
                  input_tokens=usage['input_tokens'],
                  output_tokens=usage['output_tokens'],
                  num_citations=len(citations))

        return {
            'statusCode': 200,
            'headers': _build_sse_headers(),
            'body': ''.join(sse_body_parts),
        }

    except ClientError as exc:
        error_code = exc.response.get('Error', {}).get('Code', '')

        # 18.7: Handle Bedrock throttling
        if error_code == 'ThrottlingException':
            log_event('warning', 'bedrock_throttled', request_id)
            return {
                'statusCode': 429,
                'headers': {
                    'Content-Type': 'application/json',
                    **build_cors_headers(),
                },
                'body': json.dumps({'error': 'Service busy, please try again'}),
            }

        # Other Bedrock errors before streaming starts → 500
        log_event('error', 'bedrock_converse_failed', request_id,
                  error_code=error_code)
        return _build_error_response(500, 'Failed to generate response')

    except Exception:
        log_event('error', 'stream_response_unhandled', request_id)
        return _build_error_response(500, 'Failed to generate response')


# ---------------------------------------------------------------------------
# Internal handler — orchestration for tasks 15–19
# ---------------------------------------------------------------------------

def handle_chat_request(event: dict[str, Any], request_id: str) -> dict[str, Any]:
    """Process a chat request end-to-end.

    This function is the main orchestration point.  Each step below will be
    implemented by a subsequent task:

    1. Validate input          — Task 15
    2. Retrieve from KB        — Task 16
    3. Construct system prompt  — Task 17
    4. Stream response          — Task 18
    5. (CORS applied by caller) — Task 19

    Returns an API Gateway-compatible response dict.
    """
    # --- Task 15: Input validation ---
    result = validate_request(event, request_id)
    if 'statusCode' in result:
        return result
    parsed_body: dict[str, Any] = result

    log_event('info', 'validation_passed', request_id,
              session_id=parsed_body.get('session_id'),
              message_length=len(parsed_body['message']))

    # --- Task 16: KB retrieval ---
    retrieved_context, citations = retrieve_from_kb(parsed_body['message'], request_id)

    # --- Task 17: Prompt construction ---
    system_prompt = build_system_prompt(parsed_body['context'], retrieved_context)

    log_event('info', 'prompt_constructed', request_id,
              prompt_length=len(system_prompt),
              has_retrieved_context=bool(retrieved_context.strip()))

    # --- Task 18: Streaming response ---
    return stream_response(system_prompt, parsed_body['message'], citations, request_id)


# ---------------------------------------------------------------------------
# Lambda entry point — thin handler pattern (Task 14.4)
# Validates Properties: P31 (Lambda Structured Logging), P23 (CORS Headers)
# Requirements: FR-CHAT-1, NFR-OBSERVABILITY-1, NFR-CORS-1
# ---------------------------------------------------------------------------

def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point.  Delegates to ``handle_chat_request``."""
    request_id: str = getattr(context, 'aws_request_id', 'unknown')

    log_event('info', 'chat_request_received', request_id)

    try:
        return handle_chat_request(event, request_id)
    except Exception:
        log_event('error', 'unhandled_exception', request_id)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                **build_cors_headers(),
            },
            'body': json.dumps({'error': 'Internal server error'}),
        }
