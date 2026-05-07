'use client';

import { useState, useRef, useEffect, useCallback, type KeyboardEvent } from 'react';
import type { ChatMessage } from '@/hooks/useChat';
import MessageBubble from './MessageBubble';

interface ChatInterfaceProps {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  onSendMessage: (text: string) => void;
  onClearError: () => void;
  onRetry: () => void;
}

export default function ChatInterface({
  messages,
  isLoading,
  error,
  onSendMessage,
  onClearError,
  onRetry,
}: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom on new messages or streaming content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSendMessage(trimmed);
    setInput('');
  }, [input, isLoading, onSendMessage]);

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const isStreamInterruption =
    error?.toLowerCase().includes('interrupted') ||
    error?.toLowerCase().includes('aborted');

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Message list */}
      <div
        role="log"
        aria-live="polite"
        aria-busy={isLoading}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-4"
      >
        {messages.length === 0 && !isLoading && (
          <p className="text-center text-gray-400 text-sm mt-8">
            Ask a question about academic advising to get started.
          </p>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Loading indicator */}
        {isLoading && messages[messages.length - 1]?.content === '' && (
          <div className="flex items-center gap-1 px-4 py-2" aria-label="Assistant is typing">
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error display (Task 30) */}
      {error && (
        <div
          role="alert"
          className="mx-4 mb-2 rounded-md border border-red-200 bg-red-50 px-4 py-3 flex items-center justify-between gap-2"
        >
          <p className="text-sm text-red-700">
            {isStreamInterruption
              ? 'Response was interrupted. Try again.'
              : error}
          </p>
          <div className="flex gap-2 shrink-0">
            <button
              onClick={onRetry}
              className="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-400"
            >
              Retry
            </button>
            <button
              onClick={onClearError}
              className="rounded border border-red-300 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-400"
              aria-label="Dismiss error"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="shrink-0 border-t border-gray-200 bg-white px-4 py-3">
        <div className="flex gap-2 max-w-3xl mx-auto">
          <label htmlFor="chat-input" className="sr-only">
            Type your message
          </label>
          <input
            ref={inputRef}
            id="chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your question..."
            disabled={isLoading}
            aria-label="Chat message input"
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#8C1D40] disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            aria-label="Send message"
            className="rounded-md bg-[#8C1D40] px-4 py-2 text-sm font-medium text-white hover:bg-[#6b1631] focus:outline-none focus:ring-2 focus:ring-[#FFC627] focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
