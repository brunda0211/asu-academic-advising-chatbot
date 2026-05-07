import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import QuestionnairePage from '@/app/page';

// Mock next/navigation
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: jest.fn(),
  }),
}));

// Mock ChatContext
const mockSetQuestionnaireData = jest.fn();
jest.mock('@/contexts/ChatContext', () => ({
  useChatContext: () => ({
    sessionId: 'session_test123456789012345678901',
    questionnaireData: null,
    setQuestionnaireData: mockSetQuestionnaireData,
  }),
}));

describe('QuestionnaireForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 42.1 Test form renders all required fields (academic year, major, advising topic)
  it('renders all required fields', () => {
    render(<QuestionnairePage />);

    expect(screen.getByLabelText(/academic year/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/major/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/advising topic/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start chat/i })).toBeInTheDocument();
  });

  // 42.2 Test form validation prevents submission with empty fields
  it('prevents submission with empty fields and shows validation errors', async () => {
    render(<QuestionnairePage />);

    const submitButton = screen.getByRole('button', { name: /start chat/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/academic year is required/i)).toBeInTheDocument();
      expect(screen.getByText(/major is required/i)).toBeInTheDocument();
      expect(screen.getByText(/advising topic is required/i)).toBeInTheDocument();
    });

    expect(mockPush).not.toHaveBeenCalled();
    expect(mockSetQuestionnaireData).not.toHaveBeenCalled();
  });

  // 42.3 Test successful submission saves data to sessionStorage and navigates to /chat
  it('saves data and navigates to /chat on successful submission', async () => {
    const user = userEvent.setup();
    render(<QuestionnairePage />);

    // Fill in the form
    await user.selectOptions(screen.getByLabelText(/academic year/i), 'Junior');
    await user.type(screen.getByLabelText(/major/i), 'Computer Science');
    await user.selectOptions(screen.getByLabelText(/advising topic/i), 'Course Planning');

    // Submit
    await user.click(screen.getByRole('button', { name: /start chat/i }));

    expect(mockSetQuestionnaireData).toHaveBeenCalledWith({
      academic_year: 'Junior',
      major: 'Computer Science',
      advising_topic: 'Course Planning',
    });
    expect(mockPush).toHaveBeenCalledWith('/chat');
  });

  // 42.4 Test all form fields have associated labels and ARIA attributes
  it('has proper labels and ARIA attributes for accessibility', () => {
    render(<QuestionnairePage />);

    const academicYear = screen.getByLabelText(/academic year/i);
    const major = screen.getByLabelText(/major/i);
    const advisingTopic = screen.getByLabelText(/advising topic/i);

    // All fields should have aria-required
    expect(academicYear).toHaveAttribute('aria-required', 'true');
    expect(major).toHaveAttribute('aria-required', 'true');
    expect(advisingTopic).toHaveAttribute('aria-required', 'true');

    // Fields should have proper IDs matching labels
    expect(academicYear).toHaveAttribute('id', 'academic-year');
    expect(major).toHaveAttribute('id', 'major');
    expect(advisingTopic).toHaveAttribute('id', 'advising-topic');
  });

  it('shows aria-invalid on fields after failed submission', async () => {
    render(<QuestionnairePage />);

    fireEvent.click(screen.getByRole('button', { name: /start chat/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/academic year/i)).toHaveAttribute(
        'aria-invalid',
        'true'
      );
      expect(screen.getByLabelText(/major/i)).toHaveAttribute(
        'aria-invalid',
        'true'
      );
      expect(screen.getByLabelText(/advising topic/i)).toHaveAttribute(
        'aria-invalid',
        'true'
      );
    });
  });
});
