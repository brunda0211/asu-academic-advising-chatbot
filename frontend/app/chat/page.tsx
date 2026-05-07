'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useChatContext } from '@/contexts/ChatContext';
import { useChat } from '@/hooks/useChat';
import ChatInterface from '@/components/ChatInterface';

export default function ChatPage() {
  const router = useRouter();
  const { sessionId, questionnaireData } = useChatContext();
  const [ready, setReady] = useState(false);

  // ADR: Gate on questionnaireData presence | P33 requires redirect if missing
  useEffect(() => {
    if (!questionnaireData) {
      router.replace('/');
    } else {
      setReady(true);
    }
  }, [questionnaireData, router]);

  const { messages, isLoading, error, sendMessage, clearError, retry } =
    useChat({ sessionId, questionnaireData });

  if (!ready) {
    return null;
  }

  return (
    <main className="h-screen flex flex-col bg-gray-50">
      <header className="shrink-0 bg-[#8C1D40] px-4 py-3 text-white shadow-sm">
        <h1 className="text-lg font-semibold">GUIDE</h1>
        <p className="text-xs text-white/80">
          {questionnaireData?.major} &middot; {questionnaireData?.advising_topic}
        </p>
      </header>

      <ChatInterface
        messages={messages}
        isLoading={isLoading}
        error={error}
        onSendMessage={sendMessage}
        onClearError={clearError}
        onRetry={retry}
      />
    </main>
  );
}
