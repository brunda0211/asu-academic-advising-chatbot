# Security Check Hook Documentation

## Overview

The Security Check hook provides intelligent, on-demand security scanning using AWS-recommended tools (cdk-nag and automated-security-helper). It analyzes your code, infrastructure, and dependencies, then provides actionable remediation guidance.

## How It Works

### Trigger
The hook activates when you ask Kiro to run a security check. Example prompts:
- "Run a security check"
- "Check this file for security issues"
- "Scan the backend for vulnerabilities"
- "Run a full security audit"
- "Check my CDK code for security problems"

### Intelligence
Kiro automatically determines:
1. **Scope**: Which files/directories to scan based on your request
2. **Tools**: Whether to use cdk-nag, ASH, or both
3. **Mode**: Fast local scan vs comprehensive container scan
4. **Priority**: Which findings to address first

### Workflow
1. **Analyze request** → Determine scope and tools
2. **Run scans** → Execute selected security tools
3. **Parse results** → Extract and categorize findings
4. **Prioritize** → Order by severity and impact
5. **Remediate** → Provide fixes with code examples
6. **Offer to fix** → Can automatically apply fixes if desired

---

## Security Tools

### 1. cdk-nag (CDK/CloudFormation Security)

**What it checks:**
- IAM policies and roles (least privilege, wildcards)
- S3 bucket security (encryption, public access)
- Lambda configurations (environment variables, VPC)
- DynamoDB encryption and backup
- API Gateway security
- CloudFormation best practices

**When it runs:**
- User mentions "CDK", "infrastructure", or "CloudFormation"
- Scanning backend/lib/ or backend/bin/ directories
- Full codebase scan (runs alongside ASH)

**Rule packs available:**
- AWS Solutions (default)
- HIPAA Security
- NIST 800-53 rev 4 & 5
- PCI DSS 3.2.1
- Serverless best practices

**Installation:**
```bash
cd backend
npm install cdk-nag
```

**Manual usage:**
```bash
cd backend
npx cdk synth --quiet
# Look for [Error] or [Warning] lines with AwsSolutions-* rule IDs
```

---

### 2. ASH - Automated Security Helper (Comprehensive Scanning)

**What it checks:**
- **SAST**: Python (Bandit), Multi-language (Semgrep)
- **Secrets**: Hardcoded credentials, API keys (detect-secrets)
- **IaC**: CloudFormation, Terraform (Checkov, cfn-nag, cdk-nag)
- **SCA**: Dependency vulnerabilities (npm-audit, Grype)
- **SBOM**: Software bill of materials (Syft)

**When it runs:**
- User mentions "Lambda", "Python", "code", "dependencies", "secrets"
- Scanning specific files or directories
- Full codebase scan (comprehensive mode)

**Execution modes:**
- **Local** (fast): Python-only scanners (Bandit, Semgrep, detect-secrets, Checkov)
- **Container** (comprehensive): All scanners including npm-audit, Grype, Syft
- **Precommit** (fastest): Subset optimized for speed

**Installation:**
```bash
# Install uv (package manager)
curl -sSfL https://astral.sh/uv/install.sh | sh

# Create alias
alias ash="uvx git+https://github.com/awslabs/automated-security-helper.git@v3.1.12"
```

**Manual usage:**
```bash
# Scan entire project (local mode)
ash --mode local

# Scan specific directory
ash --mode local --source-dir backend/lambda

# Comprehensive scan (requires Docker)
ash --mode container

# View results
cat .ash/ash_output/ash_aggregated_results.json
open .ash/ash_output/reports/ash.html
```

---

## Usage Examples

### Example 1: Full Codebase Scan
```
User: "Run a full security check on this project"

Kiro will:
1. Run cdk-nag on backend CDK code
2. Run ASH in local mode on entire codebase
3. Parse and prioritize all findings
4. Present findings by severity
5. Offer to fix issues automatically
```

### Example 2: Specific File Scan
```
User: "Check backend/lambda/resume-parser/index.py for security issues"

Kiro will:
1. Run ASH on that specific file
2. Focus on Python-specific issues (Bandit, Semgrep)
3. Check for secrets and vulnerabilities
4. Provide file-specific remediation
```

### Example 3: Infrastructure Only
```
User: "Check my CDK stack for security problems"

Kiro will:
1. Run cdk-nag during synthesis
2. Focus on infrastructure findings
3. Explain IAM, S3, Lambda security issues
4. Provide CDK code fixes
```

### Example 4: Dependency Scan
```
User: "Check for vulnerable dependencies"

Kiro will:
1. Run ASH with focus on SCA scanners
2. Check npm packages (npm-audit)
3. Check Python packages (Grype)
4. Recommend updates or patches
```

---

## Understanding Results

### cdk-nag Output Format
```
[Error at /StackName/ResourceName] AwsSolutions-IAM4: The IAM user, role, or group uses AWS managed policies
[Warning at /StackName/BucketName] AwsSolutions-S1: The S3 Bucket does not have server access logs enabled
```

**Key components:**
- **Severity**: Error (high) or Warning (medium)
- **Path**: CloudFormation resource path
- **Rule ID**: AwsSolutions-* identifier
- **Description**: What the issue is

### ASH Output Format
ASH produces multiple report formats:

**JSON** (`.ash/ash_output/ash_aggregated_results.json`):
```json
{
  "findings": [
    {
      "scanner": "bandit",
      "severity": "HIGH",
      "rule_id": "B201",
      "file": "backend/lambda/handler.py",
      "line": 42,
      "message": "Use of exec() detected",
      "suppressed": false
    }
  ]
}
```

**HTML** (`.ash/ash_output/reports/ash.html`):
- Interactive table of all findings
- Filterable by severity, scanner, file
- Click to see code context

**Summary** (`.ash/ash_output/reports/ash.summary.txt`):
```
Scanner    | Critical | High | Medium | Low | Result
-----------|----------|------|--------|-----|--------
bandit     | 0        | 1    | 0      | 5   | FAILED
detect-secrets | 0    | 2    | 0      | 0   | FAILED
checkov    | 0        | 3    | 1      | 0   | FAILED
```

---

## Remediation Strategies

### 1. Auto-Fix (Simple Issues)
Kiro can automatically fix:
- Adding missing encryption settings
- Enabling logging/monitoring
- Updating dependency versions
- Removing hardcoded secrets (replace with environment variables)
- Adding security headers

### 2. Guided Fix (Complex Issues)
Kiro provides code examples for:
- IAM policy refinement (removing wildcards)
- Implementing least privilege
- Adding input validation
- Configuring VPC settings
- Setting up proper authentication

### 3. Suppression (False Positives)
When suppression is appropriate:
- Test/mock data (not production)
- Intentional design decisions
- Framework limitations

**Suppression format (cdk-nag):**
```typescript
import { NagSuppressions } from 'cdk-nag';

NagSuppressions.addResourceSuppressions(resource, [
  {
    id: 'AwsSolutions-IAM4',
    reason: 'AWS managed policy required for service integration',
  },
]);
```

**Suppression format (ASH):**
```python
# nosec B201 - exec() used for controlled plugin system with input validation
result = exec(sanitized_code)
```

---

## Integration with CIC Standards

The Security Check hook references CIC steering files:

### security-practices.md
- IAM least privilege patterns
- Secrets management (Secrets Manager, environment variables)
- S3 security (encryption, TLS, BlockPublicAccess)
- Code security (input validation, SAST)
- AI/GenAI security (prompt injection, output sanitization)

### backend-standards
- CDK security patterns
- Lambda security configuration
- DynamoDB encryption requirements
- IAM grant methods (no wildcards)

### CIC-coding-standards
- No hardcoding credentials, endpoints, or configuration
- Security-first principle
- Backend-first architecture
- Documentation requirements for security decisions

---

## CI/CD Integration

### Recommended Workflow

**Development** (this hook):
- On-demand security checks during development
- Fast feedback on specific changes
- Interactive remediation

**Pre-Deployment** (CI/CD):
- Automated security checks in pipeline
- Fail build on critical/high findings
- Generate security reports

### Adding to CI/CD

**GitHub Actions** (`.github/workflows/security.yml`):
```yaml
name: Security Scan
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install ASH
        run: |
          curl -sSfL https://astral.sh/uv/install.sh | sh
          echo "$HOME/.local/bin" >> $GITHUB_PATH
      
      - name: Run Security Scan
        run: |
          uvx git+https://github.com/awslabs/automated-security-helper.git@v3.1.12 \
            --mode container \
            --fail-on-findings true \
            --severity-threshold HIGH
      
      - name: Upload Results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: .ash/ash_output/reports/
```

**AWS CodeBuild** (`buildspec.yml`):
```yaml
version: 0.2

phases:
  install:
    commands:
      - curl -sSfL https://astral.sh/uv/install.sh | sh
      - export PATH="$HOME/.local/bin:$PATH"
  
  build:
    commands:
      - uvx git+https://github.com/awslabs/automated-security-helper.git@v3.1.12 --mode container
  
  post_build:
    commands:
      - echo "Security scan complete"

artifacts:
  files:
    - .ash/ash_output/reports/**/*
```

---

## Configuration

### ASH Configuration (`.ash/ash.yaml`)

Create this file in your project root for custom settings:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/awslabs/automated-security-helper/refs/heads/main/automated_security_helper/schemas/AshConfig.json

project_name: my-cic-project

global_settings:
  severity_threshold: MEDIUM
  fail_on_findings: true
  ignore_paths:
    - path: 'tests/test_data'
      reason: 'Test fixtures only'
    - path: 'node_modules'
      reason: 'Third-party dependencies'
    - path: '.ash'
      reason: 'ASH output directory'

scanners:
  bandit:
    enabled: true
    options:
      confidence_level: high
  
  detect-secrets:
    enabled: true
    options:
      baseline_file: '.secrets.baseline'
  
  checkov:
    enabled: true
    options:
      skip_checks:
        - CKV_AWS_18  # Example: Skip specific check if needed
  
  semgrep:
    enabled: true
    options:
      config: 'p/ci'  # Use CI ruleset

reporters:
  markdown:
    enabled: true
    options:
      include_detailed_findings: true
  
  html:
    enabled: true
  
  sarif:
    enabled: true
```

### cdk-nag Configuration

**In CDK app** (`backend/bin/app.ts`):
```typescript
import { App, Aspects } from 'aws-cdk-lib';
import { AwsSolutionsChecks, NagSuppressions } from 'cdk-nag';
import { MyStack } from '../lib/my-stack';

const app = new App();
const stack = new MyStack(app, 'MyStack');

// Add security checks
Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));

// Stack-level suppressions (if needed)
NagSuppressions.addStackSuppressions(stack, [
  {
    id: 'AwsSolutions-IAM4',
    reason: 'AWS managed policies required for AWS service integrations',
  },
]);

app.synth();
```

---

## Troubleshooting

### cdk-nag Issues

**Problem**: "cdk-nag not found"
```bash
cd backend
npm install cdk-nag
```

**Problem**: "Too many findings, can't read output"
```bash
# Redirect to file
cd backend
npx cdk synth --quiet 2>&1 | grep -E '(Error|Warning).*AwsSolutions' > security-findings.txt
```

**Problem**: "False positive findings"
- Add suppressions with clear justification
- Reference ADR if architectural decision
- Document in code comments

### ASH Issues

**Problem**: "uv not found"
```bash
# Install uv
curl -sSfL https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or ~/.zshrc
```

**Problem**: "Container mode fails"
```bash
# Use local mode instead (Python-only scanners)
ash --mode local

# Or install Docker/Podman for full scanner support
```

**Problem**: "Scan takes too long"
```bash
# Use precommit mode for faster scans
ash --mode precommit

# Or scan specific directory
ash --mode local --source-dir backend/lambda
```

**Problem**: "Too many findings"
```bash
# Increase severity threshold
ash --mode local --severity-threshold HIGH

# Or create .ash/ash.yaml with ignore_paths
```

---

## Best Practices

### When to Run Security Checks

**Always:**
- Before deploying to production
- After adding new AWS services
- After updating dependencies
- When handling sensitive data

**Consider:**
- After significant code changes
- Before creating pull requests
- Weekly on active projects
- After security advisories

### Prioritizing Fixes

1. **Critical/High severity** in production code
2. **Secrets/credentials** exposure
3. **IAM overpermissions** (wildcards, admin access)
4. **Data encryption** issues (S3, DynamoDB, in-transit)
5. **Dependency vulnerabilities** with known exploits
6. **Medium severity** in production code
7. **Low severity** and informational

### Documenting Security Decisions

When suppressing findings, document using ADR format:

```typescript
// ADR: Suppressing AwsSolutions-IAM4 for AWS managed policy
// Decision Date: 2024-02-13
// Rationale: AWSLambdaBasicExecutionRole required for CloudWatch Logs integration
// Alternative: Custom policy (rejected - increases maintenance burden)
NagSuppressions.addResourceSuppressions(lambdaFunction, [
  {
    id: 'AwsSolutions-IAM4',
    reason: 'AWS managed policy required for CloudWatch Logs integration. See ADR in architectureDeepDive.md',
  },
]);
```

---

## Quick Reference

### Common Commands

```bash
# Install tools
npm install cdk-nag  # In backend directory
curl -sSfL https://astral.sh/uv/install.sh | sh  # For ASH

# Run scans manually
cd backend && npx cdk synth --quiet  # cdk-nag
ash --mode local  # ASH local mode
ash --mode container  # ASH comprehensive

# View ASH results
cat .ash/ash_output/ash_aggregated_results.json  # JSON
open .ash/ash_output/reports/ash.html  # HTML report
cat .ash/ash_output/reports/ash.summary.txt  # Text summary
```

### Kiro Prompts

```
"Run a security check"
"Check this file for security issues"
"Scan the backend for vulnerabilities"
"Run a full security audit"
"Check my CDK code for security problems"
"Scan for secrets and credentials"
"Check for dependency vulnerabilities"
"Run security check on backend/lambda/handler.py"
```

---

## Additional Resources

### Documentation
- [cdk-nag GitHub](https://github.com/cdklabs/cdk-nag)
- [cdk-nag Rules](https://github.com/cdklabs/cdk-nag/blob/main/RULES.md)
- [ASH Documentation](https://awslabs.github.io/automated-security-helper/)
- [ASH GitHub](https://github.com/awslabs/automated-security-helper)

### CIC Steering Files
- `.kiro/steering/security-practices.md` - Security best practices
- `.kiro/steering/backend-standards` - CDK security patterns
- `.kiro/steering/CIC-coding-standards` - Core security principles

### Related Tools
- [cfn-nag](https://github.com/stelligent/cfn_nag) - CloudFormation linter
- [Checkov](https://www.checkov.io/) - IaC security scanner
- [Bandit](https://bandit.readthedocs.io/) - Python security linter
- [Semgrep](https://semgrep.dev/) - Multi-language SAST

---

**Last Updated**: February 13, 2026  
**Hook Version**: 1.0.0  
**Recommended for**: All CIC projects
