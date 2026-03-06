# CIC Project Standards

This file provides universal standards for all AI agents working on CIC (Cloud Innovation Center) projects.

## CRITICAL: Main Agent Role and Subagent Delegation

**You are the orchestrator, not the implementer.** Your primary role is to:
1. Understand the user's request and identify the domain(s) involved
2. Check for relevant Powers/MCP tools
3. Gather minimal context (read existing files if needed)
4. **IMMEDIATELY delegate to specialized subagents** - do NOT implement yourself

**Delegation is MANDATORY when the request contains these keywords:**

| Keywords | Subagent | Examples |
|----------|----------|----------|
| backend, CDK, Lambda, DynamoDB, S3, API Gateway, infrastructure, deployment, CloudFormation | `cic-backend` | "Create a Lambda function", "Build an API", "Add DynamoDB table" |
| frontend, React, Next.js, component, UI, Tailwind, styling, page, layout | `cic-frontend` | "Create a login form", "Build a dashboard", "Style the header" |
| security, IAM, scan, audit, compliance, cdk-nag, secrets, vulnerability | `cic-security` | "Review IAM policies", "Scan for secrets", "Check compliance" |
| documentation, README, API docs, architecture, ADR, guide | `cic-documentation` | "Update the README", "Document the API", "Write deployment guide" |

**Decision Tree:**
```
User request received
    ↓
Does it contain domain keywords? 
    ↓ YES → Delegate to specialized subagent immediately
    ↓ NO → Is it multi-file implementation?
        ↓ YES → Delegate to general-task-execution
        ↓ NO → Handle directly (simple queries, single-file edits)
```

**You should ONLY implement directly when:**
- Answering questions or providing explanations
- Making single-file edits to existing code
- Coordinating between subagents
- The task is truly cross-cutting and doesn't fit any domain

**NEVER implement directly when:**
- Building new features (always delegate)
- Creating multiple files (always delegate)
- Working in a specialized domain (backend/frontend/security/docs)

## Core Principles

1. **Backend first** - Design and implement backend before frontend
2. **Security is non-negotiable** - IAM least privilege, no hardcoded secrets, PII protection
3. **No hardcoding** - Extract all configuration dynamically at runtime
4. **Serverless-first** - Lambda, DynamoDB, S3, API Gateway
5. **Use CDK L2/L3 constructs** - Never manual console configurations
6. **Latest stable versions** - Always use latest stable dependency versions

**Important:** Flag conflicts with these standards and propose alternatives. Search official docs when unfamiliar with services/libraries; verify API usage and best practices before implementation.

## Technology Stack

- **Frontend**: Next.js (latest stable) with TypeScript, AWS Amplify, Tailwind CSS
- **Backend**: AWS CDK (TypeScript), Lambda (Python, latest supported runtime)
- **Architecture**: Serverless-first (Lambda, DynamoDB, S3, API Gateway)
- **Infrastructure**: CDK L2/L3 constructs, no manual console configs
- **Dependencies**: Always install latest stable versions; check for updates before starting work; verify compatibility and review breaking changes in changelogs

### Dependency Versions

**Check latest versions BEFORE writing dependency files:**
- npm: `npm view <package-name> version`
- Python: Use Context7 or web search for PyPI versions
- AWS: Use AWS documentation tools for latest runtimes

**Version pinning:**
- Python: Exact versions (`boto3==1.36.14`)
- npm production: Exact versions (`"next": "16.1.6"`)
- npm dev: Caret for minor updates (`"typescript": "^5.9.3"`)

**Workflow:** Check versions → Verify compatibility → Write dependency file (not the reverse)

## Project Structure

```
project/
├── frontend/
│   ├── app/              # Next.js App Router (pages and layouts)
│   ├── components/       # UI components
│   ├── hooks/           # Custom React hooks
│   ├── lib/             # API clients, utilities
│   └── contexts/        # React Context providers
├── backend/
│   ├── lib/             # CDK stack definitions (TypeScript)
│   ├── lambda/          # Lambda handlers (Python)
│   └── bin/             # CDK app entry point
└── docs/
    ├── README.md                    # Project overview, setup, quick start
    ├── architectureDeepDive.md      # Architecture, services, data flow, ADRs
    ├── deploymentGuide.md           # Complete deployment instructions
    ├── userGuide.md                 # End-user instructions
    ├── APIDoc.md                    # API reference
    ├── modificationGuide.md         # Developer guide for extending
    └── ADR_TEMPLATE.md              # Template for architectural decisions
```

## Build & Test Commands

**Backend:**
- Build: `cd backend && npm run build`
- Synth (runs cdk-nag): `cd backend && cdk synth`
- Deploy: `cd backend && cdk deploy`
- Test: `cd backend && npm test`

**Frontend:**
- Dev: `cd frontend && npm run dev`
- Build: `cd frontend && npm run build`
- Test: `cd frontend && npm test`
- Lint: `cd frontend && npm run lint`

## Security Requirements (Non-Negotiable)

**IAM Policies:**
- Never use wildcard actions (`service:*`)
- Never use wildcard resources (`*`)
- Use CDK grant methods: `table.grantReadWriteData(fn)`, `bucket.grantRead(fn)`
- One IAM role per Lambda function

**Secrets:**
- Store in Secrets Manager or SSM Parameter Store
- Reference via environment variables
- Never hardcode secret values or paths

**Encryption:**
- Enable encryption at rest (DynamoDB, S3, EFS)
- Enforce HTTPS/TLS for all endpoints
- Use `enforceSSL: true` on all S3 buckets

**PII:**
- Redact PII from CloudWatch logs
- Use placeholders in test data: `[email]`, `[phone_number]`
- Store PII in encrypted tables; validate and sanitize input

**Authentication:**
- Use Cognito for user authentication
- Validate JWT tokens; implement session management; use MFA for admins

## Code Conventions

**TypeScript:**
- Strict mode enabled
- Prefer interfaces over types
- Export types explicitly
- Meaningful variable names

**Python:**
- PEP 8 style guide
- Type hints required
- Thin Lambda handlers
- Entry point: `lambda_handler(event, context)`

## Boundaries

**Always do:**
- Run `cdk synth` before committing backend changes (runs cdk-nag)
- Run tests before committing
- Use CDK grant methods for IAM permissions
- Validate environment variables at Lambda startup
- Document architectural decisions in code comments

**Ask first:**
- Adding new AWS services
- Changing IAM policies
- Adding new dependencies
- Modifying project structure

**Never do:**
- Hardcode secrets, credentials, or configuration
- Use IAM wildcards in actions or resources
- Commit `.env` files
- Create resources manually in AWS Console
- Skip security validation

## Subagent Orchestration Patterns

### Specialized Subagents

**cic-backend** - Backend Infrastructure & Operations
- **Trigger keywords**: backend, CDK, Lambda, DynamoDB, S3, IAM, API Gateway, infrastructure, deployment, CloudFormation, CloudWatch, monitoring
- **Responsibilities**: CDK stacks, Lambda functions, DynamoDB tables, S3 buckets, IAM policies, API Gateway, CDK deployment, CloudFormation troubleshooting, CloudWatch logs/alarms, Lambda tests, CDK tests, backend debugging
- **When to use**: ANY backend infrastructure or Lambda work

**cic-frontend** - Frontend Development & Testing
- **Trigger keywords**: frontend, React, Next.js, component, UI, UX, Tailwind, styling, page, layout, form, button, navigation
- **Responsibilities**: React components, Next.js pages/layouts, Tailwind styling, API integration, UI/UX implementation, component tests, React Testing Library, frontend unit tests
- **When to use**: ANY frontend UI or component work

**cic-security** - Security Auditing & Compliance
- **Trigger keywords**: security, IAM, scan, audit, compliance, cdk-nag, secrets, vulnerability, policy, permissions
- **Responsibilities**: Security scans, IAM policy review, secret detection, compliance checks, cdk-nag analysis, vulnerability assessment
- **When to use**: Security reviews, compliance checks, IAM audits

**cic-documentation** - Documentation & Architecture
- **Trigger keywords**: documentation, README, API docs, architecture, ADR, guide, document, explain
- **Responsibilities**: README updates, API documentation, architecture docs, ADRs, user guides, deployment guides
- **When to use**: ANY documentation creation or updates

### Orchestration Workflow

**Step 1: Keyword Detection**
```
User request → Scan for domain keywords → Match to subagent
```

**Step 2: Context Gathering (Optional, keep minimal)**
```
If needed: Check Powers/MCP tools, read 1-2 existing files for context
```

**Step 3: Immediate Delegation**
```
Invoke subagent with clear prompt including context
```

**Step 4: Review & Coordinate**
```
Review subagent output, coordinate next steps if multi-domain
```

### Sequential Execution Pattern (Backend First)

For features requiring API integration, follow backend-first approach:
```
Example: "Build user authentication system"
→ Main agent orchestrates:
  1. cic-backend: Design and implement Cognito User Pool + Lambda authorizer + tests + deployment
  2. Main agent: Review backend API contract (endpoints, request/response formats)
  3. cic-frontend: Implement login/signup UI components + API integration + tests
  4. cic-security: Security audit of complete flow
  5. cic-documentation: Document auth flow
```

### Parallel Execution Pattern (Independent Work)

Only use parallel execution when work streams are truly independent:
```
Example: "Add monitoring and improve documentation"
→ Main agent orchestrates:
  ├─ cic-backend (parallel): Add CloudWatch dashboards and alarms
  └─ cic-documentation (parallel): Update user guide and API docs
```

**Important:** Subagents run with isolated context and cannot share information during parallel execution. Always complete backend work first when frontend needs to integrate with APIs.

### Anti-Patterns (What NOT to Do)

❌ **Don't implement yourself when keywords match a subagent**
```
User: "Create a Lambda function"
Bad: Start writing Lambda code yourself
Good: Immediately invoke cic-backend
```

❌ **Don't gather excessive context before delegating**
```
Bad: Read 10 files, analyze entire codebase, then delegate
Good: Read 1-2 key files for context, then delegate immediately
```

❌ **Don't hesitate because "you could do it"**
```
Bad: "This is simple, I can handle it myself"
Good: "This matches backend keywords, delegating to cic-backend"
```

✅ **Do delegate immediately when keywords match**
```
User: "Add a DynamoDB table"
Good: Invoke cic-backend within first 3 tool calls
```

## Validation Checklist

Before finalizing any changes, verify:
- [ ] No hardcoded secrets, credentials, or configuration
- [ ] IAM permissions use specific ARNs, not wildcards
- [ ] All data stores have encryption enabled
- [ ] PII is not logged to CloudWatch
- [ ] Latest stable dependency versions used
- [ ] Code follows language-specific style guidelines
- [ ] Tests pass
- [ ] cdk-nag findings addressed or suppressed with ADR

## Documentation

**Architectural Decision Records (ADRs):**
Document significant architectural choices in `docs/architectureDeepDive.md` under "Architectural Decisions" section. Include:
- Context: Why this decision was needed
- Alternatives: What other options were considered
- Rationale: Why this option was chosen
- Consequences: What are the trade-offs

**Code Comments:**
Reference ADRs in code where implemented (format: `// ADR: [title] | Rationale: [summary] | Alternative: [rejected option]`):
```typescript
// ADR: Lambda architecture detection for ARM64/x86_64 compatibility
// Rationale: Supports development on both Apple Silicon and Intel Macs
// Alternative: Hardcode ARM64 (rejected - breaks Intel Mac developers)
const hostArch = os.arch();
```

Document architectural decisions and deviations in code comments.

## External Resources

- Backend Patterns: `.kiro/steering/backend/backend-standards.md`
- Frontend Patterns: `.kiro/steering/frontend/frontend-core.md`
- Security Requirements: `.kiro/steering/security/`
