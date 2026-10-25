# Security Policy

## Reporting Security Issues

We take the security of the Epoxa Voice AI platform seriously. If you discover a vulnerability, please report it responsibly by contacting:

**Email:** security@epoxcel.com  
**PGP Key:** Available upon request.

Please do **NOT** file public GitHub issues for security vulnerabilities. We will respond within 24 hours and provide an estimated remediation timeline.

---

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Security Architecture & Design Guarantees

1. **Row Level Security (RLS) Enforced**: Direct PostgreSQL table access from client-side Supabase anonymous or authenticated roles is completely revoked. All business operations route through the FastAPI application layer with scoped Unit-of-Work boundaries.
2. **Least-Privilege Roles**: Application processes connect as `epoxa_api` or `epoxa_agent` roles with minimum necessary grants. Direct execution as the `postgres` superuser is strictly prohibited in production.
3. **Zero Secrets in Source or Client Bundles**: All credentials are provided through environment variables managed by `pydantic-settings` as `SecretStr`. Frontend build artifacts are verified free of secret tokens.
4. **Rate Limiting & Abuse Protection**: Public call-start endpoints enforce per-IP rate limits and a global concurrent-call cap to prevent denial-of-wallet attacks.
5. **PII Redaction**: Transcripts and log messages redact phone numbers, emails, and sensitive authentication headers using structured JSON logging.
