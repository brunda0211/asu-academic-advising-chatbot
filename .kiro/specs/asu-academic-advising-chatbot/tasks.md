# Tasks: GUIDE — ASU Academic Advising Chatbot

## Overview

Implementation tasks for the GUIDE chatbot, organized in backend-first order: CDK infrastructure → Lambda handler → API Gateway integration → Frontend. Tests are deferred until all implementation tasks are complete.

**Task Conventions:**
- `- [ ]` = Trackable task with checkbox
- `- ` (no checkbox) = Implementation detail or context
- `- [ ]* ` = Property-based test task (deferred to testing phase)
- `_Requirements: [list]_` = Traceability to requirements
- Tag each property test with comment: `# Property N: [Name]` and `# Validates: Requirements [list]`

---

## Phase 1: Backend Infrastructure (CDK Stack)

### 1.1 Project Setup and CDK Stack Scaffolding

- [x] 1. Initialize CDK stack with cdk-nag AwsSolutions checks
  - [x] 1.1 Add `cdk-nag` dependency to `backend/package.json` and install
  - [x] 1.2 Configure `Aspects.of(app).add(new AwsSolutionsChecks())` in `backend/bin/backend.ts`
  - [x] 1.3 Add `cdk-s3-vectors` dependency to `backend/package.json` and install
  - [x] 1.4 Define CDK context variables in `backend/cdk.json`: `githubToken`, `githubOwner`, `githubRepo`, `projectPrefix`
  - [x] 1.5 Set up `BackendStack` constructor to read context variables with validation
    - Throw descriptive error if required context variables are missing
    - _Requirements: NFR-SECURITY-1, NFR-OBSERVABILITY-1_

### 1.2 S3 Storage Layer

- [x] 2. Create Documents Bucket for academic advising documents
  - [x] 2.1 Create S3 bucket with `enforceSSL: true`, `blockPublicAccess: BlockPublicAccess.BLOCK_ALL`, `encryption: BucketEncryption.S3_MANAGED`
  - [x] 2.2 Enable `autoDeleteObjects: true` and `removalPolicy: RemovalPolicy.DESTROY` for dev lifecycle
  - [x] 2.3 Add `docs/` prefix documentation in code comments for admin upload convention
    - Validates Properties: P27 (S3 Encryption at Rest), P28 (S3 SSL Enforcement), P29 (S3 Block Public Access)
    - _Requirements: NFR-SECURITY-1_

- [x] 3. Create S3 Vectors Bucket and Vector Index
  - [x] 3.1 Create S3 Vectors bucket using `cdk-s3-vectors` `S3VectorsBucket` construct
  - [x] 3.2 Create Vector Index with configuration: `dimensionCount: 1024`, `distanceMetric: cosine`, `dataType: float32`
  - [x] 3.3 Add cdk-nag suppressions for S3 Vectors internal constructs (ADR-7): AwsSolutions-IAM5, AwsSolutions-IAM4, AwsSolutions-L1
    - Suppression reason: "Internal construct managed by cdk-s3-vectors package"
    - Validates Properties: P27 (S3 Encryption at Rest)
    - _Requirements: NFR-SECURITY-1, FR-RAG-1_

### 1.3 Bedrock Knowledge Base

- [x] 4. Create Knowledge Base Role and Knowledge Base
  - [x] 4.1 Create IAM role for Bedrock KB with `bedrock.amazonaws.com` as trusted principal
  - [x] 4.2 Grant KB role `s3:GetObject` and `s3:ListBucket` on Documents Bucket ARN
  - [x] 4.3 Grant KB role `bedrock:InvokeModel` on Titan Embed V2 ARN (`amazon.titan-embed-text-v2:0`)
  - [x] 4.4 Grant KB role S3 Vectors permissions (wildcard with cdk-nag suppression per ADR-7)
  - [x] 4.5 Create `CfnKnowledgeBase` with S3_VECTORS storage configuration pointing to S3 Vectors bucket and index
  - [x] 4.6 Set embedding model to Titan Embed V2 with 1024 dimensions
    - _Requirements: FR-RAG-1, NFR-SECURITY-1_

- [x] 5. Create Knowledge Base Data Source
  - [x] 5.1 Create `CfnDataSource` pointing to Documents Bucket with `docs/` prefix inclusion pattern
  - [x] 5.2 Configure fixed-size chunking: 525 tokens, 15% overlap
  - [x] 5.3 Set data source type to S3 with appropriate bucket ARN
    - Validates Properties: P7 (Retrieval Invocation), P8 (Retrieval Result Count)
    - _Requirements: FR-RAG-1_

### 1.4 Chat Lambda Infrastructure

- [x] 6. Create Chat Lambda function and IAM role
  - [x] 6.1 Create Lambda function directory: `backend/lambda/chat/`
  - [x] 6.2 Create placeholder `index.py` handler file (implementation in Phase 2)
  - [x] 6.3 Define Lambda function in CDK: Python 3.13 runtime (upgraded from 3.12 per cdk-nag AwsSolutions-L1), 512 MB memory, 5-minute timeout
  - [x] 6.4 Detect host architecture for Lambda architecture (ARM64 on Apple Silicon, x86_64 on Intel) per backend-standards.md
  - [x] 6.5 Create dedicated IAM role (`ChatLambdaRole`) with least-privilege permissions:
    - `bedrock:Retrieve` on KB ARN
    - `bedrock:InvokeModelWithResponseStream` on Nova Lite ARN for us-east-1, us-east-2, us-west-2
    - Add cdk-nag suppression for cross-region Bedrock ARNs (ADR-7)
  - [x] 6.6 Set environment variables: `KNOWLEDGE_BASE_ID`, `MODEL_ID` (`us.amazon.nova-lite-v1:0`), `NUM_KB_RESULTS` (`5`), `MAX_TOKENS` (`4096`), `TEMPERATURE` (`0.7`), `LOG_LEVEL` (`INFO`)
    - `CORS_ALLOWED_ORIGIN` set after Amplify app is created (Task 9)
    - Validates Properties: P16 (Model ID Correctness), P17 (Inference Config Bounds)
    - _Requirements: FR-CHAT-3, NFR-SECURITY-1_

### 1.5 API Gateway

- [x] 7. Create REST API V1 with /chat endpoint
  - [x] 7.1 Create `RestApi` with access logging enabled to CloudWatch log group
  - [x] 7.2 Create `/chat` resource with POST method using `LambdaIntegration` (streaming enabled)
  - [x] 7.3 Add OPTIONS preflight method for CORS on `/chat` resource
  - [x] 7.4 Configure default CORS: allow origins (Amplify URL placeholder + `http://localhost:3000`), allow headers (`Content-Type`), allow methods (`POST, OPTIONS`)
  - [x] 7.5 Add cdk-nag suppressions for public endpoint (ADR-7): AwsSolutions-APIG4, AwsSolutions-COG4
    - Suppression reason: "Public academic advising endpoint — no authentication by design"
    - Validates Properties: P23 (CORS Headers on All Responses), P30 (API Gateway Access Logging)
    - _Requirements: NFR-CORS-1, NFR-OBSERVABILITY-1_

### 1.6 Amplify Hosting

- [x] 8. Create Amplify App for Next.js frontend
  - [x] 8.1 Create `CfnApp` with `WEB_COMPUTE` platform, no SPA rewrite rules
  - [x] 8.2 Set `AMPLIFY_MONOREPO_APP_ROOT` to `frontend` in environment variables
  - [x] 8.3 Configure GitHub source with OAuth token from SSM Parameter Store (via CDK context `githubToken`)
  - [x] 8.4 Create Amplify branch (main) with `NEXT_PUBLIC_API_URL` environment variable pointing to API Gateway URL + `/chat`
    - _Requirements: NFR-DEPLOYMENT-1_

- [x] 9. Wire Amplify URL back to CORS configuration
  - [x] 9.1 Update Chat Lambda `CORS_ALLOWED_ORIGIN` environment variable with Amplify app default domain URL
  - [x] 9.2 Update API Gateway CORS allowed origins to include Amplify URL
    - Validates Properties: P23 (CORS Headers on All Responses)
    - _Requirements: NFR-CORS-1_

### 1.7 Post-Deploy Custom Resources

- [x] 10. Create CustomResource to trigger initial KB sync
  - [x] 10.1 Create a CDK `AwsCustomResource` that calls `bedrock-agent:StartIngestionJob` on stack creation
  - [x] 10.2 Scope IAM permissions to `bedrock:StartIngestionJob` on the specific KB and data source ARN
  - [x] 10.3 Add cdk-nag suppression if needed for custom resource Lambda role
    - _Requirements: FR-RAG-1_

- [x] 11. Create AwsCustomResource to trigger Amplify build on deploy
  - [x] 11.1 Create `AwsCustomResource` that calls `amplify:StartJob` with `jobType: RELEASE` on stack creation/update
  - [x] 11.2 Scope IAM permissions to `amplify:StartJob` on the specific Amplify app and branch ARN
    - _Requirements: NFR-DEPLOYMENT-1_

### 1.8 Stack Outputs

- [x] 12. Add CfnOutputs for key resource identifiers
  - [x] 12.1 Output API Gateway URL (`ApiUrl`)
  - [x] 12.2 Output Amplify App default domain (`AmplifyUrl`)
  - [x] 12.3 Output Knowledge Base ID (`KnowledgeBaseId`)
  - [x] 12.4 Output Documents Bucket name (`DocumentsBucketName`)
    - _Requirements: NFR-DEPLOYMENT-1_

---

- [x] 13. **CHECKPOINT: CDK Infrastructure Complete**
  - Run `cdk synth` — must complete without errors
  - Verify cdk-nag produces no unsuppressed AwsSolutions findings
  - Verify all expected resources appear in synthesized CloudFormation template
  - Verify IAM roles have least-privilege permissions (no wildcard actions)
  - Verify all S3 buckets have encryption, BPA, and enforceSSL
  - Verify API Gateway has access logging configured
  - _Validates: P27, P28, P29, P30_

---

## Phase 2: Chat Lambda Implementation

### 2.1 Lambda Handler Core

- [x] 14. Implement Chat Lambda handler (`backend/lambda/chat/index.py`)
  - [x] 14.1 Create module-level AWS clients (per backend-standards.md): `bedrock_agent_runtime` (for KB Retrieve), `bedrock_runtime` (for converse_stream)
  - [x] 14.2 Read environment variables at module level using `os.environ.get()`: `KNOWLEDGE_BASE_ID`, `MODEL_ID`, `NUM_KB_RESULTS`, `MAX_TOKENS`, `TEMPERATURE`, `CORS_ALLOWED_ORIGIN`, `LOG_LEVEL`
  - [x] 14.3 Implement structured JSON logger with fields: `timestamp`, `level`, `action`, `request_id`
  - [x] 14.4 Implement `lambda_handler(event, context)` entry point as thin handler that delegates to internal functions
    - Validates Properties: P31 (Lambda Structured Logging)
    - _Requirements: FR-CHAT-1, NFR-OBSERVABILITY-1_

### 2.2 Input Validation

- [x] 15. Implement request validation logic
  - [x] 15.1 Parse JSON body from API Gateway event, return 400 if body is missing or invalid JSON
  - [x] 15.2 Validate `message` field: required, non-empty after trim, max 2000 characters
  - [x] 15.3 Validate `session_id` field: required, minimum 33 characters
  - [x] 15.4 Validate `context.academic_year`: must be one of `Freshman`, `Sophomore`, `Junior`, `Senior`, `Graduate`
  - [x] 15.5 Validate `context.major`: required, non-empty, max 200 characters
  - [x] 15.6 Validate `context.advising_topic`: must be one of `Course Planning`, `Degree Requirements`, `Academic Standing`, `General Advising`
  - [x] 15.7 Return 400 with specific error message for each validation failure, include CORS headers on all error responses
  - [x] 15.8 Log validation failures at WARN level (log field name and reason, NOT the user's message content)
    - Validates Properties: P1 (Message Presence), P2 (Message Length Bound), P3 (Session ID Format), P4 (Academic Year Enum), P5 (Major Field Presence), P6 (Advising Topic Enum), P32 (No PII in Logs)
    - _Requirements: FR-CHAT-1, FR-QUESTIONNAIRE-1, FR-SESSION-1, NFR-SECURITY-2, NFR-SECURITY-3_

### 2.3 Knowledge Base Retrieval

- [x] 16. Implement KB retrieval logic
  - [x] 16.1 Call `bedrock_agent_runtime.retrieve()` with `knowledgeBaseId` from env var and `retrievalQuery` from user message
  - [x] 16.2 Request `NUM_KB_RESULTS` (default 5) results via `retrievalConfiguration.vectorSearchConfiguration.numberOfResults`
  - [x] 16.3 Extract text content from retrieval results and join with double newlines for context injection
  - [x] 16.4 Extract S3 source URIs from result metadata for citation events
  - [x] 16.5 Handle empty retrieval results gracefully: proceed with empty context string, log at INFO level
  - [x] 16.6 Handle retrieval exceptions with try/except: log error at ERROR level, proceed with empty context (do NOT return 500)
    - Validates Properties: P7 (Retrieval Invocation), P8 (Retrieval Result Count), P9 (Context Injection), P10 (Empty Retrieval Graceful Handling), P11 (Retrieval Failure Resilience), P12 (Citation Extraction)
    - _Requirements: FR-RAG-1, FR-RAG-2, FR-RAG-3, NFR-RELIABILITY-1_

### 2.4 Prompt Construction

- [x] 17. Implement system prompt construction
  - [x] 17.1 Define `SYSTEM_PROMPT_TEMPLATE` constant with instruction block, student context block, and retrieved documents block (per design.md System Prompt Template section)
  - [x] 17.2 Inject `academic_year`, `major`, `advising_topic` into designated placeholders only (never into instruction text)
  - [x] 17.3 Inject retrieved context into `{retrieved_context}` placeholder
  - [x] 17.4 Use clear delimiters (`## Student Context`, `## Retrieved ASU Documents`) between sections
  - [x] 17.5 If no retrieved context, include a note: "No documents were retrieved for this query."
    - Validates Properties: P13 (Student Context Inclusion), P14 (System Prompt Structure), P15 (No User Input in Instructions)
    - _Requirements: FR-QUESTIONNAIRE-2, FR-CHAT-2, NFR-SECURITY-3_

### 2.5 Streaming Response

- [x] 18. Implement Bedrock converse_stream and SSE streaming
  - [x] 18.1 Call `bedrock_runtime.converse_stream()` with model ID `us.amazon.nova-lite-v1:0`, system prompt, and user message
  - [x] 18.2 Set inference config: `maxTokens` from env var (default 4096), `temperature` from env var (default 0.7)
  - [x] 18.3 Iterate over stream events, format each text chunk as SSE: `data: {"type": "text-delta", "content": "..."}\n\n`
  - [x] 18.4 After text streaming completes, emit citations event: `data: {"type": "citations", "sources": [...]}\n\n`
  - [x] 18.5 Emit finish event with token usage: `data: {"type": "finish", "usage": {"input_tokens": N, "output_tokens": N}}\n\n`
  - [x] 18.6 Handle streaming errors: if error occurs mid-stream, emit error event `data: {"type": "error", "message": "..."}\n\n` before closing
  - [x] 18.7 Handle Bedrock throttling: catch `ThrottlingException`, return 429 with appropriate error message and CORS headers
  - [x] 18.8 Set response headers: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`, plus CORS headers
    - Validates Properties: P16 (Model ID Correctness), P17 (Inference Config Bounds), P18 (SSE Format Compliance), P19 (Stream Termination), P20 (Chunk Content Type), P21 (Stream Error Event), P22 (No Empty Streams), P23 (CORS Headers on All Responses)
    - _Requirements: FR-CHAT-3, FR-STREAM-1, FR-STREAM-2, NFR-CORS-1_

### 2.6 CORS Response Helper

- [x] 19. Implement CORS response helper function
  - [x] 19.1 Create `build_cors_headers()` function that reads `CORS_ALLOWED_ORIGIN` from env var
  - [x] 19.2 Return headers dict with `Access-Control-Allow-Origin`, `Access-Control-Allow-Headers` (`Content-Type`), `Access-Control-Allow-Methods` (`POST, OPTIONS`)
  - [x] 19.3 Apply CORS headers to ALL responses: success streams, 400 errors, 429 errors, 500 errors
    - Validates Properties: P23 (CORS Headers on All Responses)
    - _Requirements: NFR-CORS-1_

---

- [ ] 20. **CHECKPOINT: Chat Lambda Complete**
  - Lambda handler parses request, validates input, retrieves from KB, constructs prompt, streams response
  - All error paths return appropriate status codes with CORS headers
  - Structured JSON logging on all code paths
  - No PII (full message content) in log output
  - No hardcoded secrets or configuration values
  - _Validates: P1–P23, P31, P32_

---

## Phase 3: Frontend Implementation

### 3.1 Frontend Project Setup

- [x] 21. Configure Next.js project for the chatbot
  - [x] 21.1 Verify `frontend/package.json` has Next.js, React, TypeScript, Tailwind CSS dependencies at latest stable versions
  - [x] 21.2 Add `NEXT_PUBLIC_API_URL` to `.env.local` for local development (pointing to localhost or deployed API)
  - [x] 21.3 Configure TypeScript strict mode in `frontend/tsconfig.json`
  - [x] 21.4 Verify Tailwind CSS configuration in `frontend/postcss.config.mjs` and `frontend/app/globals.css`
    - _Requirements: NFR-DEPLOYMENT-1_

### 3.2 Session Management

- [x] 22. Implement session management utilities (`frontend/lib/session.ts`)
  - [x] 22.1 Create `generateSessionId()` function: format `session_{timestamp}_{random}`, minimum 33 characters
  - [x] 22.2 Create `getOrCreateSessionId()` that checks `sessionStorage` first, generates new if absent
  - [x] 22.3 Create `getQuestionnaireData()` and `setQuestionnaireData()` for sessionStorage read/write
  - [x] 22.4 Create `clearSession()` for cleanup
  - [x] 22.5 Export TypeScript interfaces: `QuestionnaireData` (academic_year, major, advising_topic), `SessionData`
    - Validates Properties: P25 (Session ID Generation), P26 (Session Persistence)
    - _Requirements: FR-SESSION-1, FR-SESSION-2_

### 3.3 API Client

- [x] 23. Implement chat API client (`frontend/lib/api.ts`)
  - [x] 23.1 Create `sendChatMessage()` function that sends POST to `NEXT_PUBLIC_API_URL` with message, session_id, and context
  - [x] 23.2 Use `fetch` with `AbortController` timeout (30 seconds)
  - [x] 23.3 Return `ReadableStream` reader for SSE parsing
  - [x] 23.4 Implement `parseSSEStream()` function that reads chunks via `TextDecoder`, splits on `data: ` prefix, parses JSON
  - [x] 23.5 Handle network errors, timeout errors, and HTTP error responses with typed error classes
  - [x] 23.6 Implement retry logic with exponential backoff (max 3 attempts) for 5xx errors only
    - Validates Properties: P34 (Streaming Display)
    - _Requirements: FR-STREAM-3, FR-CHAT-5_

### 3.4 useChat Custom Hook

- [x] 24. Implement `useChat` custom hook (`frontend/hooks/useChat.ts`)
  - [x] 24.1 Manage state: `messages` array (role + content), `isLoading` boolean, `error` string | null
  - [x] 24.2 Implement `sendMessage(text)` function that:
    - Adds user message to messages array
    - Calls `sendChatMessage()` with message, session ID, and questionnaire context
    - Streams response chunks into an assistant message (append content incrementally)
    - Sets `isLoading` to false and emits finish when stream completes
  - [x] 24.3 Implement `clearError()` and `retry()` functions
  - [x] 24.4 Strip HTML tags from user input before sending (input sanitization)
  - [x] 24.5 Handle AbortController cleanup on component unmount
    - Validates Properties: P34 (Streaming Display), P35 (Loading State), P37 (Input Sanitization)
    - _Requirements: FR-CHAT-1, FR-CHAT-4, FR-CHAT-5, FR-STREAM-3, NFR-SECURITY-3_

### 3.5 Chat Context Provider

- [x] 25. Implement ChatContext provider (`frontend/contexts/ChatContext.tsx`)
  - [x] 25.1 Create React Context that provides questionnaire data and session ID to child components
  - [x] 25.2 Initialize session ID on mount via `getOrCreateSessionId()`
  - [x] 25.3 Load questionnaire data from sessionStorage on mount
  - [x] 25.4 Provide `setQuestionnaireData()` function for the questionnaire form
  - [x] 25.5 Wrap the app layout with `ChatProvider` in `frontend/app/layout.tsx`
    - Validates Properties: P26 (Session Persistence)
    - _Requirements: FR-SESSION-2, FR-QUESTIONNAIRE-2_

### 3.6 Questionnaire Page

- [x] 26. Implement Questionnaire page (`frontend/app/page.tsx`)
  - [x] 26.1 Create `QuestionnaireForm` client component with fields:
    - Academic Year: dropdown (Freshman, Sophomore, Junior, Senior, Graduate)
    - Major: text input (required, max 200 chars)
    - Advising Topic: dropdown (Course Planning, Degree Requirements, Academic Standing, General Advising)
  - [x] 26.2 Add client-side form validation: all fields required, major non-empty
  - [x] 26.3 On submit: save data to sessionStorage via context, navigate to `/chat` using `useRouter().push()`
  - [x] 26.4 Style with Tailwind CSS: centered card layout, responsive (mobile-first), ASU-themed colors
  - [x] 26.5 Add semantic HTML: `<form>`, `<label>`, `<select>`, `<input>` with proper `htmlFor` and `id` attributes
  - [x] 26.6 Add ARIA labels for accessibility: `aria-required`, `aria-invalid` on validation errors, `role="alert"` for error messages
    - Validates Properties: P33 (Questionnaire Completion Gate)
    - _Requirements: FR-QUESTIONNAIRE-1, NFR-ACCESSIBILITY-1_

### 3.7 Chat Page

- [x] 27. Implement Chat page (`frontend/app/chat/page.tsx`)
  - [x] 27.1 Add questionnaire completion gate: if no questionnaire data in sessionStorage, redirect to `/` via `useRouter().replace()`
  - [x] 27.2 Initialize `useChat` hook with session ID and questionnaire context from ChatContext
  - [x] 27.3 Create `ChatInterface` client component with message list and input area
    - Validates Properties: P33 (Questionnaire Completion Gate)
    - _Requirements: FR-QUESTIONNAIRE-3, FR-CHAT-1_

- [x] 28. Implement ChatInterface component (`frontend/components/ChatInterface.tsx`)
  - [x] 28.1 Render scrollable message list with auto-scroll to bottom on new messages
  - [x] 28.2 Render input area: text input + send button, disable send button while `isLoading`
  - [x] 28.3 Show loading indicator (typing animation or spinner) while waiting for response
  - [x] 28.4 Display streaming text incrementally as chunks arrive (not waiting for complete response)
  - [x] 28.5 Style with Tailwind CSS: full-height layout, message bubbles (user right-aligned, assistant left-aligned), responsive
  - [x] 28.6 Add semantic HTML and ARIA: `role="log"` on message list, `aria-live="polite"` for new messages, `aria-busy` during loading
    - Validates Properties: P34 (Streaming Display), P35 (Loading State), P38 (Responsive Layout)
    - _Requirements: FR-CHAT-1, FR-CHAT-4, FR-STREAM-3, NFR-ACCESSIBILITY-1_

- [x] 29. Implement MessageBubble component (`frontend/components/MessageBubble.tsx`)
  - [x] 29.1 Render user messages with right-aligned bubble styling
  - [x] 29.2 Render assistant messages with left-aligned bubble styling, support incremental text display
  - [x] 29.3 Render citation links when present (from citations event)
  - [x] 29.4 Add `role="article"` and `aria-label` indicating message sender
    - _Requirements: FR-CHAT-1, FR-RAG-2, NFR-ACCESSIBILITY-1_

### 3.8 Error Handling UI

- [x] 30. Implement frontend error handling
  - [x] 30.1 Display user-friendly error messages for network errors, timeouts, and server errors
  - [x] 30.2 Add retry button that calls `useChat.retry()` for failed messages
  - [x] 30.3 Show "Response was interrupted. Try again." for stream interruptions (incomplete stream detected)
  - [x] 30.4 Show specific error messages from 4xx API responses (parse error body)
  - [x] 30.5 Style error messages with warning colors, add `role="alert"` for screen readers
    - Validates Properties: P36 (Error Display)
    - _Requirements: FR-CHAT-5_

---

- [ ] 31. **CHECKPOINT: Frontend Complete**
  - Questionnaire page collects and validates all required fields
  - Chat page enforces questionnaire completion gate
  - Messages stream incrementally from API
  - Loading states and error handling work correctly
  - Session ID persists across page navigations
  - UI is responsive from 320px to 1920px
  - All interactive elements have ARIA labels
  - _Validates: P25, P26, P33–P38_

---

## Phase 4: Integration and Verification

- [x] 32. End-to-end integration verification
  - [x] 32.1 Run `cdk synth` and verify clean output with no unsuppressed cdk-nag findings
  - [x] 32.2 Verify Lambda handler imports and runs locally with mock event (no AWS calls)
  - [x] 32.3 Verify frontend builds successfully with `npm run build` in `frontend/`
  - [x] 32.4 Verify all environment variables are wired correctly between CDK stack and Lambda/Amplify
  - [x] 32.5 Review all cdk-nag suppressions have ADR justification comments
    - _Requirements: NFR-SECURITY-1, NFR-DEPLOYMENT-1_

- [x] 33. Upload sample academic documents
  - [x] 33.1 Create `backend/sample-docs/` directory with 2-3 sample ASU academic documents (text or markdown format)
  - [x] 33.2 Document the upload and sync process in code comments: `aws s3 cp` to Documents Bucket `docs/` prefix, then `aws bedrock-agent start-ingestion-job`
    - _Requirements: FR-RAG-1_

---

## Phase 5: Testing (After All Implementation Complete)

> **Note:** All test tasks are grouped here and should be executed ONLY after Phases 1–4 are complete. Tag each property test with comment: `# Property N: [Name]` and `# Validates: Requirements [list]`

### 5.1 CDK Stack Tests (Jest + CDK Assertions)

- [x] 34. Write CDK infrastructure tests (`backend/test/backend.test.ts`)
  - [x] 34.1 Test S3 Documents Bucket has encryption, BPA, and enforceSSL
  - [x] 34.2 Test S3 Vectors Bucket and Vector Index are created with correct dimensions
  - [x] 34.3 Test Knowledge Base is created with S3_VECTORS storage config
  - [x] 34.4 Test Chat Lambda has correct runtime (Python 3.12), timeout (5 min), memory (512 MB)
  - [x] 34.5 Test Chat Lambda environment variables are set correctly
  - [x] 34.6 Test ChatLambdaRole has bedrock:Retrieve and bedrock:InvokeModelWithResponseStream permissions
  - [x] 34.7 Test REST API V1 has /chat POST method with Lambda integration
  - [x] 34.8 Test API Gateway has access logging enabled
  - [x] 34.9 Test Amplify App has WEB_COMPUTE platform
  - [x] 34.10 Test CfnOutputs exist for ApiUrl, AmplifyUrl, KnowledgeBaseId, DocumentsBucketName
  - [x] 34.11 Run `cdk synth` to verify cdk-nag compliance (no unsuppressed findings)
    - Validates Properties: P27, P28, P29, P30
    - _Requirements: NFR-SECURITY-1, NFR-OBSERVABILITY-1_

### 5.2 Lambda Unit Tests (pytest)

- [x] 35. Write Chat Lambda unit tests (`backend/lambda/chat/test_index.py`)
  - [x] 35.1 Test valid request returns 200 with SSE stream headers
  - [x] 35.2 Test missing message returns 400 with error body
  - [x] 35.3 Test message exceeding 2000 chars returns 400
  - [x] 35.4 Test invalid session_id (< 33 chars) returns 400
  - [x] 35.5 Test invalid academic_year enum returns 400
  - [x] 35.6 Test empty major returns 400
  - [x] 35.7 Test invalid advising_topic enum returns 400
  - [x] 35.8 Test KB retrieval failure proceeds without context (no 500)
  - [x] 35.9 Test empty KB retrieval results proceeds with empty context
  - [x] 35.10 Test CORS headers present on all response types (success, 400, 500)
  - [x] 35.11 Test structured JSON log output format
  - [x] 35.12 Test no full message content appears in log output
    - Validates Properties: P1–P6, P10, P11, P23, P31, P32
    - _Requirements: FR-CHAT-1, FR-RAG-3, NFR-CORS-1, NFR-OBSERVABILITY-1, NFR-SECURITY-2_

### 5.3 Lambda Property-Based Tests (pytest + hypothesis)

- [x] 36. Write property-based tests for input validation
  - [x] 36.1 Property 1: Message Presence — generate empty/None messages, verify 400 and no Bedrock invocation
  - [x] 36.2 Property 2: Message Length Bound — generate strings > 2000 chars, verify 400
  - [x] 36.3 Property 3: Session ID Format — generate strings < 33 chars, verify 400
  - [x] 36.4 Property 4: Academic Year Enum — generate strings not in allowed set, verify 400
  - [x] 36.5 Property 5: Major Field Presence — generate empty/oversized strings, verify 400
  - [x] 36.6 Property 6: Advising Topic Enum — generate strings not in allowed set, verify 400
    - Configure hypothesis: `max_examples=100`, `deadline=5000`
    - Validates Properties: P1–P6
    - _Requirements: FR-CHAT-1, FR-QUESTIONNAIRE-1, FR-SESSION-1_

- [x] 37. Write property-based tests for prompt construction
  - [x] 37.1 Property 13: Student Context Inclusion — generate random valid context values, verify all appear in system prompt
  - [x] 37.2 Property 14: System Prompt Structure — verify instruction block, student context block, and retrieved docs block appear in order
  - [x] 37.3 Property 15: No User Input in Instructions — generate random messages with injection attempts, verify they only appear in user message position
    - Configure hypothesis: `max_examples=100`
    - Validates Properties: P13–P15
    - _Requirements: FR-QUESTIONNAIRE-2, FR-CHAT-2, NFR-SECURITY-3_

- [x] 38. Write property-based tests for CORS compliance
  - [x] 38.1 Property 23: CORS Headers on All Responses — generate random valid and invalid requests, verify CORS headers present on every response
    - Configure hypothesis: `max_examples=100`
    - Validates Properties: P23
    - _Requirements: NFR-CORS-1_

### 5.4 Frontend Unit Tests (Jest + React Testing Library)

- [x] 39. Write session management tests (`frontend/lib/__tests__/session.test.ts`)
  - [x] 39.1 Test `generateSessionId()` produces IDs ≥ 33 characters starting with `session_`
  - [x] 39.2 Test `getOrCreateSessionId()` returns existing ID from sessionStorage
  - [x] 39.3 Test `getOrCreateSessionId()` creates new ID when sessionStorage is empty
  - [x] 39.4 Test `setQuestionnaireData()` and `getQuestionnaireData()` round-trip
    - Validates Properties: P25, P26
    - _Requirements: FR-SESSION-1, FR-SESSION-2_

- [x] 40. Write API client tests (`frontend/lib/__tests__/api.test.ts`)
  - [x] 40.1 Test `sendChatMessage()` sends correct request body format
  - [x] 40.2 Test `parseSSEStream()` correctly parses text-delta, citations, and finish events
  - [x] 40.3 Test AbortController timeout triggers after 30 seconds
  - [x] 40.4 Test retry logic with exponential backoff on 5xx errors (max 3 attempts)
  - [x] 40.5 Test no retry on 4xx errors
    - _Requirements: FR-STREAM-3, FR-CHAT-5_

- [x] 41. Write useChat hook tests (`frontend/hooks/__tests__/useChat.test.ts`)
  - [x] 41.1 Test sendMessage adds user message and streams assistant response
  - [x] 41.2 Test isLoading is true during request and false after completion
  - [x] 41.3 Test error state is set on failed request
  - [x] 41.4 Test retry function re-sends last failed message
  - [x] 41.5 Test HTML tag stripping on user input
  - [x] 41.6 Test cleanup on unmount (AbortController abort)
    - Validates Properties: P34, P35, P37
    - _Requirements: FR-CHAT-1, FR-CHAT-4, FR-CHAT-5, NFR-SECURITY-3_

- [x] 42. Write QuestionnaireForm component tests (`frontend/components/__tests__/QuestionnaireForm.test.tsx`)
  - [x] 42.1 Test form renders all required fields (academic year, major, advising topic)
  - [x] 42.2 Test form validation prevents submission with empty fields
  - [x] 42.3 Test successful submission saves data to sessionStorage and navigates to /chat
  - [x] 42.4 Test all form fields have associated labels and ARIA attributes
    - Validates Properties: P33
    - _Requirements: FR-QUESTIONNAIRE-1, NFR-ACCESSIBILITY-1_

- [x] 43. Write ChatInterface component tests (`frontend/components/__tests__/ChatInterface.test.tsx`)
  - [x] 43.1 Test message list renders user and assistant messages
  - [x] 43.2 Test send button is disabled during loading
  - [x] 43.3 Test loading indicator appears during pending request
  - [x] 43.4 Test error message displays with retry button on failure
  - [x] 43.5 Test message list has `role="log"` and `aria-live="polite"`
    - Validates Properties: P34, P35, P36, P38
    - _Requirements: FR-CHAT-1, FR-CHAT-4, FR-CHAT-5, NFR-ACCESSIBILITY-1_

- [x] 44. Write Chat page tests (`frontend/app/chat/__tests__/page.test.tsx`)
  - [x] 44.1 Test redirect to `/` when sessionStorage has no questionnaire data
  - [x] 44.2 Test page renders ChatInterface when questionnaire data is present
    - Validates Properties: P33
    - _Requirements: FR-QUESTIONNAIRE-3_

### 5.5 Frontend Property-Based Tests (Jest + fast-check)

- [x] 45. Write property-based tests for session ID generation
  - [x] 45.1 Property 25: Session ID Generation — generate random timestamps, verify ID format (≥ 33 chars, starts with `session_`)
    - Configure fast-check: `numRuns: 100`
    - Validates Properties: P25
    - _Requirements: FR-SESSION-1_

- [x] 46. Write property-based tests for input sanitization
  - [x] 46.1 Property 37: Input Sanitization — generate strings with HTML tags (`<script>`, `<img>`, `<div>`), verify all tags stripped after sanitization
    - Configure fast-check: `numRuns: 100`
    - Validates Properties: P37
    - _Requirements: NFR-SECURITY-3_

---

- [-] 47. **CHECKPOINT: All Tests Pass**
  - Run `pytest` in `backend/lambda/chat/` — all unit and property tests pass
  - Run `npx jest` in `backend/` — all CDK assertion tests pass
  - Run `cdk synth` in `backend/` — cdk-nag compliance verified
  - Run `npm test` in `frontend/` — all component, hook, and property tests pass
  - Review test coverage: all 38 correctness properties have at least one test
  - _Validates: P1–P38_
