---
inclusion: fileMatch
fileMatchPattern: "docs/**/*,README.md,SECURITY.md,LICENSE,backend/lib/**/*stack*.ts,backend/bin/**/*.ts"
---

# Security: Compliance & Documentation

Documentation, threat modeling, legal hygiene, and deployment consistency for CIC projects.

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
