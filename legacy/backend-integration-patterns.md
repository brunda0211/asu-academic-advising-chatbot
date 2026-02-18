---
inclusion: fileMatch
fileMatchPattern: "frontend/**/lib/**/*,frontend/**/hooks/**/*,frontend/**/services/**/*"
---

# Backend Integration Patterns for Frontend

Standard patterns for integrating frontend with AWS backend services.

## API Architecture

**Lambda Function URLs** (primary method): No API Gateway required; built-in HTTPS; streaming support for SSE; simplified CORS; direct Lambda invocation.

```typescript
const response = await fetch(process.env.NEXT_PUBLIC_API_URL, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});
```

**Standard payload**: Always include `session_id` for stateful interactions; use snake_case for backend compatibility; include user context when available; enable streaming with `stream: true`.

```typescript
interface RequestPayload {
  query?: string; prompt?: string; inputs?: Array<{ text?: string; image?: unknown }>;
  session_id: string; userId?: string; email?: string; user_location?: string;
  stream?: boolean;
}
```

## Streaming (SSE)

**Standard SSE client**: Accept `text/event-stream`; use ReadableStream reader; decode with TextDecoder; split on `\n\n`; parse `data:` prefix.

```typescript
export async function streamResponse(payload: RequestPayload, onChunk: (event: StreamEvent) => void, onError: (error: Error) => void, onComplete: () => void) {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
    body: JSON.stringify(payload)
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) { onComplete(); break; }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.substring(6));
        onChunk(data);
      }
    }
  }
}
```

**Event types**: `thinking`/`reasoning-delta` (agent reasoning → collapsible block), `text-delta`/`response`/`content` (incremental text → append), `tool-input-available` (tool start → loading), `tool-output-available` (tool results → parse/display), `sources`/`citations` (references → citation list), `final_result`/`finish` (completion → end streaming), `error` (error → show message).

```typescript
const handleStreamEvent = (event: StreamEvent) => {
  switch (event.type) {
    case 'thinking': case 'reasoning-delta': updateThinkingBlock(event.data); break;
    case 'text-delta': case 'content': appendToMessage(event.data); break;
    case 'tool-output-available': processToolOutput(event.toolName, event.output); break;
    case 'finish': completeMessage(); break;
    case 'error': handleError(event.error); break;
  }
};
```

**Lambda response unwrapping**: Lambda may wrap SSE chunks in JSON strings; try parsing and unwrap if string.

```typescript
let chunk = decoder.decode(value, { stream: true });
try {
  const unwrapped = JSON.parse(chunk);
  if (typeof unwrapped === 'string') chunk = unwrapped;
} catch {}
```

## Session Management

**Session ID format** (AWS AgentCore compatible): Minimum 33 characters; format `session_<timestamp>_<random><random>`.

```typescript
function generateSessionId(): string {
  const timestamp = Date.now().toString(36);
  const random1 = Math.random().toString(36).substring(2, 15);
  const random2 = Math.random().toString(36).substring(2, 15);
  let sessionId = `session_${timestamp}_${random1}${random2}`;
  while (sessionId.length < 33) sessionId += Math.random().toString(36).substring(2, 1);
  return sessionId;
}
```

**Storage strategies**: SessionStorage (recommended for chat apps; cleared on tab close), per-page-load (new session each refresh with `useMemo`), localStorage (persistent across sessions).

```typescript
const SESSION_KEY = 'app_session_id';
export function getOrCreateSessionId(): string {
  let sessionId = sessionStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = generateSessionId();
    sessionStorage.setItem(SESSION_KEY, sessionId);
  }
  return sessionId;
}
```

## AWS Service Integration

**S3 uploads**: Use Cognito Identity Pool for credentials; `@aws-sdk/client-s3` with `PutObjectCommand`.

```typescript
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { fromCognitoIdentityPool } from '@aws-sdk/credential-provider-cognito-identity';
import { CognitoIdentityClient } from '@aws-sdk/client-cognito-identity';

const s3Client = new S3Client({
  region: AWS_REGION,
  credentials: fromCognitoIdentityPool({
    client: new CognitoIdentityClient({ region: AWS_REGION }),
    identityPoolId: COGNITO_IDENTITY_POOL_ID
  })
});

export async function uploadFile(file: File, key: string) {
  await s3Client.send(new PutObjectCommand({
    Bucket: BUCKET_NAME, Key: key, Body: file, ContentType: file.type
  }));
  return key;
}
```

**Bedrock Agent Runtime**: Use `@aws-sdk/client-bedrock-agent-runtime` with `InvokeAgentCommand`.

```typescript
import { BedrockAgentRuntimeClient, InvokeAgentCommand } from '@aws-sdk/client-bedrock-agent-runtime';

const client = new BedrockAgentRuntimeClient({ region: AWS_REGION, credentials: /* ... */ });

export async function invokeAgent(prompt: string, sessionId: string) {
  return await client.send(new InvokeAgentCommand({
    agentId: AGENT_ID, agentAliasId: AGENT_ALIAS_ID, sessionId, inputText: prompt
  }));
}
```

## Error Handling

**Comprehensive pattern**: Use AbortController for timeout (30s); parse error responses; map network/timeout/HTTP errors to user-friendly messages.

```typescript
async function apiCall(endpoint: string, payload: any) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `HTTP error! status: ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {}
      throw new Error(errorMessage);
    }

    return response;
  } catch (error) {
    if (error instanceof Error) {
      if (error.name === 'AbortError') throw new Error('Request timed out. Please try again.');
      if (error.message.includes('Failed to fetch')) throw new Error('Network error. Please check your connection.');
    }
    throw error;
  }
}
```

**User-friendly messages**: Timeout → "Request timed out. Server may be busy"; Network → "Network connection failed. Check internet"; 5xx → "Server error. Try again in a few minutes"; 4xx → "Request error. Check input".

## Data Processing

**JSON parsing from streaming**: Extract JSON array from text with regex; handle embedded JSON in responses.

```typescript
function parseJobResults(jobAgentResult: string): Job[] {
  let cleanResult = jobAgentResult.trim();
  const jsonMatch = cleanResult.match(/(\[[\s\S]*?\])/);
  if (jsonMatch) cleanResult = jsonMatch[1];
  try {
    return JSON.parse(cleanResult);
  } catch (error) {
    console.error('Failed to parse job results:', error);
    throw new Error('Unable to process results');
  }
}
```

**Tool output processing**: Handle string output (parse JSON), array output (find text field and parse), extract structured data.

```typescript
function processToolOutput(toolName: string, output: unknown) {
  let outputData: unknown = output;
  if (typeof output === 'string') outputData = JSON.parse(output);
  if (Array.isArray(output)) {
    const textContent = output.find(item => typeof item === 'object' && item !== null && 'text' in item);
    if (textContent) outputData = JSON.parse(textContent.text);
  }
  return outputData.resources_by_category;
}
```

## Retry and Resilience

**Automatic retry**: Retry on 5xx errors with exponential backoff (1s, 2s, 4s); don't retry 4xx client errors; max 3 attempts.

```typescript
async function fetchWithRetry(url: string, options: RequestInit, maxRetries: number = 3): Promise<Response> {
  let lastError: Error;
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      if (response.ok) return response;
      if (response.status >= 400 && response.status < 500) throw new Error(`Client error: ${response.status}`);
      lastError = new Error(`Server error: ${response.status}`);
    } catch (error) {
      lastError = error as Error;
      if (lastError.message.includes('Client error')) throw lastError;
    }
    if (i < maxRetries - 1) await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
  }
  throw lastError!;
}
```

**User-initiated retry**: Allow users to retry failed messages; find previous user message and resend.

```typescript
const retryMessage = (messageId: string) => {
  const errorIndex = messages.findIndex(m => m.id === messageId);
  if (errorIndex > 0) {
    const userMessage = messages[errorIndex - 1];
    if (userMessage.role === 'user') {
      setMessages(prev => prev.filter(m => m.id !== messageId));
      sendMessage(userMessage.content);
    }
  }
};
```

## Performance

**Request debouncing**: Prevent duplicate requests with timeout-based debounce.

```typescript
import { useCallback, useRef } from 'react';

function useDebounce<T extends (...args: any[]) => any>(callback: T, delay: number): T {
  const timeoutRef = useRef<NodeJS.Timeout>();
  return useCallback((...args: Parameters<T>) => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => callback(...args), delay);
  }, [callback, delay]) as T;
}
```

**Response caching**: Cache API responses with TTL (5 min); check timestamp before returning cached data.

```typescript
const responseCache = new Map<string, { data: any; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000;

async function fetchWithCache(key: string, fetcher: () => Promise<any>) {
  const cached = responseCache.get(key);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) return cached.data;
  const data = await fetcher();
  responseCache.set(key, { data, timestamp: Date.now() });
  return data;
}
```

## Multi-language Support

**Backend translation pattern**: Send user input as-is (don't translate client-side); include optional `user_language` hint; backend handles detection, translation to English, processing, translation back to user language; frontend displays translated responses and handles RTL languages (Arabic, Hebrew).

```typescript
interface TranslatedRequest {
  query: string; session_id: string; user_language?: string;
}
```

## Export and Download

**PDF export**: POST session_id to export endpoint; receive base64 PDF; convert to Blob; trigger download.

```typescript
async function exportToPDF(sessionId: string) {
  const response = await fetch(EXPORT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId })
  });
  const data = await response.json();
  const blob = base64ToBlob(data.pdf, 'application/pdf');
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = `resources-${sessionId}.pdf`; link.click();
  URL.revokeObjectURL(url);
}

function base64ToBlob(base64: string, mimeType: string): Blob {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) byteNumbers[i] = byteCharacters.charCodeAt(i);
  return new Blob([new Uint8Array(byteNumbers)], { type: mimeType });
}
```

## Testing

**Mock API responses**: Create mock handlers with jest.fn(); implement test behavior.

```typescript
// __mocks__/apiService.ts
export const mockStreamResponse = jest.fn();

// In tests
import { mockStreamResponse } from '@/__mocks__/apiService';
mockStreamResponse.mockImplementation((payload, onChunk) => {
  onChunk({ type: 'text-delta', data: 'Hello' });
  onChunk({ type: 'finish' });
});
```

**Integration tests**: Test streaming flows; verify chunks received; check completion.

```typescript
describe('Chat API Integration', () => {
  it('should handle streaming response', async () => {
    const chunks: string[] = [];
    await streamResponse(
      { query: 'test', session_id: 'test-123' },
      (event) => { if (event.type === 'text-delta') chunks.push(event.data); },
      (error) => fail(error), () => {}
    );
    expect(chunks.length).toBeGreaterThan(0);
  });
});
```

## Security

**CORS**: Lambda Function URLs must have proper CORS config (allowOrigins, allowMethods, allowHeaders, maxAge).

**Input sanitization**: Trim, remove HTML tags, limit length before sending.

```typescript
function sanitizeInput(input: string): string {
  return input.trim().replace(/[<>]/g, '').substring(0, 10000);
}
```

**Credential management**: Use Cognito Identity Pool for AWS SDK; use Lambda Function URLs for API access; store sensitive config in environment variables; validate at build time; never expose credentials in frontend.

## Monitoring and Logging

**Structured logging**: Implement info/error/debug levels; send errors to monitoring service if configured.

```typescript
const logger = {
  info: (message: string, data?: any) => console.log(`[INFO] ${message}`, data),
  error: (message: string, error?: Error) => {
    console.error(`[ERROR] ${message}`, error);
    // Send to monitoring service if configured
  },
  debug: (message: string, data?: any) => {
    if (process.env.NODE_ENV === 'development') console.debug(`[DEBUG] ${message}`, data);
  }
};
```

**Performance tracking**: Track API call duration; log completion/failure with metrics.

```typescript
async function trackedFetch(url: string, options: RequestInit) {
  const startTime = performance.now();
  try {
    const response = await fetch(url, options);
    const duration = performance.now() - startTime;
    logger.info('API call completed', { url, duration, status: response.status });
    return response;
  } catch (error) {
    const duration = performance.now() - startTime;
    logger.error('API call failed', { url, duration, error });
    throw error;
  }
}
```
