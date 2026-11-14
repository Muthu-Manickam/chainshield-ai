---
type: decision
status: accepted
date: 2026-11-15
---
# ADR-005 Auth in FastAPI

**Status:** accepted

## Decision
Email + password auth owned by FastAPI with three roles.

## Context
Dashboards need real users; keeping auth in the only backend avoids a second auth system.

## Details
pwdlib argon2 hashes, PyJWT token in an httpOnly cookie. Roles: analyst, supervisor, admin.

## Alternatives rejected
Auth.js / Clerk (needs Next.js or a SaaS).

## Related
- [[Auth and users]]
