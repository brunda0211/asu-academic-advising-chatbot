import { render, screen, fireEvent } from '@testing-library/react';
import ChatInterface from '../ChatInterface';
import type { ChatMessage } from '@/hooks/useChat';

const mockOnSendMessage = jest.fn();
const mockOnClearError = jest.fn();
const mockOnRetry = jest.fn();

const defaultProps = {
  messages: [] as ChatMessage[],
  isLoading: false,
  error: null as string | null,
  onSendMessage: mockOnSendMessage,
  onClearError: mockOnClearError,
  onRetry: mockOnRetry,
};

describe('ChatInterface', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 43.1 Test message list renders user and assistant messages
  it('renders user and assistant messages', () => {
    const messages: ChatMessage[] = [
      { id: 'msg_1', role: 'user', content: 'Hello there' },
      { id: 'msg_2', role: 'assistant', content: 'Hi! How can I help?' },
    ];

    render(<ChatInterface {...defaultProps} messages={messages} />);

    expect(screen.getByText('Hello there')).toBeInTheDocument();
    expect(screen.getByText('Hi! How can I help?')).toBeInTheDocument();
  });

  // 43.2 Test send button is disabled during loading
  it('disables send button during loading', () => {
    render(<ChatInterface {...defaultProps} isLoading={true} />);

    const sendButton = screen.getByRole('button', { name: /send message/i });
    expect(sendButton).toBeDisabled();
  });

  it('disables send button when input is empty', () => {
    render(<ChatInterface {...defaultProps} />);

    const sendButton = screen.getByRole('button', { name: /send message/i });
    expect(sendButton).toBeDisabled();
  });

  it('enables send button when input has text and not loading', () => {
    render(<ChatInterface {...defaultProps} />);

    const input = screen.getByLabelText(/chat message input/i);
    fireEvent.change(input, { target: { value: 'Hello' } });

    const sendButton = screen.getByRole('button', { name: /send message/i });
    expect(sendButton).not.toBeDisabled();
  });

  // 43.3 Test loading indicator appears during pending request
  it('shows loading indicator during pending request', () => {
    const messages: ChatMessage[] = [
      { id: 'msg_1', role: 'user', content: 'Hello' },
      { id: 'msg_2', role: 'assistant', content: '' },
    ];

    render(
      <ChatInterface {...defaultProps} messages={messages} isLoading={true} />
    );

    expect(screen.getByLabelText(/assistant is typing/i)).toBeInTheDocument();
  });

  // 43.4 Test error message displays with retry button on failure
  it('displays error message with retry button on failure', () => {
    render(
      <ChatInterface {...defaultProps} error="Something went wrong" />
    );

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    const retryButton = screen.getByRole('button', { name: /retry/i });
    expect(retryButton).toBeInTheDocument();

    fireEvent.click(retryButton);
    expect(mockOnRetry).toHaveBeenCalledTimes(1);
  });

  it('shows "Response was interrupted" for stream interruption errors', () => {
    render(
      <ChatInterface {...defaultProps} error="Request was interrupted" />
    );

    expect(
      screen.getByText(/response was interrupted/i)
    ).toBeInTheDocument();
  });

  // 43.5 Test message list has role="log" and aria-live="polite"
  it('message list has role="log" and aria-live="polite"', () => {
    render(<ChatInterface {...defaultProps} />);

    const messageList = screen.getByRole('log');
    expect(messageList).toBeInTheDocument();
    expect(messageList).toHaveAttribute('aria-live', 'polite');
  });

  it('sends message on Enter key press', () => {
    render(<ChatInterface {...defaultProps} />);

    const input = screen.getByLabelText(/chat message input/i);
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    expect(mockOnSendMessage).toHaveBeenCalledWith('Hello');
  });

  it('clears input after sending message', () => {
    render(<ChatInterface {...defaultProps} />);

    const input = screen.getByLabelText(/chat message input/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    expect(input.value).toBe('');
  });

  it('does not send on Shift+Enter', () => {
    render(<ChatInterface {...defaultProps} />);

    const input = screen.getByLabelText(/chat message input/i);
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter', shiftKey: true });

    expect(mockOnSendMessage).not.toHaveBeenCalled();
  });
});
