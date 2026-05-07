# ASU Academic Advising Chatbot

An AI-powered chatbot that answers Arizona State University academic advising questions using a Retrieval-Augmented Generation (RAG) architecture. Students can ask about degree requirements, course catalogs, academic standing policies, and more — and get accurate, source-backed answers in real time.

---

## High Level Architecture

The chatbot uses a serverless RAG pipeline on AWS:

1. **Frontend** — Next.js (App Router) hosted on AWS Amplify with SSR
2. **API** — API Gateway REST API routes requests to a Lambda function
3. **Chat Lambda** — Validates input, retrieves relevant documents from Bedrock Knowledge Base, and streams responses using Amazon Nova Lite
4. **Knowledge Base** — Bedrock Knowledge Base with S3 Vectors storage and Titan Embed V2 embeddings
5. **Document Store** — S3 bucket holding academic advising documents (course catalogs, policies, degree requirements)

### AWS Services Used

- AWS Lambda (Python 3.13)
- Amazon API Gateway (REST API V1)
- Amazon Bedrock (Nova Lite for generation, Titan Embed V2 for embeddings)
- Amazon Bedrock Knowledge Base with S3 Vectors
- Amazon S3 (document storage + vector store)
- AWS Amplify (frontend hosting with SSR)
- AWS CDK (infrastructure as code)

---

## Prerequisites

- AWS Account with Bedrock model access enabled
- AWS CLI v2 configured with credentials
- Node.js 18+ and npm
- AWS CDK v2 (`npm install -g aws-cdk`)
- Git
- A GitHub account (for Amplify deployment)

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/brunda0211/asu-academic-advising-chatbot.git
cd asu-academic-advising-chatbot
cd backend && npm install
cd ../frontend && npm install
```

### 2. Deploy the backend

```bash
cd backend
cdk deploy \
  -c githubToken=ghp_YOUR_TOKEN \
  -c githubOwner=brunda0211 \
  -c githubRepo=asu-academic-advising-chatbot \
  -c projectPrefix=asu-advising
```

### 3. Upload documents for the knowledge base

```bash
aws s3 cp backend/sample-docs/ s3://asu-advising-documents-<ACCOUNT_ID>-<REGION>/docs/ --recursive
```

### 4. Access the chatbot

After deployment, the Amplify URL is printed in the CDK outputs:
```
AmplifyUrl = https://main.<app-id>.amplifyapp.com
```

For local development:
```bash
cd frontend
npm run dev
```
Then open http://localhost:3000

---

## Project Structure

```
├── backend/
│   ├── bin/              # CDK app entry point
│   ├── lambda/
│   │   └── chat/         # Chat Lambda handler (Python)
│   ├── lib/
│   │   └── backend-stack.ts  # CDK stack definition
│   ├── sample-docs/      # Sample academic advising documents
│   └── package.json
├── frontend/
│   ├── app/              # Next.js App Router pages
│   ├── components/       # React components (ChatInterface, MessageBubble)
│   ├── hooks/            # Custom hooks (useChat)
│   ├── contexts/         # React Context (ChatContext)
│   ├── lib/              # API client, session management
│   └── package.json
├── docs/                 # Documentation
└── README.md
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Deployment Guide](./docs/deploymentGuide.md) | Full deployment instructions |
| [User Guide](./docs/userGuide.md) | How to use the chatbot |
| [API Documentation](./docs/APIDoc.md) | API reference |
| [Architecture Deep Dive](./docs/architectureDeepDive.md) | Detailed architecture and ADRs |
| [Modification Guide](./docs/modificationGuide.md) | Guide for extending the project |

---

## Troubleshooting

**CDK deploy fails with "Missing required CDK context variable"**
→ Provide all four context variables (`githubToken`, `githubOwner`, `githubRepo`, `projectPrefix`) via `-c` flags.

**Chatbot returns empty responses**
→ Upload documents to the S3 bucket's `docs/` prefix and trigger a knowledge base sync.

**CORS errors in browser**
→ The Amplify URL and `http://localhost:3000` are automatically configured as allowed origins.

---

## License

This project is licensed under the MIT License — see the [LICENSE](./LICENSE) file for details.
