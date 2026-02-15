---
inclusion: fileMatch
fileMatchPattern: "frontend/**/*"
---

# Frontend Development Standards

Next.js patterns and standards for CIC frontend projects.

## Technology Stack

**Next.js 15+ with App Router (Required)**
- React 19+ with TypeScript strict mode
- Server-Side Rendering (SSR) and Static Site Generation (SSG)
- Built-in image optimization and code splitting
- File-based routing with App Router

### TypeScript Configuration

**Required tsconfig.json settings:**

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{"name": "next"}],
    "paths": {"@/*": ["./*"]}
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

## Project Structure

```
frontend/
├── app/                     # Next.js App Router
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Home page
│   └── globals.css         # Global styles
├── components/             # Reusable UI components
│   └── ui/                # UI library components
├── hooks/                  # Custom React hooks
├── contexts/               # React Context providers
├── lib/                    # API clients and utilities
│   ├── config.ts          # Configuration
│   └── utils.ts           # Helpers
├── data/                   # Static data
├── public/                 # Static files
├── package.json
├── tsconfig.json
├── next.config.ts
├── postcss.config.mjs
└── tailwind.config.ts
```

## Styling

**Tailwind CSS v4+ (Required)**

```typescript
// tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: { extend: {} },
  plugins: [],
};
export default config;
```

```javascript
// postcss.config.mjs
export default {
  plugins: { tailwindcss: {}, autoprefixer: {} }
};
```

**Typography** - Use Next.js font optimization:

```typescript
import { Geist_Sans, Poppins } from 'next/font/google';

const geistSans = Geist_Sans({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={geistSans.variable}>
      <body className={geistSans.className}>{children}</body>
    </html>
  );
}
```

## API Integration

### Environment Variables

```typescript
// lib/config.ts
export const config = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL!,
  awsRegion: process.env.NEXT_PUBLIC_AWS_REGION!,
};

if (!config.apiUrl) throw new Error('NEXT_PUBLIC_API_URL required');

export const getApiEndpoint = (path: string = '') => {
  const baseUrl = config.apiUrl.replace(/\/$/, '');
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
};
```

**Naming**: `NEXT_PUBLIC_*` for client-side, no prefix for server-side
**Files**: `.env.example` (template), `.env.local` (gitignored)

### Service Layer

```typescript
// lib/apiClient.ts
import { getApiEndpoint } from './config';

export async function fetchData(endpoint: string) {
  const response = await fetch(getApiEndpoint(endpoint));
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return response.json();
}
```

```typescript
// hooks/useChat.ts
'use client';

import { useState } from 'react';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const sendMessage = async (text: string) => {
    setIsLoading(true);
    try {
      // API call logic
    } finally {
      setIsLoading(false);
    }
  };
  
  return { messages, isLoading, sendMessage };
}
```

**Patterns**:
- Separate API logic from UI components
- Use custom hooks for stateful interactions
- Mark client-side hooks with `'use client'`
- Implement error handling and loading states

### Session Management

```typescript
// Generate unique session IDs (33+ chars for AWS AgentCore)
const sessionId = `session_${Date.now()}_${randomString()}`;
sessionStorage.setItem('session_id', sessionId);
```

## Real-time Features (SSE)

```typescript
const reader = response.body?.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  buffer += decoder.decode(value, { stream: true });
  // Process SSE events: text-delta, thinking-start/end, tool-output-available, finish, error
}
```

**UI patterns**: Loading states, character-by-character streaming, collapsible reasoning blocks

## State Management

### Context API

```typescript
// contexts/LanguageContext.tsx
'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

const LanguageContext = createContext<{language: string; setLanguage: (lang: string) => void} | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState('en');
  return <LanguageContext.Provider value={{ language, setLanguage }}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('useLanguage must be used within LanguageProvider');
  return context;
}
```

**Usage in layout**:
```typescript
// app/layout.tsx
import { LanguageProvider } from '@/contexts/LanguageContext';

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body><LanguageProvider>{children}</LanguageProvider></body>
    </html>
  );
}
```

### Custom Hooks

```typescript
// hooks/useStreamingChat.ts
'use client';

import { useState, useCallback } from 'react';

export function useStreamingChat() {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  
  const sendMessage = useCallback(async (text: string) => {
    setIsStreaming(true);
    try {
      // Implementation
    } finally {
      setIsStreaming(false);
    }
  }, []);
  
  return { messages, isStreaming, sendMessage };
}
```

**Rules**: Add `'use client'`, use `useCallback` for functions, use `useMemo` for expensive computations

## Internationalization

**Use react-i18next**:
```typescript
import { useTranslation } from 'react-i18next';
const { t } = useTranslation();
<p>{t('welcome.message')}</p>
```

**Structure**: `public/locales/{lang}/common.json`
**Features**: Browser detection, user preference storage, manual switcher

## Component Patterns

**Chat interfaces**: Separate user/assistant messages, markdown rendering with `react-markdown`, avatars, timestamps, citations, retry/rating actions

**Forms**: Controlled components, validation before submission, loading states, error display, success feedback

**Responsive design**: Mobile-first, breakpoints (480px, 600px, 768px, 1024px), drawer/sidebar for mobile, touch-friendly buttons (min 44x44px)

## AWS Integration

```typescript
// components/AmplifyConfigClient.tsx
import { Amplify } from 'aws-amplify';
import amplifyOutputs from '@/amplify_outputs.json';
Amplify.configure(amplifyOutputs);
```

**Common integrations**: Cognito (auth), S3 (file uploads), Bedrock (AI), Lambda Function URLs (API)

## Performance & Testing

**Optimization**: Dynamic imports for heavy components, Next.js Image component, cache API responses, sessionStorage for temp data

**Testing**: `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`

## Build & Deployment

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  }
}
```

```typescript
// next.config.ts
const nextConfig: NextConfig = {
  reactStrictMode: true,
  images: { domains: ['example.com'] },
  env: { NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL }
};
export default nextConfig;
```

**AWS Amplify**: Automatic CI/CD from GitHub, environment variables via CDK/Console, Next.js SSR support

## Documentation

**README must include**: Overview, architecture, environment variables, local development, deployment, project structure, troubleshooting

**Code comments**: Document API integration patterns, state management flows, streaming implementations, business logic

**Architectural decisions**: Document significant frontend architecture choices (state management approach, routing strategy, API integration pattern) in `docs/architectureDeepDive.md`. Reference decisions in code comments.

```typescript
// ADR: Using Context API instead of Redux
// Decision Date: 2024-01-20
// Rationale: Simpler for chat state, no external dependencies, sufficient for our use case
// Alternative: Redux (rejected - overkill for single-page chat interface)
export const ChatContext = createContext<ChatContextType | undefined>(undefined);
```

## Security & Accessibility

**Security**: Never commit `.env` files, use HTTPS only, sanitize user inputs, generate non-guessable session IDs

**Accessibility**: Semantic HTML, ARIA labels, keyboard navigation, color contrast, screen reader compatibility

## Version Control

**.gitignore**: `node_modules/`, `.next/`, `.env*.local`, `*.log`, `.DS_Store`, `*.tsbuildinfo`, `next-env.d.ts`

**Commits**: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`
