# Requirements Document

## Introduction

The Agentic Job Search system is a conversational AI-powered platform that helps users find jobs, analyze resumes, and receive career guidance. Users interact through a Next.js chat interface that streams responses from an AWS Strands-based AI agent backed by Amazon Bedrock (Claude). The system supports multi-turn conversations, resume uploads, and persists session history in DynamoDB.

## Glossary

- **Agent**: The Strands-based AI orchestrator running in AWS Lambda that routes user requests to specialized tools and generates responses via Amazon Bedrock.
- **Chat_Interface**: The Next.js frontend component through which users send messages and receive streaming responses.
- **Orchestrator_Lambda**: The AWS Lambda function that serves as the main entry point, receives user messages, invokes the Agent, and streams responses back via Lambda Function URL.
- **Job_Search_Tool**: An Agent tool that queries external job listing sources and returns relevant job postings.
- **Resume_Analysis_Tool**: An Agent tool that retrieves a user's uploaded resume from S3 and provides structured feedback.
- **Career_Guidance_Tool**: An Agent tool that provides career path recommendations based on user context.
- **Session**: A persisted record of a user's conversation history stored in DynamoDB, identified by a session ID.
- **SSE**: Server-Sent Events — the streaming protocol used to deliver incremental Agent responses to the frontend.
- **Resume**: A document uploaded by the user to S3 for analysis by the Resume_Analysis_Tool.
- **Bedrock**: Amazon Bedrock service providing the Claude LLM that powers the Agent.

---

## Requirements

### Requirement 1: Chat Interface

**User Story:** As a job seeker, I want to send messages through a chat interface and receive streaming AI responses, so that I can have a natural conversation about my job search.

#### Acceptance Criteria

1. WHEN a user submits a message in the Chat_Interface, THE Chat_Interface SHALL send the message and current session ID to the Orchestrator_Lambda via an HTTP POST request.
2. WHEN the Orchestrator_Lambda begins responding, THE Chat_Interface SHALL display the response incrementally as SSE tokens arrive.
3. WHEN a streaming response is in progress, THE Chat_Interface SHALL display a visual loading indicator.
4. WHEN a streaming response completes, THE Chat_Interface SHALL append the full assistant message to the conversation history display.
5. IF a network error occurs during streaming, THEN THE Chat_Interface SHALL display an error message and allow the user to retry.
6. THE Chat_Interface SHALL render job listings, resume tips, and career guidance returned by the Agent in a structured, readable format.

---

### Requirement 2: Multi-Turn Conversation Support

**User Story:** As a job seeker, I want the AI agent to remember what I said earlier in our conversation, so that I can have coherent multi-turn exchanges without repeating myself.

#### Acceptance Criteria

1. WHEN a user sends a message, THE Orchestrator_Lambda SHALL retrieve the existing Session from DynamoDB using the session ID before invoking the Agent.
2. WHEN the Agent generates a response, THE Orchestrator_Lambda SHALL persist the updated conversation history (user message and assistant response) to DynamoDB.
3. THE Agent SHALL include prior conversation turns from the Session when constructing prompts to Bedrock.
4. WHEN a user starts a new conversation, THE Chat_Interface SHALL generate a new unique session ID and store it for the duration of the browser session.
5. IF a session ID is not found in DynamoDB, THEN THE Orchestrator_Lambda SHALL initialize a new empty Session and proceed normally.

---

### Requirement 3: Job Search

**User Story:** As a job seeker, I want the AI agent to search for relevant job listings based on my stated preferences, so that I can discover opportunities that match my skills and goals.

#### Acceptance Criteria

1. WHEN the Agent determines a user's message requires job listings, THE Agent SHALL invoke the Job_Search_Tool with extracted search parameters (role, location, keywords).
2. WHEN the Job_Search_Tool is invoked, THE Job_Search_Tool SHALL return a list of job postings including title, company, location, and a brief description.
3. WHEN job results are returned, THE Agent SHALL incorporate them into a coherent response to the user.
4. IF the Job_Search_Tool returns no results for the given parameters, THEN THE Agent SHALL inform the user and suggest broadening the search criteria.
5. IF the Job_Search_Tool encounters an external service error, THEN THE Job_Search_Tool SHALL return a structured error response and THE Agent SHALL inform the user that job search is temporarily unavailable.

---

### Requirement 4: Resume Upload and Storage

**User Story:** As a job seeker, I want to upload my resume so that the AI agent can analyze it and provide personalized feedback.

#### Acceptance Criteria

1. WHEN a user selects a resume file in the Chat_Interface, THE Chat_Interface SHALL upload the file directly to S3 using a pre-signed URL.
2. THE Orchestrator_Lambda SHALL generate a pre-signed S3 upload URL scoped to the user's session ID upon request.
3. WHEN a resume is uploaded, THE Chat_Interface SHALL associate the S3 object key with the current session ID.
4. THE S3 bucket SHALL enforce server-side encryption (SSE-S3 or SSE-KMS) for all stored resume objects.
5. IF a file exceeding 10 MB is selected for upload, THEN THE Chat_Interface SHALL reject the upload and display an error message to the user.
6. WHERE resume storage is enabled, THE system SHALL restrict S3 object access to the Orchestrator_Lambda IAM role only.

---

### Requirement 5: Resume Analysis

**User Story:** As a job seeker, I want the AI agent to analyze my uploaded resume and provide actionable feedback, so that I can improve my chances of getting interviews.

#### Acceptance Criteria

1. WHEN the Agent determines a user's message requires resume analysis, THE Agent SHALL invoke the Resume_Analysis_Tool with the S3 object key associated with the current session.
2. WHEN invoked, THE Resume_Analysis_Tool SHALL retrieve the resume document from S3 and extract its text content.
3. WHEN text is extracted, THE Resume_Analysis_Tool SHALL return structured feedback including strengths, areas for improvement, and keyword suggestions.
4. IF no resume has been uploaded for the current session, THEN THE Agent SHALL prompt the user to upload a resume before analysis can proceed.
5. IF the Resume_Analysis_Tool cannot parse the uploaded file, THEN THE Resume_Analysis_Tool SHALL return a structured error and THE Agent SHALL inform the user that the file format is unsupported.

---

### Requirement 6: Career Guidance

**User Story:** As a job seeker, I want the AI agent to provide career path recommendations based on my background and goals, so that I can make informed decisions about my professional development.

#### Acceptance Criteria

1. WHEN the Agent determines a user's message requires career guidance, THE Agent SHALL invoke the Career_Guidance_Tool with relevant context extracted from the conversation.
2. WHEN invoked, THE Career_Guidance_Tool SHALL return structured career path recommendations including suggested roles, required skills, and learning resources.
3. WHEN career guidance is returned, THE Agent SHALL present the recommendations in a clear, actionable format within the streaming response.
4. IF insufficient context is available to generate meaningful guidance, THEN THE Career_Guidance_Tool SHALL return a clarifying question for the Agent to relay to the user.

---

### Requirement 7: Streaming SSE Responses

**User Story:** As a job seeker, I want to see the AI agent's response appear word-by-word as it is generated, so that I get immediate feedback without waiting for the full response.

#### Acceptance Criteria

1. THE Orchestrator_Lambda SHALL expose a Lambda Function URL with streaming response mode enabled.
2. WHEN the Agent generates tokens, THE Orchestrator_Lambda SHALL emit each token as an SSE `data:` event over the Lambda Function URL response stream.
3. WHEN the Agent finishes generating a response, THE Orchestrator_Lambda SHALL emit a terminal SSE event (e.g., `data: [DONE]`) to signal stream completion.
4. THE Orchestrator_Lambda SHALL set the `Content-Type` response header to `text/event-stream` for all streaming responses.
5. IF the Agent raises an unhandled exception during streaming, THEN THE Orchestrator_Lambda SHALL emit an SSE error event before closing the stream.

---

### Requirement 8: Session Persistence

**User Story:** As a job seeker, I want my conversation history to be saved so that I can return to a previous session and continue where I left off.

#### Acceptance Criteria

1. THE system SHALL store each Session as a DynamoDB item keyed by session ID, containing the full ordered list of conversation turns.
2. WHEN a conversation turn is completed, THE Orchestrator_Lambda SHALL update the DynamoDB Session item with the new user and assistant messages within 5 seconds of response completion.
3. THE DynamoDB table SHALL have a TTL attribute set to automatically expire Session items after 30 days of inactivity.
4. THE DynamoDB table SHALL have encryption at rest enabled using AWS managed keys.
5. IF a DynamoDB write fails, THEN THE Orchestrator_Lambda SHALL log the error and continue streaming the response to the user without interruption.

---

### Requirement 9: Security and IAM

**User Story:** As a system operator, I want all AWS resources to follow least-privilege IAM policies and security best practices, so that the system is protected against unauthorized access and data breaches.

#### Acceptance Criteria

1. THE Orchestrator_Lambda IAM role SHALL be granted only the specific DynamoDB actions (GetItem, PutItem, UpdateItem) on the sessions table ARN.
2. THE Orchestrator_Lambda IAM role SHALL be granted only the specific S3 actions (GetObject, PutObject) on the resume bucket ARN.
3. THE Orchestrator_Lambda IAM role SHALL be granted only the `bedrock:InvokeModelWithResponseStream` action on the specific Bedrock model ARN.
4. THE system SHALL store no secrets or credentials in Lambda environment variables in plaintext; all sensitive configuration SHALL be retrieved from AWS Secrets Manager or SSM Parameter Store at runtime.
5. THE S3 bucket SHALL block all public access.
6. WHERE Cognito authentication is enabled, THE Orchestrator_Lambda SHALL validate the JWT token from the request before processing any user message.

---

### Requirement 10: Infrastructure as Code

**User Story:** As a developer, I want all AWS infrastructure defined in AWS CDK (TypeScript), so that the system can be reliably deployed and reproduced across environments.

#### Acceptance Criteria

1. THE system SHALL define all AWS resources (Lambda, DynamoDB, S3, Amplify, IAM roles) using AWS CDK L2 or L3 constructs in TypeScript.
2. THE CDK stack SHALL accept environment-specific configuration (e.g., table names, bucket names, model IDs) via CDK context or environment variables, with no hardcoded values.
3. WHEN the CDK stack is synthesized, THE stack SHALL produce a valid CloudFormation template deployable to a target AWS account and region.
4. THE CDK stack SHALL use CDK grant methods (e.g., `table.grantReadWriteData`, `bucket.grantRead`) to assign IAM permissions rather than inline policy statements.
