---
inclusion: always
---

# External Tool Usage Standards (Powers & MCP)

**CRITICAL**: External tools (Kiro Powers and MCP servers) provide access to official documentation, best practices, validation tools, and specialized capabilities. You MUST use these tools proactively BEFORE writing code, not reactively after encountering issues.

## Core Principle

External tools are like checking official documentation before implementing — not debugging tools for after you've already written code. Use them to inform your implementation, not to fix it later.

## Tool Discovery

- **Powers**: Run `kiroPowers list` to see installed powers
- **MCP Tools**: Check available MCP tools through the MCP interface
- **Documentation**: See `.kiro/steering/README.md` for recommended tool configurations

Common tool categories:
- Infrastructure/IaC documentation and validation
- Observability and monitoring
- Security and IAM policy analysis
- Design system integration
- API documentation and code examples

## Workflow: Check Tools BEFORE Writing Code

**Trigger keywords:** infrastructure, cloud, aws, monitoring, security, iam, policy, api, integration, design, ui

**Process:**
1. See relevant keywords → Check for Powers/MCP tools (`kiroPowers list`)
2. Query tools for best practices and requirements
3. Write code incorporating guidance
4. Use tools throughout implementation (not just once)

## When to Use External Tools

**Infrastructure/Cloud:** Before writing IaC, configuring services, defining policies
**Observability:** When setting up monitoring, investigating performance, analyzing logs
**Security:** Before finalizing policies, implementing auth, configuring secrets
**Design/Frontend:** Before implementing UI, creating components, accessibility features
**APIs/Integration:** When integrating third-party services, learning frameworks

## Proactive vs Reactive

❌ **REACTIVE:** Write code → Get errors → Check tools → Fix
✅ **PROACTIVE:** See keywords → Check tools → Query best practices → Write correct code

## Common Mistakes

1. Waiting until stuck (check at START, not when debugging)
2. Checking but not querying (discover AND use tools)
3. One-time check (use throughout implementation)
4. Ignoring keywords (infrastructure/security/monitoring = check tools)
5. Treating as optional (MANDATORY for specialized work)

## Summary

External tools are design tools, not debugging tools. Check them BEFORE writing code, just like checking dependency versions before writing package.json. Keywords in task = check for relevant tools first.