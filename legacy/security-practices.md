---
inclusion: fileMatch
fileMatchPattern: "**/*.ts,**/*.py,**/lib/**/*,**/lambda/**/*"
---

# Security Best Practices

Comprehensive security guidance for CIC projects. Auto-loads when working on TypeScript, Python, or infrastructure code.

## Guiding Principles

1. **PoC code becomes production code.** Treat every line as if it will ship.
2. **Least privilege is not optional.** Wildcard permissions are never acceptable, even in prototypes.
3. **Security is not a phase.** It is a property of every commit.
4. **Document as you go.** Missing documentation is a security finding.
5. **Automate enforcement.** Use tooling and IDE agents to catch violations before they reach a pull request.

## 1. IAM and Access Control

| Practice | Detail |
|---|---|
| **No wildcard actions** | Never use `service:*`. Enumerate the specific API actions your code actually calls. |
| **No wildcard resources** | Always scope `Resource` to specific ARNs. Use CDK-generated ARNs (e.g., `bucket.bucketArn`, `table.tableArn`). |
| **No `iam:*` ever** | This is a privilege escalation vector. If your deployment needs to create roles, use a narrowly scoped deployment role created out of band. |
| **One role per function** | Each Lambda function or ECS task gets its own IAM role with only the permissions that specific function requires. |
| **Add conditions** | Use conditions like `aws:SourceAccount`, `aws:SourceArn`, or `aws:PrincipalOrgID` to restrict trust relationships. |
| **Review with tooling** | Run `cdk-nag` or `cfn-nag` on every synthesized template before deployment. |

### Example: Before and After

**Before (non-compliant):**
```python
iam.PolicyStatement(actions=["s3:*"], resources=["*"])
```

**After (compliant):**
```python
iam.PolicyStatement(
    actions=["s3:GetObject", "s3:PutObject"],
    resources=[f"{input_bucket.bucket_arn}/*", f"{output_bucket.bucket_arn}/*"],
    conditions={"StringEquals": {"aws:SourceAccount": core.Aws.ACCOUNT_ID}}
)
```

## 2. Secrets Management

| Practice | Detail |
|---|---|
| **No hardcoded secret paths** | Pass secret names or ARNs via environment variables set by CDK/CloudFormation. |
| **Use Secrets Manager or Parameter Store** | All credentials, API keys, and tokens must be stored in AWS Secrets Manager or SSM Parameter Store. |
| **Grant narrow access** | The Lambda role should have `secretsmanager:GetSecretValue` only on the specific secret ARN it needs. |
| **Rotate secrets** | Enable automatic rotation where supported. Document rotation procedures for third-party credentials. |
| **Never log secrets** | Ensure no secret value is written to CloudWatch Logs, Step Functions state, or S3. |

### Example: Correct Pattern

```python
# Infrastructure (CDK)
secret = secretsmanager.Secret.from_secret_name_v2(self, "AdobeApiSecret", "my-app/adobe-credentials")
lambda_fn.add_environment("ADOBE_SECRET_ARN", secret.secret_arn)
secret.grant_read(lambda_fn)

# Application code
import os, boto3, json

def get_credentials():
    secret_arn = os.environ["ADOBE_SECRET_ARN"]
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    return json.loads(response["SecretString"])
```

## 3. S3 Security
### Best Practices

| Practice | Detail |
|---|---|
| **Block Public Access** | Enable `BlockPublicAccess.BLOCK_ALL` on every bucket. No exceptions for PoCs. |
| **Enforce TLS** | Set `enforce_ssl=True` in CDK or add a bucket policy denying `aws:SecureTransport = false`. |
| **Encrypt at rest** | Use `encryption=s3.BucketEncryption.S3_MANAGED` at minimum. Prefer KMS for sensitive data. |
| **Enable versioning** | Enable on any bucket storing documents or artifacts. |
| **Enable access logging** | Create a dedicated logging bucket and enable server access logging on all data buckets. |
| **Encrypt on upload** | Always include `ServerSideEncryption` in `put_object` and `upload_file` calls. |
| **Auto-delete for PoC** | Use `removal_policy=RemovalPolicy.DESTROY` and `auto_delete_objects=True` so PoC resources clean up. |

### Example: Secure Bucket in CDK

```python
input_bucket = s3.Bucket(
    self, "InputDocumentBucket",
    bucket_name=f"{project_prefix}-input-{core.Aws.ACCOUNT_ID}",
    block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
    encryption=s3.BucketEncryption.S3_MANAGED,
    enforce_ssl=True,
    versioned=True,
    removal_policy=core.RemovalPolicy.DESTROY,
    auto_delete_objects=True,
    server_access_logs_bucket=log_bucket,
    server_access_logs_prefix="input-bucket-logs/",
)
```

## 4. Code Security and Dependency Management

| Practice | Detail |
|---|---|
| **Pin dependencies** | Always pin exact versions in `requirements.txt`, `package.json`, `pom.xml`. |
| **Scan dependencies** | Run `pip-audit`, `npm audit`, or `mvn dependency-check:check` in CI. |
| **Update regularly** | Use Dependabot, Renovate, or a manual review cadence (at least monthly for PoCs). |
| **Run SAST** | Run Bandit (Python), ESLint-security (JS), SpotBugs (Java) on every commit. |
| **Fix or document** | Every HIGH/CRITICAL finding must be fixed or have a documented risk acceptance with a rationale and owner. |
| **Secure temp files** | Use `tempfile.NamedTemporaryFile()` with `delete=True`. Call `.flush()` before reading `.name`. Never construct temp paths with user input. |
| **Validate paths** | Never concatenate user input into file paths. Use `os.path.basename()` and validate against an allowlist. |
| **No `eval()` or `exec()`** | Never use dynamic code execution on untrusted input. |

## 5. AI and GenAI Security

| Practice | Detail |
|---|---|
| **Validate AI inputs** | Sanitize all content before sending it to a model. Limit input size and character set. |
| **Filter AI outputs** | Never insert model output directly into HTML, SQL, or code. Sanitize and validate against expected structure. |
| **Protect against prompt injection** | Separate system prompts from user content. Use delimiters and instruct the model to ignore conflicting instructions in user content. |
| **Log all invocations** | Log the model ID, input hash (not full PII), output hash, latency, and token count for every Bedrock call. |
| **Document model usage** | Maintain a register of which models are used, their purpose, and who approved their use. |
| **Consider bias** | For accessibility features, document how AI-generated content is reviewed for accuracy and bias. Even in a PoC, note this as a known risk. |
| **Scope Bedrock permissions** | Grant `bedrock:InvokeModel` only for the specific model ARNs used, not `bedrock:*`. |

### Example: Safe Output Handling

```python
import html

def apply_alt_text(img_element, ai_generated_text):
    # Sanitize AI output before inserting into HTML
    safe_text = html.escape(ai_generated_text.strip())
    # Validate length
    if len(safe_text) > 500:
        safe_text = safe_text[:500]
    img_element["alt"] = safe_text
```

## 6. Data Security and Encryption

| Practice | Detail |
|---|---|
| **Classify data** | Even in a PoC, state what kind of data flows through the system (e.g., "user-uploaded PDFs, potentially containing PII"). |
| **Encrypt at rest everywhere** | S3 buckets, DynamoDB tables, EFS volumes, EBS volumes — all must have encryption enabled. |
| **Encrypt in transit everywhere** | Enforce TLS. Use VPC endpoints for AWS service calls where possible. |
| **Encrypt on every upload** | Include `ServerSideEncryption` on every `put_object` call. Don't rely solely on bucket defaults. |
| **Document key management** | State which encryption approach is used (SSE-S3, SSE-KMS) and why. |
| **Enable access logging** | For S3 and any API Gateway. This is your audit trail. |

## 7. Error Handling, Resilience, and Observability

| Practice | Detail |
|---|---|
| **Structured logging** | Use JSON-formatted logs with consistent fields: `timestamp`, `request_id`, `step`, `status`, `error_type`, `message`. |
| **Correlate across services** | Pass a correlation ID (e.g., the Step Functions execution ID) through every Lambda invocation and log it. |
| **Configure DLQs** | Every SQS queue and Lambda event source must have a dead-letter queue. |
| **Retry with backoff** | Use exponential backoff with jitter for external API calls. Configure Step Functions retry policies on every task state. |
| **Don't swallow errors** | Never catch an exception and silently continue. Log it, optionally re-raise it, and ensure the pipeline state reflects the failure. |
| **Set alarms** | Create CloudWatch alarms for: Lambda errors, Step Functions failed executions, DLQ message count > 0, and external API error rates. |
| **Pass status in state** | Step Functions state should carry structured status objects, not just success/fail booleans. Include error codes and messages. |

### Example: Step Functions Retry Configuration

```json
{
  "Type": "Task",
  "Resource": "arn:aws:lambda:...:check-accessibility",
  "Retry": [
    {
      "ErrorEquals": ["ServiceUnavailable", "TooManyRequestsException"],
      "IntervalSeconds": 5,
      "MaxAttempts": 3,
      "BackoffRate": 2.0
    }
  ],
  "Catch": [
    {
      "ErrorEquals": ["States.ALL"],
      "ResultPath": "$.error",
      "Next": "HandleFailure"
    }
  ]
}
```

## 8. Documentation and Threat Modeling

| Practice | Detail |
|---|---|
| **Create a SECURITY.md** | Every repo needs one. It should contain: threat model summary, known risks, security contacts, and vulnerability reporting instructions. |
| **Lightweight threat model** | Use a simple table: Asset → Threat → Mitigation → Status. Cover the top 5-10 risks. STRIDE is optional for a PoC; a simple list is sufficient. |
| **Document security controls per service** | For each AWS service used, write one sentence about how it is secured (e.g., "S3: SSE-S3 encryption, BPA enabled, TLS enforced"). |
| **Architecture diagram with security boundaries** | Show VPC boundaries, public/private subnets, IAM role assignments, and encryption in transit/at rest on the architecture diagram. |
| **Shared responsibility callout** | Add a section noting that the customer is responsible for configuring IAM, encryption, and network controls, linking to the AWS Shared Responsibility Model. |

### Example: Lightweight Threat Model Table

| # | Asset | Threat | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|---|
| 1 | S3 Input Bucket | Unauthorized access to uploaded PDFs | Medium | High | BPA, bucket policy, IAM scoping, encryption | ✅ Implemented |
| 2 | Adobe API Credentials | Credential exposure in logs or code | Medium | High | Secrets Manager, env vars, no logging of values | ✅ Implemented |
| 3 | Bedrock Prompts | Prompt injection via malicious PDF content | Low | Medium | Input sanitization, output validation | ⚠️ Partial |
| 4 | Lambda /tmp | Sensitive data persisted in temp storage | Low | Medium | Ephemeral storage, no cross-invocation state | ✅ Accepted |
| 5 | Step Functions State | PII in execution history | Low | Medium | No PII in state, use S3 references instead | ⚠️ Needs review |

## 9. Legal and Licensing Hygiene

| Practice | Detail |
|---|---|
| **License header in every source file** | Use SPDX identifiers. Apply consistently across Python, Java, JavaScript, and shell scripts. |
| **Single license declaration** | Ensure `LICENSE`, `package.json`, `pyproject.toml`, and `pom.xml` all declare the same license. |
| **No internal contact info** | Never include internal email addresses, aliases, or internal URLs in public repos. Use a team alias or GitHub issues for contact. |
| **Third-party license tracking** | Maintain a `THIRD-PARTY-LICENSES` file and review it when adding dependencies. |
| **No personal file paths** | Scrub build artifacts and test reports for local file paths before committing. |

## 10. Deployment Consistency and Infrastructure as Code

| Practice | Detail |
|---|---|
| **Single source of truth** | Use one deployment method (prefer CDK or CloudFormation). Remove or clearly deprecate alternatives. |
| **No security config in scripts** | If shell scripts are used for orchestration, they should call CDK/CloudFormation — not create resources directly with the AWS CLI. |
| **Validate before deploy** | Run `cdk diff`, `cdk-nag`, and a synthesized template review before every deployment. |
| **Tag everything** | Apply consistent tags (Project, Environment, Owner, CostCenter) to all resources for traceability. |
| **Meaningful resource names** | Use descriptive names (e.g., `PdfInputDocumentBucket` instead of `Bucket1`). Names should convey purpose. |

## 11. Automated Security Scanning

CIC projects use AWS-recommended security tools integrated via Kiro's Security Check hook.

### Security Check Hook

**Trigger**: Ask Kiro to "run a security check" or similar prompt
**Tools**: Automatically selects cdk-nag and/or ASH based on context
**Workflow**: Scans → Parses results → Prioritizes findings → Provides fixes

**Example prompts**:
- "Run a security check"
- "Check this file for security issues"
- "Scan the backend for vulnerabilities"
- "Check my CDK code for security problems"

See `.kiro/steering/SECURITY_CHECK_HOOK.md` for complete documentation.

### Tool 1: cdk-nag (Infrastructure Security)

**Purpose**: Validates CDK/CloudFormation against AWS best practices during synthesis

**What it checks**:
- IAM policies (wildcards, least privilege)
- S3 security (encryption, public access)
- Lambda configurations
- DynamoDB encryption
- API Gateway security

**Installation**:
```bash
cd backend
npm install cdk-nag
```

**Integration** (add to `backend/bin/app.ts`):
```typescript
import { App, Aspects } from 'aws-cdk-lib';
import { AwsSolutionsChecks } from 'cdk-nag';

const app = new App();
// ... create stacks ...
Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));
app.synth();
```

**Suppressing findings** (when justified):
```typescript
import { NagSuppressions } from 'cdk-nag';

NagSuppressions.addResourceSuppressions(resource, [
  {
    id: 'AwsSolutions-IAM4',
    reason: 'AWS managed policy required for CloudWatch Logs. See ADR in architectureDeepDive.md',
  },
]);
```

### Tool 2: ASH - Automated Security Helper (Comprehensive Scanning)

**Purpose**: Multi-scanner orchestration for SAST, SCA, IaC, and secrets detection

**What it checks**:
- **SAST**: Python (Bandit), Multi-language (Semgrep)
- **Secrets**: Hardcoded credentials (detect-secrets)
- **IaC**: CloudFormation, Terraform (Checkov, cfn-nag, cdk-nag)
- **SCA**: Dependencies (npm-audit, Grype)
- **SBOM**: Software bill of materials (Syft)

**Installation**:
```bash
# Install uv package manager
curl -sSfL https://astral.sh/uv/install.sh | sh

# Create alias
alias ash="uvx git+https://github.com/awslabs/automated-security-helper.git@v3.1.12"
```

**Usage**:
```bash
# Fast scan (Python-only scanners)
ash --mode local

# Comprehensive scan (requires Docker)
ash --mode container

# Scan specific directory
ash --mode local --source-dir backend/lambda

# View results
cat .ash/ash_output/ash_aggregated_results.json
open .ash/ash_output/reports/ash.html
```

**Configuration** (`.ash/ash.yaml` in project root):
```yaml
project_name: my-cic-project
global_settings:
  severity_threshold: MEDIUM
  ignore_paths:
    - path: 'tests/test_data'
      reason: 'Test fixtures only'
scanners:
  bandit:
    enabled: true
  detect-secrets:
    enabled: true
  checkov:
    enabled: true
```

### When to Run Security Scans

**Always**:
- Before deploying to production
- After adding new AWS services
- After updating dependencies
- When handling sensitive data

**Consider**:
- After significant code changes
- Before creating pull requests
- Weekly on active projects
- After security advisories

### CI/CD Integration

**Development**: Use Security Check hook for on-demand scans with interactive remediation

**CI/CD**: Add automated scans to pipeline (see SECURITY_CHECK_HOOK.md for examples)

### Prioritizing Security Findings

1. **Critical/High severity** in production code
2. **Secrets/credentials** exposure
3. **IAM overpermissions** (wildcards, admin access)
4. **Data encryption** issues
5. **Dependency vulnerabilities** with known exploits
6. **Medium severity** in production code
7. **Low severity** and informational

## Quick Reference Checklist

Use this checklist before every pull request:

```
## Security PR Checklist

### Automated Scanning
- [ ] Run Security Check hook: "Run a security check"
- [ ] Address all Critical/High severity findings
- [ ] Document suppressions with justification

### IAM
- [ ] No wildcard actions in any IAM policy
- [ ] No wildcard resources (`*`) in any IAM policy
- [ ] Each function/task has its own role
- [ ] Permissions are commented with justification

### Secrets
- [ ] No hardcoded secret names, paths, or values in source code
- [ ] All secrets referenced via environment variables
- [ ] Secret access scoped to specific ARNs

### S3
- [ ] Block Public Access enabled on all buckets
- [ ] Encryption at rest enabled on all buckets
- [ ] TLS enforced on all buckets
- [ ] ServerSideEncryption set on all upload operations

### Code Security
- [ ] No new HIGH/CRITICAL findings from SAST tools
- [ ] Dependencies pinned to specific versions
- [ ] No known CVEs in dependencies at HIGH/CRITICAL severity
- [ ] No bare except blocks that swallow errors
- [ ] No unsanitized user input in file paths or shell commands

### AI/GenAI
- [ ] Model outputs sanitized before use in HTML/SQL/code
- [ ] Bedrock permissions scoped to specific model ARNs
- [ ] Prompt construction separates system and user content
- [ ] Model invocations are logged

### Resilience
- [ ] External API calls have retry with backoff
- [ ] Lambda functions have DLQ or on-failure destination
- [ ] Step Functions tasks have Retry and Catch blocks
- [ ] Correlation ID logged in every function

### Documentation
- [ ] SECURITY.md exists and is current
- [ ] Architecture diagram shows security boundaries
- [ ] No internal email addresses or file paths in any file
- [ ] License headers present on all source files
```

## Integration

Reference this checklist in:
- PR templates for code review
- CI/CD pipeline validation
- Pre-commit hooks for automated checks
- SECURITY.md in project root
