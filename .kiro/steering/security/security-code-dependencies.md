---
inclusion: fileMatch
fileMatchPattern: "**/lambda/**/*.py,**/requirements.txt,**/package.json,**/package-lock.json,**/lambda/**/*bedrock*,**/lambda/**/*ai*"
---

# Security: Code & Dependencies

Code security, dependency management, and AI/GenAI security best practices for CIC projects.

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
