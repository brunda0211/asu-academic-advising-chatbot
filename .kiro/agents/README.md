# CIC Subagents

Specialized AI agents for CIC (Cloud Innovation Center) project development. Each agent is configured with domain-specific knowledge and tools to provide expert assistance.

**Universal Standards**: All agents automatically inherit CIC standards from `AGENTS.md`, which provides core principles, security requirements, code conventions, and orchestration patterns.

## Available Subagents

### 1. CIC Backend Agent
**File:** `cic-backend.md`  
**Purpose:** AWS CDK infrastructure, Lambda development, deployment, and backend testing

**Specialization:**
- AWS CDK stack design (TypeScript)
- Lambda function development (Python)
- DynamoDB and S3 configuration
- API Gateway and Function URLs
- IAM policies with least privilege
- CDK deployment and CloudFormation troubleshooting
- CloudWatch logs analysis and debugging
- Lambda and CDK testing with pytest and Jest

**Use Cases:**
```
"Design and implement a DynamoDB table for user profiles with CDK"
"Create a Lambda function that processes S3 uploads and stores metadata"
"Deploy the CDK stack and troubleshoot any CloudFormation errors"
"Write unit tests for the Lambda handler function"
"Debug Lambda timeout issues using CloudWatch logs"
"Implement a Step Functions workflow for document processing"
```

---

### 2. CIC Frontend Agent
**File:** `cic-frontend.md`  
**Purpose:** Next.js frontend development and testing

**Specialization:**
- Next.js with App Router
- React components with TypeScript
- Tailwind CSS styling
- API integration and AWS SDK usage
- State management and error handling
- React Testing Library for component tests
- Jest unit tests for hooks and utilities

**Use Cases:**
```
"Create a responsive dashboard component with Tailwind"
"Build a file upload form with progress indicator and S3 integration"
"Implement a chat interface with streaming responses from Bedrock"
"Write React Testing Library tests for the login component"
"Add dark mode support to the application"
"Create an authentication flow with Cognito"
```

---

### 3. CIC Security Agent
**File:** `cic-security.md`  
**Purpose:** Security auditing and compliance

**Specialization:**
- IAM policy review (no wildcards, least privilege)
- Secrets management validation
- Encryption verification
- PII protection auditing
- cdk-nag findings analysis
- Compliance documentation review

**Important:** This agent is READ-ONLY. It identifies issues but does not fix them.

**Use Cases:**
```
"Audit the backend for security violations"
"Check for hardcoded secrets in the codebase"
"Verify all IAM policies follow least privilege"
"Generate a security compliance report"
"Review encryption configuration across all services"
```

---

### 4. CIC Documentation Agent
**File:** `cic-documentation.md`  
**Purpose:** Documentation creation and maintenance

**Specialization:**
- Architecture documentation
- Architectural Decision Records (ADRs)
- API documentation
- Deployment guides
- User guides
- Security documentation (SECURITY.md)
- Threat modeling

**Use Cases:**
```
"Document the new authentication flow in architectureDeepDive.md"
"Create an ADR for choosing DynamoDB over RDS"
"Generate API documentation from Lambda function signatures"
"Update the deployment guide with new CDK context variables"
"Create a threat model for the S3 bucket configuration"
```

---

## How Subagents Work

### Automatic Selection

Kiro IDE automatically selects the right agent based on keywords in your task description:

**Backend Agent** triggers on:
- CDK, CloudFormation, infrastructure, stack
- Lambda, function, handler, Python
- DynamoDB, table, database, S3, bucket
- IAM, policy, permissions
- Deployment, CloudWatch, debugging
- Backend tests, pytest, Lambda tests

**Frontend Agent** triggers on:
- React, component, JSX, TSX
- Next.js, page, route, layout
- Tailwind, CSS, styling
- UI, interface, form
- Component tests, React Testing Library

**Security Agent** triggers on:
- Security, audit, scan
- IAM review, policy check
- Secret, credential, hardcoded
- Compliance, cdk-nag

**Documentation Agent** triggers on:
- README, API docs
- Architecture docs, ADRs
- User guides, deployment guides
- Documentation updates

### Orchestration Pattern

For complex features, the main agent orchestrates multiple subagents:

```
User: "Build user authentication system"

Main agent orchestrates:
├─ cic-backend (parallel): Cognito User Pool + Lambda authorizer + tests + deployment
└─ cic-frontend (parallel): Login/signup UI components + tests
→ cic-security: Security audit
→ cic-documentation: Document auth flow
```

---

## Common Workflows

### Pattern 1: Full-Stack Feature Development

**Scenario:** "Build a user profile management feature"

**Workflow:**
1. **Backend Agent** (parallel): Design DynamoDB table, create CRUD Lambda functions, write tests, deploy
2. **Frontend Agent** (parallel): Create profile UI components and forms, write component tests
3. **Security Agent**: Review IAM policies and check for security issues
4. **Documentation Agent**: Document the feature in architecture and user guides

---

### Pattern 2: Security Audit Workflow

**Scenario:** "Perform comprehensive security review before demo"

**Workflow:**
1. **Security Agent**: Scan entire codebase for security issues
2. **Backend Agent**: Fix IAM policy violations and encryption issues
3. **Frontend Agent**: Fix any client-side security issues
4. **Security Agent**: Re-scan to verify fixes
5. **Documentation Agent**: Document security measures in SECURITY.md

---

### Pattern 3: Rapid Prototyping Workflow

**Scenario:** "Build a chatbot demo in 2 hours"

**Workflow:**
1. **Backend Agent** + **Frontend Agent** (parallel):
   - Backend: Lambda + Bedrock integration + deployment
   - Frontend: Chat UI components
2. **Documentation Agent**: Create quick-start guide

---

### Pattern 4: Debugging & Troubleshooting Workflow

**Scenario:** "Lambda function is timing out in production"

**Workflow:**
1. **Backend Agent**: Check CloudWatch logs and metrics
2. **Backend Agent**: Analyze Lambda code for performance issues
3. **Backend Agent**: Implement fixes (optimize queries, add caching)
4. **Backend Agent**: Write performance tests and redeploy
5. **Documentation Agent**: Document the issue and solution

---

## Best Practices

### When to Use Subagents

**Use subagents when:**
- Task requires specialized domain knowledge (backend vs frontend)
- Working on large features that span multiple domains
- Need to parallelize independent work streams
- Performing specialized audits (security)

**Don't use subagents when:**
- Task is simple and single-domain
- Context is already small and manageable
- Quick iterations are needed

### Delegation Guidelines

1. **Be specific**: Give subagents clear, well-defined tasks
2. **Provide context**: Include necessary file paths, requirements, constraints
3. **Verify output**: Review subagent work before proceeding
4. **Iterate**: Use subagents multiple times if needed
5. **Document**: Have subagents document their work

### Parallel Execution

Subagents can work simultaneously on independent tasks:

```
Parallel workflow:
- Backend Agent: Implement API endpoints + tests + deployment
- Frontend Agent: Build UI components + tests

Sequential workflow:
- Security Agent: Identify issues
- Backend Agent: Fix backend issues
- Frontend Agent: Fix frontend issues
- Security Agent: Verify fixes
```

---

## Subagent Configuration

Each subagent is configured with:

### Universal Standards (AGENTS.md)
All agents automatically inherit:
- Core CIC principles
- Technology stack requirements
- Security requirements (non-negotiable)
- Code conventions (TypeScript, Python)
- Build and test commands
- Boundaries (always do, ask first, never do)
- Orchestration patterns

### Domain-Specific Steering Files
Additional guidance loads based on file patterns:
- **Backend work**: backend-standards.md, security-iam-secrets.md, security-data-encryption.md, security-operations.md, security-code-dependencies.md
- **Frontend work**: frontend-core.md, frontend-styling.md, frontend-state-i18n.md, frontend-integration-api.md, frontend-integration-aws.md, frontend-integration-patterns.md

### Tools
Appropriate tools for their domain:
- **Read/Write agents**: Full file manipulation, code editing, diagnostics (Backend, Frontend, Documentation)
- **Read-only agents**: File reading, searching, diagnostics only (Security)

### Powers
AWS-specific capabilities:
- All agents have `includePowers: true` to access available Powers

---

## Troubleshooting

### Subagent Not Loading

**Issue:** Subagent doesn't appear in the list

**Solutions:**
1. Verify file is in `.kiro/agents/` directory
2. Check markdown frontmatter syntax is valid
3. Ensure file has `.md` extension
4. Restart Kiro IDE

### Subagent Producing Incorrect Output

**Issue:** Subagent doesn't follow CIC standards

**Solutions:**
1. Check steering files are correctly referenced
2. Verify instructions are clear and specific
3. Ensure appropriate tools are available
4. Provide more specific task description

### Subagent Can't Access Files

**Issue:** Subagent reports file access errors

**Solutions:**
1. Verify file paths are correct and relative to workspace root
2. Check subagent has appropriate tools (readFile, readCode, etc.)
3. Ensure files exist in the workspace

---

## Version History

### v2.0.0 (Current)
- Consolidated from 6 to 4 agents for efficiency
- Merged deployment into backend agent
- Distributed testing to backend and frontend agents
- Reduced token consumption while maintaining functionality
- Simplified agent selection and orchestration

### v1.0.0
- Initial release with 6 core subagents
- Backend, Frontend, Security, Deployment, Testing, Documentation
