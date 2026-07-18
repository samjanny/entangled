# Security policy

The Entangled specification and conformance corpus define security-sensitive
cryptographic, parsing, origin-binding, trust, and state-management behavior.

## Reporting a vulnerability

Do not open a public issue or discussion for a suspected vulnerability.

1. Prefer [GitHub private vulnerability reporting](https://github.com/samjanny/entangled/security/advisories/new).
2. If that channel is unavailable, email `samjanny@gmail.com` with a subject
   beginning `[entangled security]`.

Include the affected specification revision or commit, the relevant section or
corpus vector, the security consequence, and any known constraints on
exploitability. Do not include sensitive payloads in public channels.

## Response targets

The maintainers aim to acknowledge reports within 3 business days and provide
an initial assessment within 7 business days. Fix and disclosure timing will be
coordinated privately, with a 90-day disclosure window as the default maximum.

## Scope

In scope are normative protocol ambiguities, security-relevant contradictions,
conformance corpus errors, deterministic generator defects, and repository
supply-chain configuration. Implementation-specific defects should be reported
to the affected implementation repository unless the specification caused or
permits the unsafe behavior.
