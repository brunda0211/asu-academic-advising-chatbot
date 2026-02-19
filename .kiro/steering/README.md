# Kiro Steering Files

Organized guidance for CIC projects. Files auto-load based on context to minimize token usage.

## Structure

```
.kiro/steering/
├── README.md                                    # This file
├── ASU-CIC-architectural-standards.md          # Core principles (always loaded)
├── security-check-workflow.md                  # Security check workflow (manual)
├── backend/
│   ├── backend-standards.md                    # CDK/Lambda patterns
│   ├── backend-integration-api.md              # API & streaming patterns
│   ├── backend-integration-aws.md              # AWS service integration
│   └── backend-integration-patterns.md         # Error handling & performance
├── frontend/
│   ├── frontend-core.md                        # Next.js core & TypeScript
│   ├── frontend-styling.md                     # Tailwind & responsive design
│   └── frontend-state-i18n.md                  # State management & i18n
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

### Auto-loaded by File Pattern (Targeted)

**Backend Integration** (frontend files only):
- `backend-integration-api.md` - Loads for API/streaming files (api*, stream*, useChat*, useStream*)
- `backend-integration-aws.md` - Loads for AWS service files (s3*, bedrock*, cognito*, aws*)
- `backend-integration-patterns.md` - Loads for error/test files (error*, retry*, fetch*, logger*, tests)

**Frontend** (frontend files only):
- `frontend-core.md` - Loads for config/core files (tsconfig, next.config, app/*, config*, utils*)
- `frontend-styling.md` - Loads for styling files (tailwind.config, postcss.config, *.css, components)
- `frontend-state-i18n.md` - Loads for state/i18n files (contexts/*, hooks/use*, i18n*, locales/*)

**Backend** (backend files only):
- `backend-standards.md` - Loads for all backend TypeScript/Python files

**Security** (targeted by concern):
- `security-iam-secrets.md` - Loads for IAM/policy/secret files
- `security-data-encryption.md` - Loads for S3/DynamoDB files
- `security-code-dependencies.md` - Loads for Python/dependency files
- `security-operations.md` - Loads for error handling/observability files
- `security-compliance.md` - Loads for documentation files

### Manual Reference Only
- `security-check-workflow.md` - Referenced by Security Check hook
- `security/security-scanning.md` - Referenced by Security Check hook

## Usage

Steering files automatically load based on specific file patterns:
- Editing `frontend/lib/apiClient.ts` → Loads backend-integration-api
- Editing `frontend/lib/s3Upload.ts` → Loads backend-integration-aws
- Editing `backend/lib/my-stack.ts` (with IAM) → Loads backend-standards + security-iam-secrets
- Editing `frontend/tailwind.config.ts` → Loads frontend-styling
- Editing `frontend/contexts/AuthContext.tsx` → Loads frontend-state-i18n

To manually reference a file: `#security-check-workflow.md`

## Benefits

- **Minimal context usage** - Only relevant guidance loads
- **Organized by domain** - Easy to find and maintain
- **Comprehensive coverage** - All original content preserved
- **Smart auto-loading** - Right guidance at the right time
