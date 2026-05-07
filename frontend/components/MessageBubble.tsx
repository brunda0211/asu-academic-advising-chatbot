'use client';

import type { ChatMessage } from '@/hooks/useChat';

interface MessageBubbleProps {
  message: ChatMessage;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <article
      role="article"
      aria-label={`${isUser ? 'You' : 'GUIDE assistant'} said`}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[85%] sm:max-w-[75%] rounded-lg px-4 py-2 text-sm leading-relaxed ${
          isUser
            ? 'bg-[#8C1D40] text-white rounded-br-none'
            : 'bg-gray-100 text-gray-800 rounded-bl-none'
        }`}
      >
        {/* Message content with whitespace preserved */}
        <p className="whitespace-pre-wrap break-words">{message.content}</p>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-200">
            <p className="text-xs font-medium text-gray-500 mb-1">Sources:</p>
            <ul className="space-y-0.5">
              {message.citations.map((source, idx) => (
                <li key={idx}>
                  <a
                    href={source}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-[#8C1D40] underline hover:text-[#6b1631] break-all"
                  >
                    {formatCitationLabel(source, idx)}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </article>
  );
}

/** Extracts a readable label from an S3 URI or URL. */
function formatCitationLabel(source: string, index: number): string {
  try {
    // Extract filename from S3 URI like s3://bucket/docs/file.pdf
    const parts = source.split('/');
    const filename = parts[parts.length - 1];
    if (filename) return decodeURIComponent(filename);
  } catch {
    // Fall through to default
  }
  return `Source ${index + 1}`;
}
