'use client';

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import {
  getOrCreateSessionId,
  getQuestionnaireData,
  setQuestionnaireData as persistQuestionnaireData,
  type QuestionnaireData,
} from '@/lib/session';

interface ChatContextValue {
  sessionId: string;
  questionnaireData: QuestionnaireData | null;
  setQuestionnaireData: (data: QuestionnaireData) => void;
}

const ChatContext = createContext<ChatContextValue | undefined>(undefined);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string>('');
  const [questionnaireData, setQuestionnaireState] =
    useState<QuestionnaireData | null>(null);

  // Initialize session ID and load questionnaire data on mount
  useEffect(() => {
    setSessionId(getOrCreateSessionId());
    setQuestionnaireState(getQuestionnaireData());
  }, []);

  const setQuestionnaireData = useCallback((data: QuestionnaireData) => {
    persistQuestionnaireData(data);
    setQuestionnaireState(data);
  }, []);

  return (
    <ChatContext.Provider
      value={{ sessionId, questionnaireData, setQuestionnaireData }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
}
