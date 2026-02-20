# Kiro Steering Files

Organized guidance for CIC projects. Files auto-load based on context to minimize token usage.

## Structure

```
.kiro/steering/
├── README.md                                    # This file
├── ASU-CIC-architectural-standards.md          # Core principles (always loaded)
├── security-check-workflow.md                  # Security check workflow (manual)
├── backend/
│   ├── backend-standards.md                    # CDK/Lambda patterns (all backend files)
│   ├── backend-integration-api.md              # API & streaming patterns (frontend lib files)
│   ├── backend-integration-aws.md              # AWS service integration (frontend lib files)
│   └── backend-integration-patterns.md         # Error handling & performance (frontend lib/test files)
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

**Backend (AWS CDK + Lambda — `backend/` directory)**:
- `backend-standards.md` - Loads for ALL files under `backend/**/*` (CDK TypeScript + Lambda Python)
- `security-iam-secrets.md` - Loads for `backend/lib/**/*.ts`, `backend/bin/**/*.ts` (every CDK file triggers IAM review)
- `security-data-encryption.md` - Loads for `backend/lib/**/*stack*.ts`, S3/DynamoDB CDK constructs, Lambda storage handlers
- `security-operations.md` - Loads for `backend/lib/**/*stack*.ts`, Lambda index handlers, error/retry/log files
- `security-code-dependencies.md` - Loads for `backend/lambda/**/*.py`, `requirements.txt`, agent/strands/bedrock Lambda files
- `security-compliance.md` - Loads for `backend/lib/**/*stack*.ts`, `backend/bin/**/*.ts`, docs files

**Frontend (Next.js — `frontend/` directory)**:
- `frontend-core.md` - Loads for `frontend/app/**/*`, `frontend/lib/**/*.ts`, tsconfig, next.config, config/utils files
- `frontend-styling.md` - Loads for tailwind.config, postcss.config, `*.css`, `frontend/components/**/*`
- `frontend-state-i18n.md` - Loads for `frontend/contexts/**/*`, `frontend/hooks/**/*.ts`, i18n/locales files

**Backend Integration patterns (frontend files that call the backend)**:
- `backend-integration-api.md` - Loads for `frontend/lib/**/*api*`, `*stream*`, `*client*`, `hooks/use*Chat*`, `use*Stream*`, `use*Api*`
- `backend-integration-aws.md` - Loads for `frontend/lib/**/*s3*`, `*bedrock*`, `*cognito*`, `*aws*`, `*upload*`, `*storage*`
- `backend-integration-patterns.md` - Loads for `frontend/lib/**/*error*`, `*retry*`, `*fetch*`, `*logger*`, `*utils*`, test files

### Manual Reference Only
- `security-check-workflow.md` - Referenced by Security Check hook
- `security/security-scanning.md` - Referenced by Security Check hook

## Usage

Steering files automatically load based on file patterns. Examples for this project:

**Backend (AWS CDK)**:
- Editing `backend/lib/backend-stack.ts` → Loads `backend-standards` + `security-iam-secrets` + `security-data-encryption` + `security-operations` + `security-compliance`
- Editing `backend/bin/backend.ts` → Loads `backend-standards` + `security-iam-secrets` + `security-compliance`
- Editing `backend/lambda/orchestrator/index.py` → Loads `backend-standards` + `security-code-dependencies` + `security-operations`
- Editing `backend/lambda/orchestrator/requirements.txt` → Loads `backend-standards` + `security-code-dependencies`

**Frontend (Next.js)**:
- Editing `frontend/app/page.tsx` → Loads `frontend-core`
- Editing `frontend/lib/apiClient.ts` → Loads `frontend-core` + `backend-integration-api`
- Editing `frontend/lib/s3Upload.ts` → Loads `frontend-core` + `backend-integration-aws`
- Editing `frontend/components/ChatMessage.tsx` → Loads `frontend-styling`
- Editing `frontend/hooks/useChat.ts` → Loads `frontend-state-i18n`
- Editing `frontend/tailwind.config.ts` → Loads `frontend-styling`
- Editing `frontend/contexts/SessionContext.tsx` → Loads `frontend-state-i18n`

To manually reference a file: `#security-check-workflow.md`

## Benefits

- **Minimal context usage** - Only relevant guidance loads
- **Organized by domain** - Easy to find and maintain
- **Comprehensive coverage** - All original content preserved
- **Smart auto-loading** - Right guidance at the right time
- **Backend/frontend separation** - `backend/` patterns never bleed into `frontend/` and vice versa
