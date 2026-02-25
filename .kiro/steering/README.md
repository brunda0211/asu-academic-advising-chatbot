# Kiro Steering Files

Organized guidance for CIC projects. Files auto-load based on context to minimize token usage.

## Structure

```
.kiro/steering/
├── README.md                                    # This file
├── ASU-CIC-architectural-standards.md          # Core principles (always loaded)
├── security-check-workflow.md                  # Security check workflow (manual)
├── backend/
│   └── backend-standards.md                    # CDK/Lambda patterns (all backend files)
├── frontend/
│   ├── frontend-core.md                        # Next.js core & TypeScript
│   ├── frontend-styling.md                     # Tailwind & responsive design
│   ├── frontend-state-i18n.md                  # State management & i18n
│   ├── frontend-integration-api.md             # API clients & streaming
│   ├── frontend-integration-aws.md             # AWS SDK usage (S3, Cognito, Bedrock)
│   └── frontend-integration-patterns.md        # Error handling & retry patterns
└── security/
    ├── security-iam-secrets.md                 # IAM & secrets management
    ├── security-data-encryption.md             # S3 & data encryption
    ├── security-code-dependencies.md           # Code security & AI/GenAI
    ├── security-operations.md                  # Error handling & resilience
    ├── security-compliance.md                  # Documentation & legal
    └── security-scanning.md                    # Automated scanning tools (manual)
```

## Inclusion Modes

### Always Loaded
- `ASU-CIC-architectural-standards.md` - Core principles for all CIC projects
- `security-compliance.md` - Documentation, threat modeling, legal hygiene

### Auto-loaded by File Pattern

**Backend Files** (`backend/**/*`):
- `backend-standards.md` - CDK/Lambda patterns and best practices
- `security-iam-secrets.md` - IAM least privilege and secrets management
- `security-data-encryption.md` - Encryption at rest and in transit
- `security-operations.md` - Error handling, retry logic, resilience
- `security-code-dependencies.md` - Dependency security and AI/GenAI usage

**Frontend Files** (`frontend/**/*`):
- `frontend-core.md` - Next.js, React, TypeScript fundamentals
- `frontend-styling.md` - Tailwind CSS and responsive design
- `frontend-state-i18n.md` - State management and internationalization
- `frontend-integration-api.md` - API clients and streaming
- `frontend-integration-aws.md` - AWS SDK usage (S3, Cognito, Bedrock)
- `frontend-integration-patterns.md` - Error handling and retry patterns

### Manual Reference Only
- `security-check-workflow.md` - Referenced by Security Check hook
- `security-scanning.md` - Referenced by Security Check hook

## Usage

Steering files automatically load when reading files in their target directories:

**Reading any backend file** (`backend/**/*`):
- Always loaded: `ASU-CIC-architectural-standards` + `security-compliance`
- Backend-specific: `backend-standards` + `security-iam-secrets` + `security-data-encryption` + `security-operations` + `security-code-dependencies`

**Reading any frontend file** (`frontend/**/*`):
- Always loaded: `ASU-CIC-architectural-standards` + `security-compliance`
- Frontend-specific: `frontend-core` + `frontend-styling` + `frontend-state-i18n` + `frontend-integration-api` + `frontend-integration-aws` + `frontend-integration-patterns`

**Manual reference**: Use `#security-check-workflow.md` or `#security-scanning.md` to load on-demand

## Benefits

- **Simplified patterns** - Three categories: always, backend, or frontend
- **Predictable loading** - Clear rules for when guidance appears
- **Complete coverage** - All relevant guidance loads for each domain
- **Easy maintenance** - No complex pattern matching to update
- **Domain separation** - Backend and frontend guidance stay separate
