'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { sendChatMessage, parseSSEStream } from '@/lib/api';
import type { SSEEvent } from '@/lib/api';
import type { QuestionnaireData } from '@/lib/session';

// ADR: Strip HTML via regex per P37 | prevents XSS in user input before sending to API
function sanitizeInput(input: string): string {
  return input.replace(/<[^>]*>/g, '');
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: string[];
}

interface UseChatOptions {
  sessionId: string;
  questionnaireData: QuestionnaireData | null;
}

export function useChat({ sessionId, questionnaireData }: UseChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastUserMessageRef = useRef<string | null>(null);

  // Cleanup AbortController on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!questionnaireData || !sessionId) return;

      const sanitized = sanitizeInput(text).trim();
      if (!sanitized) return;

      // Store for retry
      lastUserMessageRef.current = sanitized;

      // Clear any previous error
      setError(null);

      // Add user message
      const userMessage: ChatMessage = {
        id: `msg_${Date.now()}_user`,
        role: 'user',
        content: sanitized,
      };

      // Add placeholder assistant message for streaming
      const assistantMessageId = `msg_${Date.now()}_assistant`;
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsLoading(true);

      // Create AbortController for this request
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const reader = await sendChatMessage(
          sanitized,
          sessionId,
          {
            academic_year: questionnaireData.academic_year,
            major: questionnaireData.major,
            advising_topic: questionnaireData.advising_topic,
          },
          controller.signal
        );

        await parseSSEStream(reader, (event: SSEEvent) => {
          switch (event.type) {
            case 'text-delta':
              // P34: Incremental text append
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, content: msg.content + event.content }
                    : msg
                )
              );
              break;
            case 'citations':
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, citations: event.sources }
                    : msg
                )
              );
              break;
            case 'finish':
              // Stream complete
              break;
            case 'error':
              setError(event.message);
              break;
          }
        });
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'An unexpected error occurred.';
        setError(errorMessage);
        // Remove the empty assistant message on failure
        setMessages((prev) =>
          prev.filter(
            (msg) =>
              !(msg.id === assistantMessageId && msg.content === '')
          )
        );
      } finally {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    },
    [sessionId, questionnaireData]
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const retry = useCallback(() => {
    if (lastUserMessageRef.current) {
      // Remove the last user message and any failed assistant message
      setMessages((prev) => {
        const lastUserIndex = prev.findLastIndex(
          (msg) => msg.role === 'user'
        );
        if (lastUserIndex === -1) return prev;
        return prev.slice(0, lastUserIndex);
      });
      sendMessage(lastUserMessageRef.current);
    }
  }, [sendMessage]);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearError,
    retry,
  };
}
