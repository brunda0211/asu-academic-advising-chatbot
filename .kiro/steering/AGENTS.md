# CIC Project Standards

This file provides universal standards for all AI agents working on CIC (Cloud Innovation Center) projects.

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

## Subagent Orchestration

When tasks span multiple domains, the main agent should delegate to specialized agents:

**Backend Infrastructure & Operations:**
- Use `cic-backend` agent for: CDK stacks, Lambda functions, DynamoDB, S3, IAM policies, API Gateway, CDK deployment, CloudFormation troubleshooting, CloudWatch logs, Lambda tests, CDK tests, backend debugging

**Frontend Development & Testing:**
- Use `cic-frontend` agent for: React components, Next.js pages, Tailwind styling, API integration, UI/UX, component tests, React Testing Library, frontend unit tests

**Security Auditing:**
- Use `cic-security` agent for: Security scans, IAM review, secret detection, compliance checks, cdk-nag analysis

**Documentation:**
- Use `cic-documentation` agent for: README updates, API docs, architecture docs, ADRs, user guides

**Sequential Execution Pattern (Backend First):**
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

**Parallel Execution Pattern (Independent Work):**
Only use parallel execution when work streams are truly independent:
```
Example: "Add monitoring and improve documentation"
→ Main agent orchestrates:
  ├─ cic-backend (parallel): Add CloudWatch dashboards and alarms
  └─ cic-documentation (parallel): Update user guide and API docs
```

**Important:** Subagents run with isolated context and cannot share information during parallel execution. Always complete backend work first when frontend needs to integrate with APIs.

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
