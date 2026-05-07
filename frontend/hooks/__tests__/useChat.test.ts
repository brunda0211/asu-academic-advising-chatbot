import { renderHook, act, waitFor } from '@testing-library/react';
import { useChat } from '../useChat';

// Mock the API module
jest.mock('@/lib/api', () => ({
  sendChatMessage: jest.fn(),
  parseSSEStream: jest.fn(),
}));

import { sendChatMessage, parseSSEStream } from '@/lib/api';

const mockSendChatMessage = sendChatMessage as jest.MockedFunction<typeof sendChatMessage>;
const mockParseSSEStream = parseSSEStream as jest.MockedFunction<typeof parseSSEStream>;

const defaultOptions = {
  sessionId: 'session_test123456789012345678901',
  questionnaireData: {
    academic_year: 'Junior' as const,
    major: 'Computer Science',
    advising_topic: 'Course Planning' as const,
  },
};

describe('useChat hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 41.1 Test sendMessage adds user message and streams assistant response
  it('sendMessage adds user message and streams assistant response', async () => {
    const mockReader = {} as ReadableStreamDefaultReader<Uint8Array>;
    mockSendChatMessage.mockResolvedValue(mockReader);
    mockParseSSEStream.mockImplementation(async (_reader, onEvent) => {
      onEvent({ type: 'text-delta', content: 'Hello' });
      onEvent({ type: 'text-delta', content: ' there' });
      onEvent({ type: 'finish', usage: { input_tokens: 10, output_tokens: 5 } });
    });

    const { result } = renderHook(() => useChat(defaultOptions));

    await act(async () => {
      await result.current.sendMessage('Hi');
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].role).toBe('user');
    expect(result.current.messages[0].content).toBe('Hi');
    expect(result.current.messages[1].role).toBe('assistant');
    expect(result.current.messages[1].content).toBe('Hello there');
  });

  // 41.2 Test isLoading is true during request and false after completion
  it('isLoading is true during request and false after completion', async () => {
    let resolveStream: () => void;
    const streamPromise = new Promise<void>((resolve) => {
      resolveStream = resolve;
    });

    const mockReader = {} as ReadableStreamDefaultReader<Uint8Array>;
    mockSendChatMessage.mockResolvedValue(mockReader);
    mockParseSSEStream.mockImplementation(async () => {
      await streamPromise;
    });

    const { result } = renderHook(() => useChat(defaultOptions));

    let sendPromise: Promise<void>;
    act(() => {
      sendPromise = result.current.sendMessage('Hi');
    });

    // isLoading should be true during the request
    await waitFor(() => {
      expect(result.current.isLoading).toBe(true);
    });

    // Complete the stream
    await act(async () => {
      resolveStream!();
      await sendPromise!;
    });

    expect(result.current.isLoading).toBe(false);
  });

  // 41.3 Test error state is set on failed request
  it('error state is set on failed request', async () => {
    mockSendChatMessage.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useChat(defaultOptions));

    await act(async () => {
      await result.current.sendMessage('Hi');
    });

    expect(result.current.error).toBe('Network error');
  });

  // 41.4 Test retry function re-sends last failed message
  it('retry function re-sends last failed message', async () => {
    // First call fails
    mockSendChatMessage.mockRejectedValueOnce(new Error('Server error'));

    const { result } = renderHook(() => useChat(defaultOptions));

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    expect(result.current.error).toBe('Server error');

    // Setup success for retry
    const mockReader = {} as ReadableStreamDefaultReader<Uint8Array>;
    mockSendChatMessage.mockResolvedValue(mockReader);
    mockParseSSEStream.mockImplementation(async (_reader, onEvent) => {
      onEvent({ type: 'text-delta', content: 'Response' });
      onEvent({ type: 'finish', usage: { input_tokens: 10, output_tokens: 5 } });
    });

    await act(async () => {
      result.current.retry();
    });

    // Wait for the retry to complete
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(mockSendChatMessage).toHaveBeenCalledTimes(2);
  });

  // 41.5 Test HTML tag stripping on user input
  it('strips HTML tags from user input', async () => {
    const mockReader = {} as ReadableStreamDefaultReader<Uint8Array>;
    mockSendChatMessage.mockResolvedValue(mockReader);
    mockParseSSEStream.mockImplementation(async (_reader, onEvent) => {
      onEvent({ type: 'finish', usage: { input_tokens: 10, output_tokens: 5 } });
    });

    const { result } = renderHook(() => useChat(defaultOptions));

    await act(async () => {
      await result.current.sendMessage('<script>alert("xss")</script>Hello');
    });

    // The user message should have HTML stripped
    expect(result.current.messages[0].content).toBe('alert("xss")Hello');
    // The API should receive sanitized input
    expect(mockSendChatMessage).toHaveBeenCalledWith(
      'alert("xss")Hello',
      expect.any(String),
      expect.any(Object),
      expect.any(Object)
    );
  });

  // 41.6 Test cleanup on unmount (AbortController abort)
  it('aborts request on unmount', async () => {
    let resolveStream: () => void;
    const streamPromise = new Promise<void>((resolve) => {
      resolveStream = resolve;
    });

    const mockReader = {} as ReadableStreamDefaultReader<Uint8Array>;
    mockSendChatMessage.mockResolvedValue(mockReader);
    mockParseSSEStream.mockImplementation(async () => {
      await streamPromise;
    });

    const { result, unmount } = renderHook(() => useChat(defaultOptions));

    // Start a message (don't await)
    act(() => {
      result.current.sendMessage('Hi');
    });

    // Verify the AbortController signal was passed
    await waitFor(() => {
      expect(mockSendChatMessage).toHaveBeenCalled();
    });

    const signal = mockSendChatMessage.mock.calls[0][3] as AbortSignal;
    expect(signal.aborted).toBe(false);

    // Unmount should trigger abort
    unmount();
    expect(signal.aborted).toBe(true);

    // Cleanup
    resolveStream!();
  });

  it('does not send message when sessionId is empty', async () => {
    const { result } = renderHook(() =>
      useChat({ sessionId: '', questionnaireData: defaultOptions.questionnaireData })
    );

    await act(async () => {
      await result.current.sendMessage('Hi');
    });

    expect(mockSendChatMessage).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(0);
  });

  it('does not send empty messages', async () => {
    const { result } = renderHook(() => useChat(defaultOptions));

    await act(async () => {
      await result.current.sendMessage('   ');
    });

    expect(mockSendChatMessage).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(0);
  });
});
