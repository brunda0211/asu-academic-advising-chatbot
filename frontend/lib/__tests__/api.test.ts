// Set env before importing the module
const MOCK_API_URL = 'https://api.example.com/chat';
process.env.NEXT_PUBLIC_API_URL = MOCK_API_URL;

import { sendChatMessage, parseSSEStream, ChatError } from '../api';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  // 40.1 Test sendChatMessage() sends correct request body format
  describe('sendChatMessage()', () => {
    it('sends correct request body format', async () => {
      jest.useRealTimers();

      const mockReader = {
        read: jest.fn().mockResolvedValue({ done: true, value: undefined }),
        releaseLock: jest.fn(),
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: { getReader: () => mockReader },
      });

      const context = {
        academic_year: 'Junior' as const,
        major: 'Computer Science',
        advising_topic: 'Course Planning' as const,
      };

      await sendChatMessage('Hello', 'session_abc123456789012345678901', context);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe(MOCK_API_URL);
      expect(options.method).toBe('POST');
      expect(options.headers).toEqual({ 'Content-Type': 'application/json' });
      expect(JSON.parse(options.body)).toEqual({
        message: 'Hello',
        session_id: 'session_abc123456789012345678901',
        context: {
          academic_year: 'Junior',
          major: 'Computer Science',
          advising_topic: 'Course Planning',
        },
      });
      expect(options.signal).toBeDefined();
    });

    // 40.3 Test AbortController timeout triggers after 30 seconds
    it('throws timeout error after 30 seconds', async () => {
      mockFetch.mockImplementation(
        (_url: string, options: { signal: AbortSignal }) => {
          return new Promise((_resolve, reject) => {
            options.signal.addEventListener('abort', () => {
              const error = new Error('The operation was aborted.');
              error.name = 'AbortError';
              reject(error);
            });
          });
        }
      );

      const context = {
        academic_year: 'Junior' as const,
        major: 'Computer Science',
        advising_topic: 'Course Planning' as const,
      };

      const promise = sendChatMessage(
        'Hello',
        'session_abc123456789012345678901',
        context
      );

      jest.advanceTimersByTime(30000);

      await expect(promise).rejects.toThrow('Request timed out');
    });

    // 40.4 Test retry logic with exponential backoff on 5xx errors (max 3 attempts)
    it('retries on 5xx errors with exponential backoff (max 3 attempts)', async () => {
      jest.useRealTimers();

      // Use real timers but mock setTimeout to track backoff delays
      const delays: number[] = [];
      const originalSetTimeout = global.setTimeout;
      jest.spyOn(global, 'setTimeout').mockImplementation((fn: any, delay?: number) => {
        if (delay && delay >= 1000) {
          delays.push(delay);
        }
        // Execute immediately for test speed
        if (typeof fn === 'function') fn();
        return 0 as unknown as ReturnType<typeof setTimeout>;
      });

      mockFetch
        .mockResolvedValueOnce({ ok: false, status: 500 })
        .mockResolvedValueOnce({ ok: false, status: 503 })
        .mockResolvedValueOnce({ ok: false, status: 502 });

      const context = {
        academic_year: 'Junior' as const,
        major: 'Computer Science',
        advising_topic: 'Course Planning' as const,
      };

      await expect(
        sendChatMessage('Hello', 'session_abc123456789012345678901', context)
      ).rejects.toThrow(/Server error/);

      expect(mockFetch).toHaveBeenCalledTimes(3);
      // Verify exponential backoff delays: 1000ms, 2000ms
      expect(delays).toContain(1000);
      expect(delays).toContain(2000);

      jest.restoreAllMocks();
    });

    // 40.5 Test no retry on 4xx errors
    it('does not retry on 4xx errors', async () => {
      jest.useRealTimers();

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: 'Bad request' }),
      });

      const context = {
        academic_year: 'Junior' as const,
        major: 'Computer Science',
        advising_topic: 'Course Planning' as const,
      };

      await expect(
        sendChatMessage('Hello', 'session_abc123456789012345678901', context)
      ).rejects.toThrow('Bad request');

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  // 40.2 Test parseSSEStream() correctly parses text-delta, citations, and finish events
  describe('parseSSEStream()', () => {
    it('correctly parses text-delta events', async () => {
      jest.useRealTimers();
      const events: any[] = [];
      const chunks = [
        new TextEncoder().encode(
          'data: {"type":"text-delta","content":"Hello"}\n\ndata: {"type":"text-delta","content":" world"}\n\n'
        ),
      ];

      const mockReader = {
        read: jest
          .fn()
          .mockResolvedValueOnce({ done: false, value: chunks[0] })
          .mockResolvedValueOnce({ done: true, value: undefined }),
        releaseLock: jest.fn(),
      } as unknown as ReadableStreamDefaultReader<Uint8Array>;

      await parseSSEStream(mockReader, (event) => events.push(event));

      expect(events).toHaveLength(2);
      expect(events[0]).toEqual({ type: 'text-delta', content: 'Hello' });
      expect(events[1]).toEqual({ type: 'text-delta', content: ' world' });
    });

    it('correctly parses citations events', async () => {
      jest.useRealTimers();
      const events: any[] = [];
      const chunk = new TextEncoder().encode(
        'data: {"type":"citations","sources":["s3://bucket/doc1.pdf","s3://bucket/doc2.pdf"]}\n\n'
      );

      const mockReader = {
        read: jest
          .fn()
          .mockResolvedValueOnce({ done: false, value: chunk })
          .mockResolvedValueOnce({ done: true, value: undefined }),
        releaseLock: jest.fn(),
      } as unknown as ReadableStreamDefaultReader<Uint8Array>;

      await parseSSEStream(mockReader, (event) => events.push(event));

      expect(events).toHaveLength(1);
      expect(events[0]).toEqual({
        type: 'citations',
        sources: ['s3://bucket/doc1.pdf', 's3://bucket/doc2.pdf'],
      });
    });

    it('correctly parses finish events', async () => {
      jest.useRealTimers();
      const events: any[] = [];
      const chunk = new TextEncoder().encode(
        'data: {"type":"finish","usage":{"input_tokens":100,"output_tokens":50}}\n\n'
      );

      const mockReader = {
        read: jest
          .fn()
          .mockResolvedValueOnce({ done: false, value: chunk })
          .mockResolvedValueOnce({ done: true, value: undefined }),
        releaseLock: jest.fn(),
      } as unknown as ReadableStreamDefaultReader<Uint8Array>;

      await parseSSEStream(mockReader, (event) => events.push(event));

      expect(events).toHaveLength(1);
      expect(events[0]).toEqual({
        type: 'finish',
        usage: { input_tokens: 100, output_tokens: 50 },
      });
    });

    it('handles chunked data split across reads', async () => {
      jest.useRealTimers();
      const events: any[] = [];
      const chunk1 = new TextEncoder().encode('data: {"type":"text-del');
      const chunk2 = new TextEncoder().encode('ta","content":"Hi"}\n\n');

      const mockReader = {
        read: jest
          .fn()
          .mockResolvedValueOnce({ done: false, value: chunk1 })
          .mockResolvedValueOnce({ done: false, value: chunk2 })
          .mockResolvedValueOnce({ done: true, value: undefined }),
        releaseLock: jest.fn(),
      } as unknown as ReadableStreamDefaultReader<Uint8Array>;

      await parseSSEStream(mockReader, (event) => events.push(event));

      expect(events).toHaveLength(1);
      expect(events[0]).toEqual({ type: 'text-delta', content: 'Hi' });
    });
  });
});
