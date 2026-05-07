# Design: GUIDE — ASU Academic Advising Chatbot

## Overview

This document defines the high-level architecture, component design, data flow, API contracts, and architectural decisions for the GUIDE chatbot. The system is a serverless RAG-powered academic advising chatbot deployed on AWS, using S3 Vectors + Bedrock Knowledge Base for document retrieval and Amazon Nova Lite for conversational responses streamed to a Next.js frontend.

Following backend-standards.md Lambda consolidation principle and architecture-diagrams.md guidelines, the system uses a single consolidated Lambda function, REST API V1 for streaming, and Amplify for frontend hosting.

## Architecture

```drawio
<mxGraphModel dx="1186" dy="794" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1100" pageHeight="850" math="0" shadow="0">
  <root>
    <mxCell id="0" />
    <mxCell id="1" parent="0" />

    <!-- Title -->
    <mxCell id="2" value="GUIDE — ASU Academic Advising Chatbot Architecture" style="text;html=1;fontSize=16;fontStyle=1;align=center;" vertex="1" parent="1">
      <mxGeometry x="250" y="10" width="600" height="30" as="geometry" />
    </mxCell>

    <!-- Frontend Layer -->
    <mxCell id="10" value="Frontend Layer" style="swimlane;startSize=25;fillColor=#dae8fc;strokeColor=#6c8ebf;rounded=1;" vertex="1" parent="1">
      <mxGeometry x="50" y="50" width="1000" height="120" as="geometry" />
    </mxCell>
    <mxCell id="11" value="Student&#xa;(Browser)" style="shape=mxgraph.aws4.users;verticalLabelPosition=bottom;verticalAlign=top;fillColor=#D86613;strokeColor=none;" vertex="1" parent="10">
      <mxGeometry x="30" y="35" width="50" height="50" as="geometry" />
    </mxCell>
    <mxCell id="12" value="Next.js App&#xa;(Amplify Hosting)&#xa;WEB_COMPUTE" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.amplify;fillColor=#CD2264;strokeColor=none;verticalLabelPosition=bottom;verticalAlign=top;" vertex="1" parent="10">
      <mxGeometry x="250" y="35" width="50" height="50" as="geometry" />
    </mxCell>
    <mxCell id="13" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;" edge="1" parent="10" source="11" target="12">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="14" value="HTTPS" style="edgeLabel;" vertex="1" connectable="0" parent="13">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="15" value="Questionnaire Page&#xa;→ Chat Page" style="text;html=1;fontSize=10;align=left;" vertex="1" parent="10">
      <mxGeometry x="400" y="45" width="140" height="40" as="geometry" />
    </mxCell>

    <!-- API Layer -->
    <mxCell id="20" value="API Layer" style="swimlane;startSize=25;fillColor=#fff2cc;strokeColor=#d6b656;rounded=1;" vertex="1" parent="1">
      <mxGeometry x="50" y="190" width="1000" height="120" as="geometry" />
    </mxCell>
    <mxCell id="21" value="REST API V1&#xa;(API Gateway)&#xa;/chat POST" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.api_gateway;fillColor=#E7157B;strokeColor=none;verticalLabelPosition=bottom;verticalAlign=top;" vertex="1" parent="20">
      <mxGeometry x="250" y="30" width="50" height="50" as="geometry" />
    </mxCell>
    <mxCell id="22" value="CloudWatch&#xa;Access Logs" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.cloudwatch;fillColor=#E7157B;strokeColor=none;verticalLabelPosition=bottom;verticalAlign=top;" vertex="1" parent="20">
      <mxGeometry x="700" y="30" width="50" height="50" as="geometry" />
    </mxCell>
    <mxCell id="23" value="" style="edgeStyle=orthogonalEdgeStyle;dashed=1;" edge="1" parent="20" source="21" target="22">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="24" value="Access Logging" style="edgeLabel;" vertex="1" connectable="0" parent="23">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Connection: Frontend → API -->
    <mxCell id="30" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;" edge="1" parent="1" source="12" target="21">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="31" value="HTTPS POST&#xa;(SSE Stream)" style="edgeLabel;" vertex="1" connectable="0" parent="30">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Compute Layer -->
    <mxCell id="40" value="Compute Layer" style="swimlane;startSize=25;fillColor=#d5e8d4;strokeColor=#82b366;rounded=1;" vertex="1" parent="1">
      <mxGeometry x="50" y="330" width="1000" height="120" as="geometry" />
    </mxCell>
    <mxCell id="41" value="Chat Lambda&#xa;(Python 3.12)&#xa;streamifyResponse" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.lambda;fillColor=#ED7100;strokeColor=none;verticalLabelPosition=bottom;verticalAlign=top;" vertex="1" parent="40">
      <mxGeometry x="250" y="30" width="50" height="50" as="geometry" />
    </mxCell>
    <mxCell id="42" value="IAM Role&#xa;(ChatLambdaRole)" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.role;fillColor=#DD344C;strokeColor=none;verticalLabelPosition=bottom;verticalAlign=top;" vertex="1" parent="40">
      <mxGeometry x="700" y="30" width="50" height="50" as="geometry" />
    </mxCell>
    <mxCell id="43" value="" style="edgeStyle=orthogonalEdgeStyle;dashed=1;" edge="1" parent="40" source="41" target="42">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="44" value="Assumes" style="edgeLabel;" vertex="1" connectable="0" parent="43">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Connection: API → Lambda -->
    <mxCell id="50" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;" edge="1" parent="1" source="21" target="41">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="51" value="LambdaIntegration&#xa;(Streaming)" style="edgeLabel;" vertex="1" connectable="0" parent="50">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- AI/RAG Layer -->
    <mxCell id="60" value="AI / RAG Layer" style="swimlane;startSize=25;fillColor=#e1d5e7;strokeColor=#9673a6;rounded=1;" vertex="1" parent="1">
      <mxGeometry x="50" y="470" width="1000" height="130" as="geometry" />
    </mxCell>
    <mxCell id="61" value="Bedrock&#xa;Knowledge Base&#xa;(S3_VECTORS)" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.bedrock;fillColor=#01A88D;strokeColor=none;verticalLabelPosition=bottom;verticalAlign=top;" vertex="1" parent="60">
      <mxGeometry x="150" y="35" width="50" height="50" as="geometry" />
    </mxCell>
    <mxCell id="62" value="Amazon Nova Lite&#xa;(us.amazon.nova-lite-v1:0)&#xa;Converse API" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.bedrock;fillColor=#01A88D;strokeColor=none;verticalLabelPosition=bottom;verticalAlign=top;" vertex="1" parent="60">
      <mxGeometry x="450" y="35" width="50" height="50" as="geometry" />
    </mxCell>
    <mxCell id="63" value="Titan Embed V2&#xa;(1024 dim)" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.bedrock;fillColor=#01A88D;strokeColor=none;verticalLabelPosition=bottom;verticalAlign=top;" vertex="1" parent="60">
      <mxGeometry x="750" y="35" width="50" height="50" as="geometry" />
    </mxCell>

    <!-- Connection: Lambda → KB Retrieve -->
    <mxCell id="70" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;" edge="1" parent="1" source="41" target="61">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="71" value="bedrock-agent-runtime&#xa;Retrieve API" style="edgeLabel;" vertex="1" connectable="0" parent="70">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Connection: Lambda → Nova Lite -->
    <mxCell id="72" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;" edge="1" parent="1" source="41" target="62">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="73" value="bedrock-runtime&#xa;converse_stream" style="edgeLabel;" vertex="1" connectable="0" parent="72">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Connection: KB → Titan Embed -->
    <mxCell id="74" value="" style="edgeStyle=orthogonalEdgeStyle;dashed=1;" edge="1" parent="1" source="61" target="63">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="75" value="Embedding" style="edgeLabel;" vertex="1" connectable="0" parent="74">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Storage Layer -->
    <mxCell id="80" value="Storage Layer" style="swimlane;startSize=25;fillColor=#f8cecc;strokeColor=#b85450;rounded=1;" vertex="1" parent="1">
      <mxGeometry x="50" y="620" width="1000" height="130" as="geometry" />
    </mxCell>
    <mxCell id="81" value="S3 Vectors Bucket&#xa;(Vector Store)&#xa;🔒 SSE-S3" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.s3;fillColor=#3F8624;strokeColor=none;verticalLabelPosition=bottom;verticalAlign=top;" vertex="1" parent="80">
      <mxGeometry x="150" y="35" width="50" height="50" as="geometry" />
    </mxCell>
    <mxCell id="82" value="Documents Bucket&#xa;(docs/ prefix)&#xa;🔒 SSE-S3, BPA, enforceSSL" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.s3;fillColor=#3F8624;strokeColor=none;verticalLabelPosition=bottom;verticalAlign=top;" vertex="1" parent="80">
      <mxGeometry x="450" y="35" width="50" height="50" as="geometry" />
    </mxCell>
    <mxCell id="83" value="Vector Index&#xa;(cosine, float32, 1024)" style="text;html=1;fontSize=10;align=center;" vertex="1" parent="80">
      <mxGeometry x="100" y="100" width="150" height="20" as="geometry" />
    </mxCell>

    <!-- Connection: KB → S3 Vectors -->
    <mxCell id="90" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;" edge="1" parent="1" source="61" target="81">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="91" value="Query Vectors" style="edgeLabel;" vertex="1" connectable="0" parent="90">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Connection: KB → Documents -->
    <mxCell id="92" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;" edge="1" parent="1" source="61" target="82">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
    <mxCell id="93" value="Data Source&#xa;(Ingestion)" style="edgeLabel;" vertex="1" connectable="0" parent="92">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>

    <!-- Security Boundary -->
    <mxCell id="100" value="🔒 All connections TLS/HTTPS | Encryption at rest on all storage | IAM least privilege" style="text;html=1;fontSize=10;fontStyle=2;align=center;" vertex="1" parent="1">
      <mxGeometry x="200" y="770" width="700" height="20" as="geometry" />
    </mxCell>

  </root>
</mxGraphModel>
```

> PNG version: [architecture_diagram/asu-academic-advising-chatbot-architecture.png](../../../architecture_diagram/asu-academic-advising-chatbot-architecture.png)

## Architectural Patterns

### Pattern 1: Single Consolidated Lambda (Chat + RAG Retrieval)

Following the Lambda consolidation principle from architecture-diagrams.md, the system uses a **single Lambda function** that handles the entire chat flow: input validation → KB retrieval → prompt construction → streaming response.

**Rationale:** Chat and retrieval are tightly coupled — every chat request requires retrieval. They share the same IAM permissions (bedrock-agent-runtime for retrieval, bedrock-runtime for inference), the same execution requirements (5-minute timeout, moderate memory), and the same deployment lifecycle. Separating them would add latency (extra invocation) and operational complexity with no benefit.

**No separate ingestion Lambda:** Document ingestion uses Pattern A (direct S3 upload) with KB sync triggered via CDK CustomResource or manual CLI. There is no user-facing upload endpoint, so no ingestion Lambda is needed.

### Pattern 2: REST API V1 with Lambda Streaming

REST API V1 is required for streaming responses to the frontend. Following api-gateway-patterns.md, the Lambda uses `awslambda.streamifyResponse` (Node.js wrapper) or the Python equivalent streaming pattern to write SSE chunks through the API Gateway.

**Streaming flow:**
1. Frontend sends POST to `/chat` with message + session context
2. API Gateway proxies to Chat Lambda via LambdaIntegration
3. Lambda retrieves context from KB, constructs prompt, calls `converse_stream`
4. Lambda writes SSE-formatted chunks to the response stream
5. Frontend reads chunks via ReadableStream reader + TextDecoder

### Pattern 3: Two-Page Frontend with State Handoff

The frontend uses Next.js App Router with two pages:
- **Questionnaire page** (`/`): Collects academic year, major, advising topic
- **Chat page** (`/chat`): Conversational interface with streaming responses

Questionnaire data is stored in `sessionStorage` and passed with every chat request so the Lambda can incorporate student context into the system prompt.

## Component Design

### Backend Components

| Component | Type | Purpose |
|-----------|------|---------|
| `BackendStack` | CDK Stack (TypeScript) | Single stack defining all infrastructure |
| `ChatLambda` | Lambda (Python 3.12) | Handles /chat requests: validate → retrieve → stream |
| `RestApi` | API Gateway REST V1 | Public /chat endpoint with CORS + access logging |
| `KnowledgeBase` | Bedrock CfnKnowledgeBase | S3_VECTORS storage, Titan Embed V2 |
| `DataSource` | Bedrock CfnDataSource | S3 source, docs/ prefix, fixed-size chunking |
| `VectorsBucket` | S3 Vectors Bucket | Vector store via cdk-s3-vectors |
| `VectorIndex` | S3 Vectors Index | 1024-dim cosine index |
| `DocumentsBucket` | S3 Bucket | Academic documents (PDF, TXT, HTML) |
| `AmplifyApp` | Amplify CfnApp | WEB_COMPUTE hosting for Next.js |

### Frontend Components

| Component | Type | Purpose |
|-----------|------|---------|
| `QuestionnaireForm` | Client Component | Intake form (year, major, topic) |
| `ChatInterface` | Client Component | Message list + input + streaming display |
| `MessageBubble` | Client Component | Individual message rendering (user/assistant) |
| `useChat` | Custom Hook | Chat state, streaming, session management |
| `ChatContext` | React Context | Shares questionnaire data + session across pages |

## Data Flow

### Chat Request Flow

```
1. Student fills questionnaire → data stored in sessionStorage
2. Student navigates to /chat → useChat hook initializes session
3. Student types message → POST /chat with:
   {
     "message": "What are the prerequisites for CSE 310?",
     "session_id": "session_lxyz123_abc456def789ghi",
     "context": {
       "academic_year": "Junior",
       "major": "Computer Science",
       "advising_topic": "Course Planning"
     }
   }
4. API Gateway → Chat Lambda
5. Lambda: validate input → retrieve from KB (top 5 results) → build system prompt with student context + retrieved docs → call converse_stream
6. Lambda streams SSE chunks back through API Gateway
7. Frontend appends chunks to message display in real-time
```

### Document Ingestion Flow (Pattern A — Direct Upload)

```
1. Admin uploads academic documents to Documents Bucket (docs/ prefix)
2. Admin triggers KB sync via CLI: aws bedrock-agent start-ingestion-job
3. Bedrock KB reads docs from S3 → chunks (525 tokens, 15% overlap) → embeds with Titan V2 → stores vectors in S3 Vectors
```

No Lambda is involved in ingestion. CDK deploys a CustomResource to trigger an initial sync on stack creation.

## API Specification

### POST /chat

**Endpoint:** `{api-url}/chat`
**Method:** POST
**Auth:** None (public endpoint)
**Content-Type:** `application/json`
**Response:** SSE stream (`text/event-stream`)

**Request Body:**

```json
{
  "message": "string (required, 1-2000 chars)",
  "session_id": "string (required, min 33 chars)",
  "context": {
    "academic_year": "string (Freshman|Sophomore|Junior|Senior|Graduate)",
    "major": "string (required, max 200 chars)",
    "advising_topic": "string (Course Planning|Degree Requirements|Academic Standing|General Advising)"
  }
}
```

**Response Stream (SSE format):**

```
data: {"type": "text-delta", "content": "Based on"}

data: {"type": "text-delta", "content": " the ASU catalog,"}

data: {"type": "text-delta", "content": " CSE 310 requires..."}

data: {"type": "citations", "sources": ["s3://docs/cse-catalog.pdf"]}

data: {"type": "finish", "usage": {"input_tokens": 1250, "output_tokens": 340}}
```

**Error Responses:**

| Status | Body | Condition |
|--------|------|-----------|
| 400 | `{"error": "Message is required"}` | Missing or empty message |
| 400 | `{"error": "Invalid session_id format"}` | session_id < 33 chars |
| 400 | `{"error": "Message exceeds maximum length"}` | message > 2000 chars |
| 500 | `{"error": "Internal server error"}` | KB retrieval or Bedrock failure |

**CORS Headers (all responses including errors):**

```
Access-Control-Allow-Origin: {amplifyAppUrl} | http://localhost:3000
Access-Control-Allow-Headers: Content-Type
Access-Control-Allow-Methods: POST, OPTIONS
```

## System Prompt Template

The Chat Lambda constructs a system prompt that combines the student's intake context with retrieved document content. This grounds the model's responses in ASU-specific information and the student's situation.

```
SYSTEM_PROMPT_TEMPLATE = """
You are GUIDE, an AI academic advising assistant for Arizona State University (ASU).
You help students with academic advising questions using official ASU academic documents.

## Student Context
- Academic Year: {academic_year}
- Major: {major}
- Advising Topic: {advising_topic}

## Instructions
1. Answer questions using ONLY the retrieved ASU documents below.
2. If the documents do not contain relevant information, say so clearly.
   Do not fabricate course numbers, prerequisites, policies, or deadlines.
3. Tailor your response to the student's academic year and major.
4. Be concise, specific, and cite the source document when possible.
5. For course planning questions, mention prerequisites and co-requisites.
6. For degree requirement questions, reference the specific catalog year.
7. If the student asks something outside academic advising, politely redirect.

## Retrieved ASU Documents
{retrieved_context}
"""
```

The `{retrieved_context}` placeholder is filled with the top-K results from the Bedrock Knowledge Base Retrieve API, joined with double newlines. The `{academic_year}`, `{major}`, and `{advising_topic}` placeholders come from the request's `context` object.

## Security Design

### Encryption

| Resource | At Rest | In Transit |
|----------|---------|------------|
| Documents Bucket | SSE-S3 | enforceSSL: true (TLS) |
| S3 Vectors Bucket | S3 Vectors managed encryption | TLS |
| API Gateway | N/A | HTTPS only |
| Amplify | Managed | HTTPS only |
| Bedrock API calls | N/A | TLS |

### IAM Roles

**ChatLambdaRole** — single role for the Chat Lambda with least-privilege permissions:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `bedrock:Retrieve` | `arn:aws:bedrock:{region}:{account}:knowledge-base/{kb-id}` | KB retrieval |
| `bedrock:InvokeModelWithResponseStream` | `arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite-v1:0` | Nova Lite streaming |
| `bedrock:InvokeModelWithResponseStream` | `arn:aws:bedrock:us-east-2::foundation-model/amazon.nova-lite-v1:0` | Cross-region routing |
| `bedrock:InvokeModelWithResponseStream` | `arn:aws:bedrock:us-west-2::foundation-model/amazon.nova-lite-v1:0` | Cross-region routing |

**KnowledgeBaseRole** — assumed by `bedrock.amazonaws.com`:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `s3vectors:*` | `*` (suppressed with cdk-nag ADR) | S3 Vectors operations |
| `bedrock:InvokeModel` | Titan Embed V2 ARN | Document embedding |
| `s3:GetObject`, `s3:ListBucket` | Documents Bucket ARN | Read source documents |

### Input Validation & Prompt Injection Protection

- Validate `message` length (1–2000 characters) and character set
- Validate `session_id` format (minimum 33 characters)
- Validate `context` fields against allowed enum values
- System prompt uses clear delimiters between instructions and user content
- Model instructed to ignore conflicting instructions in user content
- No user input is interpolated into system prompt instructions — only into designated placeholders

### No Authentication

Per requirements, this is a public-facing chatbot with no authentication. The API Gateway `/chat` endpoint has no authorizer. cdk-nag findings for APIG4 and COG4 are suppressed with ADR justification.

## Error Handling

### Lambda Error Strategy

| Error Type | Handling | User-Facing Response |
|------------|----------|---------------------|
| Missing/invalid `message` | Return 400 immediately | `{"error": "Message is required"}` |
| Invalid `session_id` | Return 400 immediately | `{"error": "Invalid session_id format"}` |
| Invalid `context` fields | Return 400 with detail | `{"error": "Invalid academic_year value"}` |
| KB retrieval failure | Log error, proceed without context | Stream response with disclaimer: "I couldn't access my knowledge base..." |
| Bedrock `converse_stream` failure | Log error, return 500 | `{"error": "Internal server error"}` |
| Bedrock throttling | Log, return 429 | `{"error": "Service busy, please try again"}` |
| Timeout (>5 min) | Lambda timeout | API Gateway returns 504 |

### Frontend Error Strategy

Following frontend-integration-patterns.md:

| Error Type | Handling | User Experience |
|------------|----------|----------------|
| Network error | Catch in fetch, show message | "Network error. Please check your connection." |
| Timeout (30s AbortController) | Abort request | "Request timed out. Please try again." |
| 4xx error | Parse error body, display | Show specific error message from API |
| 5xx error | Retry with exponential backoff (max 3) | "Server error. Retrying..." then "Please try again later." |
| Stream interruption | Detect incomplete stream | Show partial response + "Response was interrupted. Try again." |

## Correctness Properties

The following properties must hold across all executions of the system. They are derived from the functional requirements and acceptance criteria, consolidated to eliminate redundancy.

### Input Validation Properties (P1–P6)

**Property 1: Message Presence**
*For any* chat request with an empty or missing `message` field, the system SHALL return HTTP 400 with an error message and SHALL NOT invoke Bedrock.
**Validates: FR-CHAT-1, FR-CHAT-2**

**Property 2: Message Length Bound**
*For any* chat request where `message` exceeds 2000 characters, the system SHALL return HTTP 400 and SHALL NOT invoke Bedrock.
**Validates: FR-CHAT-1**

**Property 3: Session ID Format**
*For any* chat request where `session_id` is missing or shorter than 33 characters, the system SHALL return HTTP 400.
**Validates: FR-SESSION-1**

**Property 4: Academic Year Enum**
*For any* chat request where `context.academic_year` is not one of the allowed enum values (Freshman, Sophomore, Junior, Senior, Graduate), the system SHALL return HTTP 400.
**Validates: FR-QUESTIONNAIRE-1**

**Property 5: Major Field Presence**
*For any* chat request where `context.major` is empty or exceeds 200 characters, the system SHALL return HTTP 400.
**Validates: FR-QUESTIONNAIRE-1**

**Property 6: Advising Topic Enum**
*For any* chat request where `context.advising_topic` is not one of the allowed enum values, the system SHALL return HTTP 400.
**Validates: FR-QUESTIONNAIRE-1**

### RAG Retrieval Properties (P7–P12)

**Property 7: Retrieval Invocation**
*For any* valid chat request, the system SHALL invoke the Bedrock Knowledge Base Retrieve API before calling the inference model.
**Validates: FR-RAG-1**

**Property 8: Retrieval Result Count**
*For any* KB retrieval call, the system SHALL request exactly `NUM_KB_RESULTS` (default 5) results.
**Validates: FR-RAG-1**

**Property 9: Context Injection**
*For any* valid chat request where KB retrieval returns results, the retrieved text SHALL appear in the system prompt sent to the inference model.
**Validates: FR-RAG-1, FR-RAG-2**

**Property 10: Empty Retrieval Graceful Handling**
*For any* valid chat request where KB retrieval returns zero results, the system SHALL still invoke the inference model with the student context (without retrieved documents) and SHALL NOT return an error.
**Validates: FR-RAG-3**

**Property 11: Retrieval Failure Resilience**
*For any* valid chat request where KB retrieval throws an exception, the system SHALL log the error and proceed to invoke the inference model without retrieved context, rather than returning a 500 error.
**Validates: FR-RAG-3, NFR-RELIABILITY-1**

**Property 12: Citation Extraction**
*For any* KB retrieval that returns results with S3 location metadata, the system SHALL extract and include source citations in the response stream.
**Validates: FR-RAG-2**

### Prompt Construction Properties (P13–P17)

**Property 13: Student Context Inclusion**
*For any* valid chat request, the system prompt sent to the inference model SHALL contain the student's `academic_year`, `major`, and `advising_topic` values.
**Validates: FR-QUESTIONNAIRE-2, FR-CHAT-2**

**Property 14: System Prompt Structure**
*For any* inference call, the system prompt SHALL contain the instruction block, student context block, and retrieved documents block in that order, with clear delimiters between sections.
**Validates: FR-CHAT-2, NFR-SECURITY-3**

**Property 15: No User Input in Instructions**
*For any* inference call, user-provided values (message, academic_year, major, advising_topic) SHALL only appear in designated placeholder positions, never interpolated into the instruction text.
**Validates: NFR-SECURITY-3**

**Property 16: Model ID Correctness**
*For any* inference call, the model ID SHALL be `us.amazon.nova-lite-v1:0` (the cross-region inference profile).
**Validates: FR-CHAT-3**

**Property 17: Inference Config Bounds**
*For any* inference call, `maxTokens` SHALL be ≤ 4096 and `temperature` SHALL be between 0.0 and 1.0 inclusive.
**Validates: FR-CHAT-3**

### Streaming Properties (P18–P23)

**Property 18: SSE Format Compliance**
*For any* streamed response chunk, the output SHALL conform to SSE format: `data: {json}\n\n`.
**Validates: FR-STREAM-1**

**Property 19: Stream Termination**
*For any* completed streaming response, the final event SHALL be of type `finish` and the stream SHALL be closed.
**Validates: FR-STREAM-1**

**Property 20: Chunk Content Type**
*For any* text-delta event in the stream, the `content` field SHALL be a non-empty string.
**Validates: FR-STREAM-1**

**Property 21: Stream Error Event**
*For any* error that occurs during streaming after the response has started, the system SHALL emit an error event in SSE format before closing the stream.
**Validates: FR-STREAM-2**

**Property 22: No Empty Streams**
*For any* valid chat request that reaches the inference model, the system SHALL emit at least one text-delta event before the finish event.
**Validates: FR-STREAM-1, FR-CHAT-3**

**Property 23: CORS Headers on All Responses**
*For any* response from the /chat endpoint (success, error, or OPTIONS preflight), the response SHALL include the correct CORS headers.
**Validates: NFR-CORS-1**

### Session Properties (P24–P26)

**Property 24: Session ID Passthrough**
*For any* valid chat request, the `session_id` from the request SHALL be available in the Lambda execution context for logging and correlation.
**Validates: FR-SESSION-1**

**Property 25: Session ID Generation**
*For any* new browser session, the frontend SHALL generate a session ID of at least 33 characters using the format `session_{timestamp}_{random}`.
**Validates: FR-SESSION-1**

**Property 26: Session Persistence**
*For any* active browser tab, the session ID SHALL persist in sessionStorage across page navigations (questionnaire → chat) and be cleared when the tab is closed.
**Validates: FR-SESSION-2**

### Infrastructure Properties (P27–P32)

**Property 27: S3 Encryption at Rest**
*For any* S3 bucket in the stack, encryption at rest SHALL be enabled (SSE-S3 minimum).
**Validates: NFR-SECURITY-1**

**Property 28: S3 SSL Enforcement**
*For any* S3 bucket in the stack, `enforceSSL` SHALL be true, denying non-HTTPS access.
**Validates: NFR-SECURITY-1**

**Property 29: S3 Block Public Access**
*For any* S3 bucket in the stack (excluding S3 Vectors managed bucket), Block Public Access SHALL be enabled.
**Validates: NFR-SECURITY-1**

**Property 30: API Gateway Access Logging**
*For any* API Gateway stage, access logging to CloudWatch SHALL be enabled.
**Validates: NFR-OBSERVABILITY-1**

**Property 31: Lambda Structured Logging**
*For any* Lambda log entry, the output SHALL be valid JSON with fields: `timestamp`, `level`, `action`, and `request_id`.
**Validates: NFR-OBSERVABILITY-1**

**Property 32: No PII in Logs**
*For any* Lambda log entry, the student's message content SHALL NOT be logged in full. Only a truncated hash or length indicator is permitted.
**Validates: NFR-SECURITY-2**

### Frontend Properties (P33–P38)

**Property 33: Questionnaire Completion Gate**
*For any* navigation to the /chat page, IF the questionnaire data is not present in sessionStorage, the user SHALL be redirected to the questionnaire page.
**Validates: FR-QUESTIONNAIRE-3**

**Property 34: Streaming Display**
*For any* streaming response, the chat interface SHALL display text incrementally as chunks arrive, not wait for the complete response.
**Validates: FR-STREAM-3**

**Property 35: Loading State**
*For any* pending chat request, the UI SHALL display a loading indicator and disable the send button.
**Validates: FR-CHAT-4**

**Property 36: Error Display**
*For any* failed chat request, the UI SHALL display a user-friendly error message with a retry option.
**Validates: FR-CHAT-5**

**Property 37: Input Sanitization**
*For any* user message submitted from the frontend, HTML tags SHALL be stripped and the message SHALL be trimmed before sending.
**Validates: NFR-SECURITY-3**

**Property 38: Responsive Layout**
*For any* viewport width from 320px to 1920px, the chat interface SHALL be usable without horizontal scrolling.
**Validates: NFR-ACCESSIBILITY-1**

### Property Reflection

These 38 properties consolidate the acceptance criteria from the requirements document into universal invariants. Input validation properties (P1–P6) cover all request validation paths. RAG properties (P7–P12) ensure retrieval is always attempted and failures are handled gracefully. Prompt properties (P13–P17) guarantee the system prompt is correctly constructed with student context. Streaming properties (P18–P23) verify SSE compliance end-to-end. Session properties (P24–P26) ensure session continuity. Infrastructure properties (P27–P32) enforce security baselines. Frontend properties (P33–P38) verify the user experience contract.

## Testing Strategy

### Dual Approach: Unit Tests + Property-Based Tests

The testing strategy combines traditional unit tests for specific scenarios with property-based tests (PBT) for universal correctness invariants.

**Unit tests** verify specific input/output pairs and edge cases. They are deterministic and fast.

**Property-based tests** verify that correctness properties hold across randomly generated inputs. They catch edge cases that hand-written tests miss.

### Unit Test Coverage

| Component | Framework | Focus Areas |
|-----------|-----------|-------------|
| Chat Lambda (Python) | pytest | Input validation, prompt construction, error handling, CORS headers |
| CDK Stack (TypeScript) | Jest + CDK assertions | Resource creation, IAM policies, environment variables, cdk-nag compliance |
| Frontend hooks (TypeScript) | Jest + React Testing Library | useChat state transitions, session management, streaming parsing |
| Frontend components (TypeScript) | Jest + React Testing Library | Questionnaire validation, chat rendering, error display, accessibility |

### Property-Based Test Configuration

**Backend (Python):** Use `hypothesis` library with minimum 100 examples per property.

```
# pytest.ini or conftest.py
hypothesis:
  max_examples: 100
  deadline: 5000  # ms, generous for Bedrock calls in integration tests
```

**Frontend (TypeScript):** Use `fast-check` library with minimum 100 runs per property.

```
// jest.config.js or test setup
fc.configureGlobal({ numRuns: 100 });
```

### Property Test Mapping

| Property | Test Type | Description |
|----------|-----------|-------------|
| P1–P6 | PBT (hypothesis) | Generate random invalid inputs, verify 400 response |
| P7–P9 | Unit + Integration | Mock KB client, verify retrieval called with correct params |
| P10–P11 | Unit | Mock empty/failed retrieval, verify graceful handling |
| P13–P15 | PBT (hypothesis) | Generate random context values, verify prompt structure |
| P18–P20 | Unit | Mock converse_stream, verify SSE format |
| P23 | PBT (hypothesis) | Generate random request scenarios, verify CORS headers present |
| P25 | PBT (fast-check) | Generate random timestamps, verify session ID format |
| P27–P29 | CDK assertions | Verify S3 bucket properties in synthesized template |
| P30 | CDK assertions | Verify API Gateway access logging configured |
| P33 | Unit (RTL) | Verify redirect when sessionStorage empty |
| P37 | PBT (fast-check) | Generate strings with HTML tags, verify sanitization |

### Test Tagging Convention

Tag each property test with a comment identifying the property and validated requirements:

```python
# Property 1: Message Presence
# Validates: FR-CHAT-1, FR-CHAT-2
@given(st.text(max_size=0) | st.none())
def test_empty_message_returns_400(message):
    ...
```

```typescript
// Property 25: Session ID Generation
// Validates: FR-SESSION-1
fc.assert(fc.property(fc.nat(), (timestamp) => {
  const id = generateSessionId();
  return id.length >= 33 && id.startsWith('session_');
}));
```

## Deployment Architecture

### CDK Stack Structure

Single `BackendStack` containing all resources. Following backend-standards.md, the stack uses CDK context variables for deployment-specific configuration.

**Required CDK Context Variables:**

| Variable | Purpose | Example |
|----------|---------|---------|
| `githubToken` | Amplify GitHub OAuth token | SSM Parameter Store name |
| `githubOwner` | GitHub repository owner | `my-org` |
| `githubRepo` | GitHub repository name | `asu-advising-chatbot` |
| `projectPrefix` | Resource naming prefix | `asu-guide` |

**Resource Creation Order:**

1. Amplify App (early — needed for CORS URL)
2. Documents Bucket (S3, enforceSSL, BPA)
3. S3 Vectors Bucket + Vector Index (cdk-s3-vectors)
4. Knowledge Base Role + Knowledge Base + Data Source
5. Chat Lambda + IAM Role
6. REST API V1 + /chat resource + CORS
7. Amplify Branch (with NEXT_PUBLIC_API_URL env var)
8. AwsCustomResource (trigger Amplify build)
9. CustomResource (trigger initial KB sync)
10. CfnOutputs (API URL, Amplify URL, KB ID)

### Environment Variables Passed to Lambda

| Variable | Source | Purpose |
|----------|--------|---------|
| `KNOWLEDGE_BASE_ID` | `knowledgeBase.attrKnowledgeBaseId` | KB retrieval |
| `MODEL_ID` | `us.amazon.nova-lite-v1:0` | Inference model |
| `NUM_KB_RESULTS` | `5` | Number of retrieval results |
| `MAX_TOKENS` | `4096` | Response length limit |
| `TEMPERATURE` | `0.7` | Response creativity |
| `CORS_ALLOWED_ORIGIN` | `amplifyAppUrl` | CORS header value |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

### Environment Variables Passed to Amplify

| Variable | Source | Purpose |
|----------|--------|---------|
| `NEXT_PUBLIC_API_URL` | `api.url + 'chat'` | Chat endpoint URL |
| `AMPLIFY_MONOREPO_APP_ROOT` | `frontend` | Monorepo app root |

## Architectural Decision Records

### ADR-1: Single Chat Lambda vs Separate Retrieval + Inference Lambdas

**Context:** The system needs to retrieve documents from a Knowledge Base and then invoke an inference model. These could be separate Lambda functions or combined.

**Alternatives:**
1. Single Lambda handling retrieval + inference (chosen)
2. Separate Retrieval Lambda + Inference Lambda with API Gateway routing
3. Step Functions orchestrating two Lambdas

**Decision:** Single Lambda.

**Rationale:** Retrieval and inference are sequential operations on every request — there is no scenario where one runs without the other. They share the same IAM permissions (bedrock-agent-runtime, bedrock-runtime), the same timeout requirements (5 min), and the same deployment lifecycle. Separating them adds inter-Lambda latency, doubles cold start risk, and increases operational complexity. Following architecture-diagrams.md Lambda consolidation principle: "If work can be done in 2 Lambda functions, do NOT create 4 or 5."

**Consequences:** Single Lambda has a broader IAM role (both retrieval and inference permissions). This is acceptable because both permission sets are narrowly scoped to specific resource ARNs.

---

### ADR-2: REST API V1 over HTTP API V2

**Context:** The frontend needs streaming responses from the Lambda. API Gateway offers two types: REST API V1 and HTTP API V2.

**Alternatives:**
1. REST API V1 with Lambda streaming (chosen)
2. HTTP API V2 (cheaper but limited streaming support)
3. Lambda Function URL (no API Gateway management features)

**Decision:** REST API V1.

**Rationale:** REST API V1 supports response streaming with Lambda integrations (as of Nov 19, 2025), per api-gateway-patterns.md. HTTP API V2 has limited streaming support for Lambda backends. Lambda Function URLs would work but lack access logging, request validation, and centralized API management. The cost difference ($3.50 vs $1.00 per million requests) is negligible for an academic advising chatbot's expected traffic volume.

**Consequences:** Slightly higher per-request cost. Gain access logging, CORS preflight handling, and future extensibility (rate limiting, API keys if needed).

---

### ADR-3: No Ingestion Lambda — Direct S3 Upload (Pattern A)

**Context:** Academic documents need to be loaded into the Knowledge Base. The s3-vectors-rag-chatbot.md steering file describes four ingestion patterns (A–D).

**Alternatives:**
1. Pattern A: Direct S3 upload + manual/automated KB sync (chosen)
2. Pattern B: Web scraper Lambda
3. Pattern C: Document processing pipeline with Textract
4. Pattern D: EventBridge + SQS batch

**Decision:** Pattern A — Direct S3 upload.

**Rationale:** ASU academic documents are pre-existing PDFs, HTML pages, and text files that are uploaded infrequently (semester updates). Bedrock KB natively parses these formats. There is no need for web scraping, OCR, or real-time ingestion. A CDK CustomResource triggers the initial KB sync on deployment. Subsequent syncs are triggered manually via CLI or could be automated with an S3 event notification in a future iteration.

**Consequences:** No automated ingestion pipeline. Admins must manually upload documents and trigger sync. This is acceptable for the initial scope and can be enhanced later without architectural changes.

---

### ADR-4: Two-Page Frontend (Questionnaire → Chat) vs Single Page

**Context:** Students must complete an intake questionnaire before chatting. This could be a separate page or a section within the chat page.

**Alternatives:**
1. Two separate pages with App Router navigation (chosen)
2. Single page with conditional rendering (questionnaire section → chat section)
3. Modal/dialog for questionnaire on the chat page

**Decision:** Two pages.

**Rationale:** Separate pages provide a clearer user flow, better URL semantics (`/` for intake, `/chat` for conversation), and simpler component logic. The questionnaire page is a focused form without chat complexity. The chat page is a focused conversation interface. Data passes between them via sessionStorage, which persists across same-tab navigations. This also allows the chat page to enforce the questionnaire completion gate (Property 33) via a simple sessionStorage check.

**Consequences:** Requires sessionStorage for state handoff. Page navigation adds a brief transition. The tradeoff is cleaner separation of concerns and simpler component code.

---

### ADR-5: Amazon Nova Lite over Claude or Nova Pro

**Context:** The system needs a foundation model for generating chat responses. Multiple models are available in Bedrock.

**Alternatives:**
1. Amazon Nova Lite — `us.amazon.nova-lite-v1:0` (chosen)
2. Amazon Nova Pro — `us.amazon.nova-pro-v1:0`
3. Anthropic Claude 3.5 Sonnet
4. Anthropic Claude 3 Haiku

**Decision:** Amazon Nova Lite.

**Rationale:** Per backend-standards.md model selection priority, AWS-owned models are preferred because they require no marketplace subscription. Nova Lite is the fastest and cheapest AWS-owned model, suitable for academic advising Q&A where responses are grounded in retrieved documents (reducing the need for advanced reasoning). The cross-region inference profile (`us.` prefix) provides high availability across us-east-1, us-east-2, and us-west-2. If response quality proves insufficient during testing, upgrading to Nova Pro requires only changing the `MODEL_ID` environment variable.

**Consequences:** Lower cost and faster responses. Potentially less nuanced reasoning than Nova Pro or Claude. Mitigated by RAG grounding — the model primarily synthesizes retrieved content rather than reasoning from scratch.

---

### ADR-6: sessionStorage over localStorage for Session Management

**Context:** The frontend needs to store the session ID and questionnaire data across page navigations within a single visit.

**Alternatives:**
1. sessionStorage (chosen)
2. localStorage (persistent across sessions)
3. React Context only (lost on page refresh)
4. URL query parameters

**Decision:** sessionStorage.

**Rationale:** Per frontend-integration-api.md, sessionStorage is recommended for chat apps because it is cleared when the tab is closed, ensuring each visit starts fresh. This aligns with the requirement for no persistent chat history. localStorage would persist data across visits, which is undesirable. React Context alone would lose state on page refresh during the questionnaire → chat transition. URL parameters would expose student data in the address bar.

**Consequences:** Data is lost if the user refreshes the chat page (they would need to re-complete the questionnaire). This is acceptable for the simple two-page flow and reinforces the "no persistent history" requirement.

---

### ADR-7: cdk-nag Suppressions for Public Endpoint and S3 Vectors

**Context:** cdk-nag AwsSolutions checks will flag the public /chat endpoint (no auth) and S3 Vectors wildcard permissions.

**Suppressions required:**

| Finding | Resource | Reason |
|---------|----------|--------|
| AwsSolutions-APIG4 | /chat POST method | Public academic advising endpoint — no authentication by design (requirements specify no auth) |
| AwsSolutions-COG4 | /chat POST method | No Cognito authorizer — public endpoint by design |
| AwsSolutions-IAM5 | KnowledgeBaseRole | S3 Vectors resource-level ARNs not yet documented. Will tighten when available. |
| AwsSolutions-IAM5 | cdk-s3-vectors constructs | Internal construct managed by cdk-s3-vectors package |
| AwsSolutions-IAM4 | cdk-s3-vectors constructs | Internal construct managed by cdk-s3-vectors package |
| AwsSolutions-L1 | cdk-s3-vectors constructs | Internal construct managed by cdk-s3-vectors package |
| AwsSolutions-IAM5 | ChatLambdaRole (Bedrock cross-region) | Cross-region inference profile requires permissions for us-east-1, us-east-2, us-west-2 |
