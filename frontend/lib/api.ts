import type { QuestionnaireData } from './session';

// --- Error Types ---

export type ChatErrorType = 'network' | 'timeout' | 'server' | 'client';

export class ChatError extends Error {
  type: ChatErrorType;
  status?: number;

  constructor(message: string, type: ChatErrorType, status?: number) {
    super(message);
    this.name = 'ChatError';
    this.type = type;
    this.status = status;
  }
}

// --- SSE Event Types ---

export interface TextDeltaEvent {
  type: 'text-delta';
  content: string;
}

export interface CitationsEvent {
  type: 'citations';
  sources: string[];
}

export interface FinishEvent {
  type: 'finish';
  usage: { input_tokens: number; output_tokens: number };
}

export interface ErrorEvent {
  type: 'error';
  message: string;
}

export type SSEEvent = TextDeltaEvent | CitationsEvent | FinishEvent | ErrorEvent;

// --- Configuration ---

const API_URL = process.env.NEXT_PUBLIC_API_URL!;
const REQUEST_TIMEOUT_MS = 30_000;
const MAX_RETRIES = 3;
const BASE_BACKOFF_MS = 1000;

// --- API Client ---

export interface ChatRequestBody {
  message: string;
  session_id: string;
  context: {
    academic_year: QuestionnaireData['academic_year'];
    major: string;
    advising_topic: QuestionnaireData['advising_topic'];
  };
}

/**
 * Sends a chat message to the API and returns a ReadableStream reader for SSE parsing.
 * Implements retry with exponential backoff for 5xx errors (max 3 attempts).
 * Uses AbortController with 30s timeout.
 */
export async function sendChatMessage(
  message: string,
  sessionId: string,
  context: ChatRequestBody['context'],
  signal?: AbortSignal
): Promise<ReadableStreamDefaultReader<Uint8Array>> {
  const body: ChatRequestBody = {
    message,
    session_id: sessionId,
    context,
  };

  let lastError: ChatError | null = null;

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    // If an external signal is provided, abort our controller when it fires
    const externalAbortHandler = () => controller.abort();
    if (signal) {
      signal.addEventListener('abort', externalAbortHandler);
    }

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const reader = response.body?.getReader();
        if (!reader) {
          throw new ChatError(
            'Response body is not readable',
            'server',
            response.status
          );
        }
        return reader;
      }

      // 4xx errors: don't retry
      if (response.status >= 400 && response.status < 500) {
        let errorMessage = `Request error (${response.status})`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.error || errorData.message || errorMessage;
        } catch {
          // Use default error message
        }
        throw new ChatError(errorMessage, 'client', response.status);
      }

      // 5xx errors: retry with backoff
      lastError = new ChatError(
        `Server error (${response.status}). Please try again.`,
        'server',
        response.status
      );
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof ChatError) {
        // Don't retry client errors
        if (error.type === 'client') throw error;
        lastError = error;
      } else if (error instanceof Error) {
        if (error.name === 'AbortError') {
          // Check if it was the external signal or our timeout
          if (signal?.aborted) {
            throw new ChatError('Request was cancelled.', 'network');
          }
          throw new ChatError(
            'Request timed out. Please try again.',
            'timeout'
          );
        }
        lastError = new ChatError(
          'Network error. Please check your connection.',
          'network'
        );
      }
    } finally {
      if (signal) {
        signal.removeEventListener('abort', externalAbortHandler);
      }
    }

    // Exponential backoff: 1s, 2s, 4s
    if (attempt < MAX_RETRIES - 1) {
      await new Promise((resolve) =>
        setTimeout(resolve, BASE_BACKOFF_MS * Math.pow(2, attempt))
      );
    }
  }

  throw lastError ?? new ChatError('Request failed after retries.', 'server');
}

/**
 * Parses an SSE stream from a ReadableStream reader.
 * Calls onEvent for each parsed SSE event.
 * Handles `data: {json}\n\n` format.
 */
export async function parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (event: SSEEvent) => void
): Promise<void> {
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      // Keep the last incomplete part in the buffer
      buffer = parts.pop() || '';

      for (const part of parts) {
        const lines = part.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.substring(6);
            try {
              const event = JSON.parse(jsonStr) as SSEEvent;
              onEvent(event);
            } catch {
              // Skip malformed JSON lines
            }
          }
        }
      }
    }

    // Process any remaining buffer content
    if (buffer.trim()) {
      const lines = buffer.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const jsonStr = line.substring(6);
          try {
            const event = JSON.parse(jsonStr) as SSEEvent;
            onEvent(event);
          } catch {
            // Skip malformed JSON lines
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
