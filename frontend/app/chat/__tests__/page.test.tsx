import { render, screen } from '@testing-library/react';
import ChatPage from '../page';

// Mock next/navigation
const mockReplace = jest.fn();
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
  }),
}));

// Mock useChat hook
jest.mock('@/hooks/useChat', () => ({
  useChat: () => ({
    messages: [],
    isLoading: false,
    error: null,
    sendMessage: jest.fn(),
    clearError: jest.fn(),
    retry: jest.fn(),
  }),
}));

// Variable to control questionnaire data in tests
let mockQuestionnaireData: any = null;

jest.mock('@/contexts/ChatContext', () => ({
  useChatContext: () => ({
    sessionId: 'session_test123456789012345678901',
    questionnaireData: mockQuestionnaireData,
    setQuestionnaireData: jest.fn(),
  }),
}));

describe('Chat Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockQuestionnaireData = null;
  });

  // 44.1 Test redirect to / when sessionStorage has no questionnaire data
  it('redirects to / when no questionnaire data is present', () => {
    mockQuestionnaireData = null;

    render(<ChatPage />);

    expect(mockReplace).toHaveBeenCalledWith('/');
  });

  // 44.2 Test page renders ChatInterface when questionnaire data is present
  it('renders ChatInterface when questionnaire data is present', () => {
    mockQuestionnaireData = {
      academic_year: 'Junior',
      major: 'Computer Science',
      advising_topic: 'Course Planning',
    };

    render(<ChatPage />);

    expect(mockReplace).not.toHaveBeenCalled();
    // ChatInterface renders the message log area
    expect(screen.getByRole('log')).toBeInTheDocument();
    // Header should show major and topic
    expect(screen.getByText(/computer science/i)).toBeInTheDocument();
    expect(screen.getByText(/course planning/i)).toBeInTheDocument();
  });
});
