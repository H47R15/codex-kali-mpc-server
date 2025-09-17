# Security Policy

The Kali Security MCP Server interacts with penetration-testing utilities, so we take security issues seriously. Thank you for taking the time to responsibly disclose vulnerabilities.

## Supported Versions

We release through semantic-release. The latest `main` branch and the most recent tagged release receive security fixes. Older releases may be patched if the issue is critical and the fix is low-risk, but we generally recommend upgrading to the newest version.

## Reporting a Vulnerability

1. Create a draft security advisory at <https://github.com/H47R15/codex-kali-mpc-server/security/advisories/new>.
2. Provide the following details:
   - A description of the issue
   - Steps to reproduce (scripts, payloads, or sample requests)
   - Impact assessment (what could an attacker achieve?)
   - Any suggested fixes or mitigations
3. If you cannot use GitHub's advisory workflow, email the maintainers at the address listed in `CODEOWNERS` via the "Email" option on their GitHub profile.

Please do **not** open public GitHub issues for security-sensitive reports.

## What to Expect

- We aim to acknowledge new reports within **2 business days**.
- You can expect regular status updates at least once every **7 days** until the issue is resolved.
- Once a fix is ready, we will coordinate a disclosure timeline with you. Our goal is to release a patch before making details public.

## Preferred Communication

Keep communications encrypted if possible. GitHub's private advisory workflow supports encrypted attachments; if you need an alternative channel, mention it in your initial report and we will work with you to establish a secure link.

## Public Disclosure

We will publish security advisories through GitHub once a fix is available and credit reporters who want to be acknowledged. If you believe the issue is already being exploited in the wild, let us know so we can prioritise accordingly.
