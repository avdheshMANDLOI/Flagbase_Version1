# FlagBase — Production-Inspired Feature Flag & A/B Testing Platform
## Project Specification Document (SRS + Technical Design)

**Version:** 2.0  
**Author:** Avdhesh (IIIT Vadodara, CSE — 3rd Year)  
**Status:** Living Document — update as implementation evolves  
**Last Updated:** June 2026

---

> This document is the single source of truth for the FlagBase project. Every architectural decision, design choice, data model, API contract, and development plan is recorded here. Any AI assistant, collaborator, or future-you reading this document should be able to fully understand and continue development without additional context.
>
> **This is a learning project, not a startup.** FlagBase is a student engineering project built to teach real backend development concepts, produce a finished and resume-worthy artifact, and demonstrate sound architectural judgment in interviews. It is explicitly **production-inspired**, not production-grade — the goal is to build like a real software company would (deployable, tested, documented versions shipped incrementally), not to replicate a commercial platform like LaunchDarkly feature-for-feature.

---

## Table of Contents

0. [Project Scope (Read This First)](#0-project-scope)
1. [Project Vision](#1-project-vision)
2. [Functional Requirements](#2-functional-requirements)
3. [Non-Functional Requirements](#3-non-functional-requirements)
4. [System Architecture](#4-system-architecture)
5. [Folder Structure](#5-folder-structure)
6. [Technology Stack](#6-technology-stack)
7. [Database Design](#7-database-design)
8. [API Design](#8-api-design)
9. [Authentication Architecture](#9-authentication-architecture)
10. [Redis Design](#10-redis-design)
11. [Evaluation Engine](#11-evaluation-engine)
12. [React Dashboard](#12-react-dashboard)
13. [Python SDK](#13-python-sdk)
14. [Analytics Engine](#14-analytics-engine)
15. [A/B Testing Engine](#15-ab-testing-engine)
16. [Deployment Architecture](#16-deployment-architecture)
17. [Logging Strategy](#17-logging-strategy)
18. [Testing Strategy](#18-testing-strategy)
19. [CI/CD Pipeline](#19-cicd-pipeline)
20. [Monitoring](#20-monitoring)
21. [Documentation Plan](#21-documentation-plan)
22. [Development Roadmap](#22-development-roadmap)
23. [Future Improvements](#23-future-improvements)
24. [Engineering Best Practices](#24-engineering-best-practices)
25. [Interview Preparation Notes](#25-interview-preparation-notes)

---

## 0. Project Scope

This section is the first thing any contributor — human or AI — should read. It governs every decision in this document. Sections below describe the **full long-term architecture**; this section tells you which parts of that architecture belong in which version, and why.

### 0.1 Why versions exist

The original draft of this specification combined everything FlagBase could ever be — auth, evaluation engine, caching, analytics, A/B testing, teams, RBAC, enterprise infra — into a single undifferentiated plan. That is a realistic spec for a *company*, not for one student with a semester's worth of evenings. Building it all at once is the most common way ambitious student projects die: 80% finished forever, nothing ever shippable, nothing to actually put on a resume or discuss in an interview.

So the project is split into five versions. Each version must be independently:

- **Deployable** — it runs, end to end, somewhere a stranger could reach it
- **Complete** — no half-built features bleeding into the next version
- **Well tested** — especially the evaluation engine, which is the heart of the project
- **Well documented** — README + architecture notes good enough that *you*, six months later, could re-onboard yourself
- **Resume-worthy** — a recruiter or interviewer looking at this version alone should see real engineering judgment

### 0.2 The three-question filter

Every feature in this document was placed in its version by asking three questions. If the answer to *any* of them is "no," the feature is pushed to a later version:

1. **Does it teach an important engineering concept?** (Not "is it cool," but "will I understand something about backend systems I didn't before?")
2. **Does it meaningfully improve the project for interviews and the resume?**
3. **Can a single student, learning concurrently, realistically finish it without the project stalling?**

This filter is also useful **in interviews**: when asked "why doesn't FlagBase have X yet," the honest answer is "I scoped it deliberately — X didn't pass the third question for v1, here's where it lives in the roadmap and why." That is a stronger answer than either not having thought about X, or having an unfinished half-implementation of it.

### 0.3 Version map

**FlagBase v1 — the placement-ready core.** Everything needed for a flag to be created, targeted, rolled out, and evaluated correctly, with one real environment, behind real auth, with a real SDK and a real (if simple) dashboard. This is the version that must exist for the project to be "done" in any meaningful sense. Scope: authentication (register/login/JWT/protected routes), single-environment projects, full flag CRUD, the complete evaluation engine (kill switch → exclude → include → percentage rollout) with deterministic MurmurHash bucketing, the targeting rules engine (user_id, email, country, custom_attributes — scoped to equality/list operators only), API key auth, a minimal Python SDK (`is_enabled()` and `track()` only — no polling, no streaming), a six-screen dashboard (Login, Projects, Project Dashboard, Flags, API Keys, Account), Docker deployment, and comprehensive tests for the evaluation engine specifically.

*Deliberately deferred from the original draft:* multi-environment support (Dev/Staging/Production) was originally planned for v1 but has been moved to v2. Modeling environments properly — separate flag states per environment, environment-scoped API keys, promotion workflows — is a real feature with real schema and evaluation-engine implications, not a one-line addition. Doing it properly is worth more (questions 1 and 2) than doing it as a thin tag with no real semantics, but doing it properly inside v1 risks question 3. v2 groups it with the other "make this production-shaped" work, which is where it belongs conceptually anyway.

**FlagBase v2 — production engineering.** Once the core works, this version is about everything that makes a system survive contact with reality: Redis caching on the evaluation path, structured logging, rate limiting, background tasks for event writes, pagination and better filtering on list endpoints, audit logs, and **multi-environment support** (moved here from the original v1 plan — see above).

**FlagBase v3 — platform capabilities.** Analytics (evaluation counts, time series, charts), evaluation history per flag, SDK improvements (polling/caching refinements), notifications, and webhooks. This is the version where FlagBase stops being just a flag store and starts being something a team would actually want a dashboard for.

**FlagBase v4 — A/B testing.** The entire experimentation system: variants, conversion tracking, the statistical significance engine (two-proportion z-test), winner selection, and the experiment dashboard. This was originally folded into the core build; it is substantial enough (its own data model, its own statistics, its own UI) to be a standalone version with its own "is it done" bar.

**FlagBase v5 — enterprise features.** Teams, RBAC, invitations, Kubernetes deployment, additional SDKs (JavaScript), WebSockets/streaming evaluation, OpenFeature compatibility, SSO, and other infrastructure that matters at company scale but not at student-project scale. This version mostly exists to show the roadmap has a ceiling worth aiming at — it is not expected to be built during the core placement-prep timeline.

### 0.4 How to read the rest of this document

Sections 1–25 below describe the **full long-term system** — they are intentionally not re-segmented version-by-version inline, because the architecture (schema, API shape, evaluation algorithm) is designed to extend cleanly rather than be rebuilt per version. Instead:

- Where a section's scope spans multiple versions, a **Scope note** at the top of the section states what's in v1 vs. deferred.
- The **Development Roadmap** (Section 22) and **Future Improvements** (Section 23) sections are the authoritative version-by-version breakdown — if you want "what do I build this week," go there.
- Treat every other section as describing the destination, not the next sprint.

---

## 1. Project Vision

### 1.1 Purpose

FlagBase is an open-source, self-hostable feature flag and A/B testing platform. It enables software development teams to decouple feature releases from code deployments — giving engineers the ability to turn features on or off for any subset of users at any time, without redeploying their application.

### 1.2 Problem Statement

Modern product engineering teams face a fundamental challenge: deploying code to production is risky. A new feature that works perfectly in staging may behave unexpectedly under real production load, with real users, at scale. The traditional solution — "test more before deploying" — does not eliminate risk; it only delays it.

Feature flags solve this by separating *deployment* from *release*. Code is deployed to production but kept hidden behind a flag. The feature is then gradually exposed to users — 1% first, then 5%, then 50%, then 100% — while engineers monitor for errors. If something breaks, the flag is turned off instantly. No rollback. No emergency deployment. No downtime.

Beyond risk mitigation, feature flags enable:
- **Gradual rollouts** — control exactly what percentage of users see a new feature
- **Targeted releases** — enable features only for beta users, premium subscribers, or specific geographies
- **Kill switches** — instantly disable a broken feature in production with one click
- **A/B testing** — show two variants to different user groups and measure which performs better
- **Canary releases** — release to internal employees first, then expand

### 1.3 Goals

**Primary Goal:** Build a production-inspired, self-hostable feature flag platform with a Python SDK that developers can integrate in two lines of code. (See [Section 0: Project Scope](#0-project-scope) for what "production-inspired" means and why it replaces "production-grade.")

**Secondary Goals:**
- Deliver flag evaluations in under 1 millisecond (p99 latency)
- Support gradual rollouts from 0% to 100% with consistent user bucketing
- Provide a clean, professional dashboard for non-technical users to manage flags
- Publish a pip-installable Python SDK to PyPI
- Enable A/B testing with statistically rigorous winner selection *(v4 — see Section 0)*
- Make the entire platform open-sourceable on GitHub

**Portfolio Goals:**
- Demonstrate full-stack engineering capability (backend, frontend, SDK, infrastructure)
- Show knowledge of systems used daily at product companies (Swiggy, Razorpay, CRED, Zepto)
- Produce a project that can be discussed in real depth during technical interviews
- Demonstrate Python expertise aligned with concurrent AI/ML learning

### 1.4 Target Users

**Primary Users (SDK consumers):**
- Backend Python developers who want to wrap new features behind flags
- Full-stack developers building web applications with gradual rollout requirements
- Startups that cannot afford LaunchDarkly ($500+/month) but need professional flag management

**Secondary Users (Dashboard consumers):**
- Product managers who need to control rollouts without engineering involvement
- Engineering leads running A/B tests and monitoring results
- QA engineers enabling features for specific test user accounts

**Tertiary Users (Self-hosters):**
- Developers and companies wanting to run the entire platform on their own infrastructure
- Open-source contributors improving the platform

### 1.5 Why This Project Exists

**The gap in the market:**
- LaunchDarkly: Industry standard, but starts at $8/seat/month — unaffordable for indie developers and early-stage startups
- Unleash: Open source, but has a complex setup and outdated UI
- Flagsmith: Good open source option but limited A/B testing capability
- GrowthBook: A/B testing focused but weak on flag management primitives

FlagBase targets the gap: a clean, modern, open-source platform with a developer-first Python SDK and built-in A/B testing — free to self-host, with no seat limits.

**The resume angle:**
Feature flags are used at every serious product company daily. Building this platform from scratch demonstrates understanding of one of the core internal tools that powers modern software delivery. This is not a CRUD application. It requires knowledge of distributed systems concepts (consistent hashing, cache invalidation), statistics (z-tests, p-values), real-time systems (WebSocket streaming), and SDK design — all simultaneously.

### 1.6 Real-World Inspiration

| Platform | What We Learned From It |
|----------|------------------------|
| **LaunchDarkly** | Dashboard UX, targeting rules model, SDK API design (is_enabled pattern), multi-environment support |
| **Unleash** | Open-source self-hosting model, activation strategies (gradual rollout, user IDs, IPs) |
| **Flagsmith** | Clean dashboard design, API key per environment pattern |
| **GrowthBook** | Statistical significance UI, Bayesian vs frequentist A/B test approaches |
| **PostHog** | Feature flags tied directly to analytics events, cohort-based targeting |

---

## 2. Functional Requirements

> **Scope note:** Requirements below are tagged `[v1]`, `[v2]`, `[v3]`, `[v4]`, or `[v5]` where a whole table or individual row belongs to a later version. Untagged rows are v1. See [Section 0](#0-project-scope) for the full version map.

### 2.1 User Management `[v1]`

| ID | Requirement |
|----|-------------|
| UM-01 | User can register with email and password |
| UM-02 | User can log in and receive a JWT access token |
| UM-03 | User can log out (client-side token deletion) |
| UM-04 | User can update their profile (name, email) |
| UM-05 | User can change their password (requires current password) |
| UM-06 | User can delete their account |
| UM-07 | Passwords must be hashed with bcrypt (minimum 12 rounds) |
| UM-08 | JWT tokens expire after 24 hours |
| UM-09 | Email addresses must be unique across the platform |

### 2.2 Project Management `[v1, single environment]`

| ID | Requirement |
|----|-------------|
| PM-01 | User can create a project (name, description, optional slug) |
| PM-02 | User can view all their projects on a dashboard |
| PM-03 | User can update project name and description |
| PM-04 | User can delete a project (cascades to all flags, API keys, events) |
| PM-05 | Each project has a unique slug used in SDK initialisation |
| PM-06 | A user can own multiple projects |
| PM-07 | `[v2]` Projects support multiple environments (Development / Staging / Production) with separate flag states per environment and environment-scoped API keys |
| PM-08 | `[v5]` Users can invite teammates to a project (teams, roles, RBAC) |

### 2.3 API Key Management `[v1]`

| ID | Requirement |
|----|-------------|
| AK-01 | Each project can have multiple API keys |
| AK-02 | User can generate a new API key for a project |
| AK-03 | API keys are displayed only once at creation time (stored as hash) |
| AK-04 | User can revoke (delete) an API key |
| AK-05 | User can give each API key a label (e.g., "Production", "Staging") |
| AK-06 | API keys are prefixed: `proj_sk_` for server-side keys |
| AK-07 | API key authentication is separate from JWT authentication |

### 2.4 Flag Management `[v1]`

| ID | Requirement |
|----|-------------|
| FM-01 | User can create a feature flag within a project |
| FM-02 | Each flag has: name (slug-style), display name, description, is_enabled, rollout_percentage |
| FM-03 | Flag names must be unique within a project |
| FM-04 | Flag names must be lowercase, alphanumeric with underscores/hyphens only |
| FM-05 | User can toggle a flag on/off via a dashboard toggle (master kill switch) |
| FM-06 | User can set rollout percentage (0–100) with a slider or input field |
| FM-07 | User can update flag description |
| FM-08 | User can delete a flag (soft delete preferred, with confirmation) |
| FM-09 | User can view a list of all flags for a project with their current status |
| FM-10 | Flag list shows: name, status, rollout %, last modified date, evaluation count |
| FM-11 | User can search/filter flags by name or status |
| FM-12 | Turning a flag off instantly overrides all rules and rollout — 100% of users get false |
| FM-13 | Rollout percentage of 100 means all users who are not excluded by rules get true |
| FM-14 | Rollout percentage of 0 means no users get true (unless matched by an explicit rule) |

### 2.5 Targeting Rules `[v1, scoped]`

> **v1 scope note:** the original draft listed `contains` as a rule operator and left `custom_attribute` open-ended (any value type, any comparison). Both are scoped down for v1: operators are limited to `equals`, `not_equals`, `in_list`, `not_in_list` (no substring `contains` — that's a v2 nice-to-have), and `custom_attribute` is restricted to **string equality/list-membership only** (no numeric ranges, no nested objects). This keeps the rules engine's contract small and fully testable in v1 while leaving room to extend the operator set later without a schema change (operator and value are already columns, not hardcoded logic).

| ID | Requirement |
|----|-------------|
| TR-01 | User can add one or more targeting rules to a flag |
| TR-02 | Rule types supported: `user_id`, `email`, `country`, `custom_attribute` |
| TR-03 | Rule operators (v1): `equals`, `not_equals`, `in_list`, `not_in_list`. `[v2]` `contains` and numeric/range operators |
| TR-04 | Rules are evaluated before rollout percentage |
| TR-05 | If a user matches any rule marked as "include", they receive true |
| TR-06 | If a user matches any rule marked as "exclude", they receive false (overrides rollout) |
| TR-07 | Rules are evaluated in priority order (user-defined ordering) |
| TR-08 | User can delete individual rules |
| TR-09 | `[v2]` User can reorder rules via drag-and-drop in the dashboard (v1: reorder by editing `priority` value directly, no drag-and-drop UI) |

### 2.6 Flag Evaluation (Core SDK Functionality) `[v1 — do not simplify]`

> This is the heart of the project. Every row below stays in v1 at full fidelity — this is the one area where the three-question filter should bias toward keeping scope, not cutting it.

| ID | Requirement |
|----|-------------|
| FE-01 | SDK can evaluate whether a flag is enabled for a given user_id |
| FE-02 | Evaluation returns: `{enabled: bool, variant: str, reason: str}` |
| FE-03 | Reason values: `"flag_disabled"`, `"rule_match_include"`, `"rule_match_exclude"`, `"rollout_included"`, `"rollout_excluded"`, `"flag_not_found"` |
| FE-04 | Same user_id always gets the same result for the same flag (consistency guarantee) |
| FE-05 | Evaluation must work correctly for rollout percentages of 0, 1, 10, 50, 99, 100 |
| FE-06 | SDK supports optional context object: `{user_id, email, country, custom_attributes: dict}` |
| FE-07 | If flag is not found, SDK returns `{enabled: false, reason: "flag_not_found"}` |
| FE-08 | SDK caches flag state locally for 30 seconds (configurable) |
| FE-09 | SDK falls back to `enabled: false` if the server is unreachable |
| FE-10 | SDK supports a `default_value` parameter for graceful degradation |

### 2.7 A/B Test Management `[v4]`

> Moved in full to v4. This is a substantial, self-contained system — its own data model (`ab_tests`, `ab_variants`), its own statistics engine, and its own dashboard UI. Building it alongside the v1 core would roughly double the surface area of the first release. See [Section 15](#15-ab-testing-engine) for the full design, which remains unchanged from the original draft.

| ID | Requirement |
|----|-------------|
| AB-01 | User can create an A/B test attached to an existing flag |
| AB-02 | Each A/B test has: name, hypothesis, variants (minimum 2), metric to track |
| AB-03 | Variants are: `control` (users who see old behaviour) and one or more `treatment` variants |
| AB-04 | Variant traffic allocation must sum to 100% |
| AB-05 | User can define a primary conversion metric (event name to track) |
| AB-06 | User can start and stop an A/B test independently of the flag's enabled state |
| AB-07 | A/B test results show: users per variant, conversion rate, lift, confidence level |
| AB-08 | Platform calculates statistical significance automatically |
| AB-09 | Dashboard shows whether results are statistically significant (default: 95% confidence) |
| AB-10 | User can declare a winner, which locks the winning variant |
| AB-11 | A/B test history is preserved after conclusion |

### 2.8 Analytics

> **Split scope:** raw event recording (AN-01, AN-02, AN-07, AN-08) is v1 — the SDK's `track()` method and the evaluation engine's event write are core v1 functionality, and the `evaluation_events` / `conversion_events` tables are needed from day one even though nothing displays them yet. The dashboard-facing analytics (AN-03–AN-06: charts, time series, top-flags views) are v3. v1's dashboard shows only a simple count, per Section 0.3.

| ID | Requirement | Version |
|----|-------------|---------|
| AN-01 | Platform tracks every flag evaluation event | v1 |
| AN-02 | Evaluation events stored: flag_id, user_id (hashed for privacy), result, reason, timestamp | v1 |
| AN-03 | Dashboard shows evaluation count per flag over last 7 days / 30 days (time series + chart) | v3 |
| AN-04 | Dashboard shows unique users exposed to each flag | v3 |
| AN-05 | Dashboard shows flag enable/disable history (audit log per flag) | v2 (audit log) |
| AN-06 | Dashboard shows top flags by evaluation volume | v3 |
| AN-07 | SDK can send custom conversion events via `client.track(event_name, user_id)` | v1 |
| AN-08 | Conversion events stored: event_name, user_id (hashed), flag_id, variant, timestamp | v1 |

v1's dashboard only needs a raw total-evaluations count per flag (a single number, computed with a `COUNT(*)` query — no time-series, no chart library). That satisfies "Analytics should initially only show simple counts" without requiring any of the v3 analytics API.

### 2.9 Dashboard Capabilities (Complete List)

> **v1 dashboard is six pages**, not nine. A/B Test Results and the dedicated Analytics page move to v4 and v3 respectively. Flag Detail is trimmed for v1: it keeps rollout/rules management but drops the evaluation history chart (v3) and A/B test section (v4) — a flag's evaluation count appears only as the single number described in 2.8.

| Page | Capabilities | Version |
|------|-------------|---------|
| Login / Register | Email + password auth, redirect to dashboard on success | v1 |
| Projects Overview | List all projects, create project, delete project, navigate into project | v1 |
| Project Dashboard | Flag list, quick stats (total flags, active flags, total evaluations today as a count) | v1 |
| Flag List | List, search, filter by status, toggle on/off, create flag button | v1 |
| Flag Detail | Edit name/description, rollout slider, rules management | v1 |
| Flag Detail (extended) | + evaluation history chart | v3 |
| Flag Detail (extended) | + A/B test section | v4 |
| API Keys | List keys (masked), create key (shown once), revoke key, label keys | v1 |
| Account Settings | Update profile, change password, delete account | v1 |
| A/B Test Results | Variant comparison table, confidence level indicator, declare winner button | v4 |
| Analytics | Evaluation charts per flag, event volume over time | v3 |

---

## 3. Non-Functional Requirements

### 3.1 Performance

| Metric | Target | Rationale |
|--------|--------|-----------|
| Flag evaluation latency (p50) | < 0.5ms | Called on every page load in user apps |
| Flag evaluation latency (p99) | < 1ms | Must not add perceptible latency to host application |
| Dashboard API response time (p95) | < 200ms | Standard SaaS dashboard expectation |
| SDK local cache hit response | < 0.1ms | In-memory dictionary lookup |
| Event ingestion throughput | 1,000 events/second | Support medium-scale production apps |
| Redis cache hit rate | > 95% | Postgres should rarely be hit during evaluations |

### 3.2 Scalability

- The evaluation endpoint must be stateless — horizontal scaling by adding more FastAPI instances behind a load balancer
- Redis acts as the shared state layer — all instances read from the same Redis
- Event ingestion should be buffered via an async write queue to prevent DB write bottlenecks
- Database indexes on all hot query paths (flag lookups by project_id + name, events by flag_id + timestamp)
- Future: read replicas for Postgres when analytics queries become expensive

### 3.3 Reliability

| Requirement | Implementation |
|-------------|---------------|
| SDK graceful degradation | Returns `default_value` (false) if server unreachable |
| SDK retry logic | Exponential backoff: 100ms, 200ms, 400ms — max 3 retries |
| Cache stale-while-revalidate | Serve stale flag data while fetching fresh data in background |
| Database connection pooling | SQLAlchemy connection pool: min 5, max 20 connections |
| Health check endpoint | GET /health returns 200 with DB and Redis status |

### 3.4 Security

| Requirement | Implementation |
|-------------|---------------|
| Password hashing | bcrypt with 12 rounds minimum |
| JWT signing | HS256 algorithm, secret from environment variable |
| API key storage | Stored as SHA-256 hash; plaintext shown only at creation |
| API key transmission | Must be sent via Authorization header, not query params |
| SQL injection prevention | SQLAlchemy ORM parameterised queries only — no raw string interpolation |
| CORS | Restrict to known frontend origin in production |
| Rate limiting | 100 requests/minute per API key on evaluation endpoint |
| User data privacy | user_id stored as SHA-256 hash in analytics events |
| HTTPS only | Enforce TLS in production; HTTP only acceptable in local development |
| Input validation | All inputs validated via Pydantic schemas before reaching business logic |

### 3.5 Availability

- Target: 99.5% uptime (acceptable for a self-hosted open-source tool)
- Railway's managed Postgres and Redis provide automatic failover
- Multiple FastAPI workers per deployment (minimum 2 Uvicorn workers)
- Zero-downtime deploys via Railway's rolling deploy feature

### 3.6 Maintainability

- All business logic lives in `services/` layer, not in route handlers
- Route handlers only: validate input → call service → return response
- No raw SQL anywhere — all DB access via SQLAlchemy models
- All configuration via environment variables, no hardcoded values
- Type hints on all function signatures
- Docstrings on all public functions and classes

---

## 4. System Architecture

> **Scope note:** the diagram and flows below show the **full, long-term architecture** (Redis, rate limiting, A/B Test Router included) — this is the destination, not v1. In v1: no Redis box (the Application Layer talks to PostgreSQL only), no A/B Test Router, no Analytics Router (a minimal count query lives inside the Flag Router instead), and step 4 of the Flag Evaluation Request Flow below reads directly from Postgres rather than checking Redis. The Rate Limiting Middleware in 4.3 is also v2. Everything else (CORS, request logging, JWT/API key auth, the core evaluation flow) is v1 from day one.

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                   CLIENT LAYER                       │
│   React Dashboard (Vercel)    Developer's App        │
│         (Browser)            (uses Python SDK)       │
└──────────────┬────────────────────┬─────────────────┘
               │ HTTPS/REST         │ HTTPS/REST
               │ JWT Auth           │ API Key Auth
               ▼                    ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Application Layer               │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │  Auth    │ │  Flag    │ │  Evaluation Engine   │ │
│  │  Router  │ │  Router  │ │  (Core Logic)        │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│  │ Project  │ │Analytics │ │   A/B Test Router    │ │
│  │  Router  │ │  Router  │ │                      │ │
│  └──────────┘ └──────────┘ └──────────────────────┘ │
└──────────────┬────────────────────┬─────────────────┘
               │                    │
       ┌───────┴──────┐    ┌────────┴──────┐
       │  PostgreSQL  │    │    Redis      │
       │  (Primary    │    │   (Cache +    │
       │   Storage)   │    │  Rate Limit)  │
       └──────────────┘    └───────────────┘
```

### 4.2 Component Interactions

**Flag Evaluation Request Flow (SDK → Server):**
1. SDK checks local in-memory cache (TTL: 30s). If hit → return immediately.
2. SDK sends `POST /api/v1/evaluate` with `{flag_name, user_id, context}` + API key header.
3. FastAPI middleware validates API key → resolves project_id.
4. Evaluation engine checks Redis for flag state (TTL: 60s). If miss → query Postgres.
5. Evaluation engine runs: kill switch check → rule evaluation → rollout bucketing.
6. Result returned to SDK. Async: evaluation event written to Postgres.
7. SDK caches result locally. Returns `{enabled, variant, reason}` to caller.

**Dashboard Flag Update Flow (Browser → Server):**
1. User clicks toggle on dashboard.
2. React sends `PATCH /api/v1/flags/{flag_id}` with JWT bearer token.
3. FastAPI validates JWT → resolves user_id → checks project ownership.
4. Service updates flag in Postgres.
5. **Cache invalidation:** Redis key for this flag is deleted immediately.
6. Next evaluation call repopulates Redis from Postgres.
7. Dashboard re-fetches flag state and updates UI.

### 4.3 Request Lifecycle (Detailed)

Every incoming request passes through this middleware stack in order:

```
Request
  │
  ▼
1. CORS Middleware (check origin header)
  │
  ▼
2. Request Logging Middleware (log method, path, timestamp)
  │
  ▼
3. Auth Middleware (JWT for /dashboard routes, API key for /evaluate)
  │
  ▼
4. Rate Limiting Middleware (Redis-based sliding window counter)
  │
  ▼
5. Route Handler (validate Pydantic schema)
  │
  ▼
6. Service Layer (business logic)
  │
  ▼
7. Repository Layer (DB queries via SQLAlchemy)
  │
  ▼
8. Response Serialisation (Pydantic response model)
  │
  ▼
Response
```

### 4.4 SDK Workflow

```
Developer Code
  │
  │  client.is_enabled("new_checkout", user_id="user_123")
  ▼
FlagClient.is_enabled()
  │
  ├─ Check local cache (dict lookup)
  │   └─ Cache HIT → return cached value immediately
  │
  └─ Cache MISS
      │
      ▼
      HTTP POST /api/v1/evaluate
      (with API key header)
      │
      ├─ Server reachable → parse response → update local cache → return
      │
      └─ Server unreachable (timeout/error)
          │
          └─ Return default_value (false) — never crash the app
```

### 4.5 Analytics Workflow

```
Flag Evaluation occurs
  │
  ▼
Async background task (FastAPI BackgroundTasks)
  │
  ▼
Write EvaluationEvent to Postgres:
  {flag_id, user_id_hash, result, reason, variant, timestamp}
  │
  ▼
Analytics endpoint queries aggregate:
  SELECT DATE(timestamp), COUNT(*), result
  FROM evaluation_events
  WHERE flag_id = ? AND timestamp > NOW() - INTERVAL '7 days'
  GROUP BY DATE(timestamp), result
  │
  ▼
Dashboard renders time-series chart
```

---

## 5. Folder Structure

### 5.1 Backend Structure

```
flagbase-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app instantiation, middleware, router registration
│   ├── config.py                  # Settings class (reads from .env via pydantic-settings)
│   ├── dependencies.py            # Shared FastAPI dependencies (get_db, get_current_user, get_project)
│   │
│   ├── api/                       # Route handlers ONLY — no business logic here
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py            # POST /auth/register, POST /auth/login
│   │   │   ├── projects.py        # CRUD /projects
│   │   │   ├── flags.py           # CRUD /projects/{id}/flags
│   │   │   ├── rules.py           # CRUD /flags/{id}/rules
│   │   │   ├── api_keys.py        # POST/DELETE /projects/{id}/api-keys
│   │   │   ├── evaluate.py        # POST /evaluate (SDK endpoint)
│   │   │   ├── events.py          # POST /events (SDK track endpoint)
│   │   │   ├── analytics.py       # GET /flags/{id}/analytics
│   │   │   ├── ab_tests.py        # CRUD /flags/{id}/ab-tests
│   │   │   └── health.py          # GET /health
│   │
│   ├── models/                    # SQLAlchemy ORM models (database tables)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── api_key.py
│   │   ├── flag.py
│   │   ├── flag_rule.py
│   │   ├── ab_test.py
│   │   ├── ab_variant.py
│   │   ├── evaluation_event.py
│   │   └── conversion_event.py
│   │
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── auth.py                # RegisterRequest, LoginRequest, TokenResponse
│   │   ├── project.py             # ProjectCreate, ProjectResponse, ProjectUpdate
│   │   ├── flag.py                # FlagCreate, FlagResponse, FlagUpdate, EvaluateRequest, EvaluateResponse
│   │   ├── rule.py                # RuleCreate, RuleResponse
│   │   ├── api_key.py             # APIKeyCreate, APIKeyResponse
│   │   ├── ab_test.py             # ABTestCreate, ABTestResponse, ABTestResults
│   │   ├── analytics.py           # AnalyticsResponse, TimeSeriesPoint
│   │   └── events.py              # TrackEventRequest
│   │
│   ├── services/                  # Business logic — the core of the application
│   │   ├── __init__.py
│   │   ├── auth_service.py        # register_user(), login_user(), hash_password(), verify_password()
│   │   ├── project_service.py     # create_project(), get_projects(), delete_project()
│   │   ├── flag_service.py        # create_flag(), update_flag(), delete_flag(), toggle_flag()
│   │   ├── rule_service.py        # create_rule(), evaluate_rules(), delete_rule()
│   │   ├── api_key_service.py     # generate_api_key(), hash_api_key(), validate_api_key()
│   │   ├── evaluation_service.py  # evaluate_flag() — THE CORE ENGINE
│   │   ├── analytics_service.py   # get_flag_analytics(), get_project_stats()
│   │   ├── ab_test_service.py     # create_ab_test(), calculate_significance(), declare_winner()
│   │   └── cache_service.py       # get_flag_from_cache(), set_flag_cache(), invalidate_flag_cache()
│   │
│   ├── repositories/              # Database query layer — only SQLAlchemy queries here
│   │   ├── __init__.py
│   │   ├── user_repo.py
│   │   ├── project_repo.py
│   │   ├── flag_repo.py
│   │   ├── rule_repo.py
│   │   ├── api_key_repo.py
│   │   ├── event_repo.py
│   │   └── ab_test_repo.py
│   │
│   ├── core/                      # Cross-cutting concerns
│   │   ├── __init__.py
│   │   ├── security.py            # JWT creation/verification, password hashing
│   │   ├── hashing.py             # MurmurHash bucketing, SHA-256 for user_id privacy
│   │   ├── exceptions.py          # Custom exception classes (FlagNotFound, Unauthorized, etc.)
│   │   ├── middleware.py          # CORS, logging, rate limiting middleware
│   │   └── database.py            # SQLAlchemy engine, session factory, Base
│   │
│   └── redis_client.py            # Redis connection pool, get_redis() dependency
│
├── migrations/                    # Alembic migration files
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # pytest fixtures: test_db, test_client, sample_user, sample_flag
│   ├── test_auth.py
│   ├── test_flags.py
│   ├── test_evaluation.py         # Most important test file — all edge cases
│   ├── test_rules.py
│   ├── test_analytics.py
│   └── test_ab_tests.py
│
├── .env.example                   # Template for environment variables
├── .env                           # Local environment (gitignored)
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt           # pytest, black, ruff, mypy
└── README.md
```

### 5.2 Frontend Structure

```
flagbase-frontend/
├── public/
│   ├── favicon.ico
│   └── index.html
│
├── src/
│   ├── main.jsx                   # React app entry point
│   ├── App.jsx                    # Router setup, auth context provider
│   │
│   ├── api/                       # All API call functions (axios wrappers)
│   │   ├── client.js              # Axios instance with base URL + interceptors
│   │   ├── auth.js                # login(), register(), logout()
│   │   ├── projects.js            # getProjects(), createProject(), deleteProject()
│   │   ├── flags.js               # getFlags(), createFlag(), updateFlag(), toggleFlag()
│   │   ├── rules.js               # createRule(), deleteRule()
│   │   ├── apiKeys.js             # getAPIKeys(), createAPIKey(), revokeAPIKey()
│   │   ├── analytics.js           # getFlagAnalytics()
│   │   ├── abTests.js             # getABTest(), createABTest(), declareWinner()
│   │   └── events.js              # trackEvent()
│   │
│   ├── context/
│   │   └── AuthContext.jsx        # Global auth state: user, token, login(), logout()
│   │
│   ├── hooks/                     # Custom React hooks
│   │   ├── useAuth.js
│   │   ├── useFlags.js
│   │   ├── useProjects.js
│   │   └── useAnalytics.js
│   │
│   ├── pages/                     # One file per route/page
│   │   ├── LoginPage.jsx
│   │   ├── RegisterPage.jsx
│   │   ├── ProjectsPage.jsx       # Landing page after login
│   │   ├── ProjectDashboardPage.jsx
│   │   ├── FlagListPage.jsx
│   │   ├── FlagDetailPage.jsx
│   │   ├── APIKeysPage.jsx
│   │   ├── ABTestPage.jsx
│   │   ├── AnalyticsPage.jsx
│   │   └── AccountPage.jsx
│   │
│   ├── components/                # Reusable UI components
│   │   ├── layout/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── Topbar.jsx
│   │   │   └── PageWrapper.jsx
│   │   ├── flags/
│   │   │   ├── FlagCard.jsx
│   │   │   ├── FlagToggle.jsx
│   │   │   ├── RolloutSlider.jsx
│   │   │   ├── RuleBuilder.jsx
│   │   │   └── FlagStatusBadge.jsx
│   │   ├── analytics/
│   │   │   ├── EvaluationChart.jsx
│   │   │   └── StatsCard.jsx
│   │   ├── abtest/
│   │   │   ├── VariantTable.jsx
│   │   │   └── SignificanceMeter.jsx
│   │   └── common/
│   │       ├── Button.jsx
│   │       ├── Modal.jsx
│   │       ├── Toast.jsx
│   │       ├── LoadingSkeleton.jsx
│   │       ├── EmptyState.jsx
│   │       ├── CopyButton.jsx
│   │       └── ConfirmDialog.jsx
│   │
│   └── utils/
│       ├── formatters.js          # Date formatting, number formatting
│       └── validators.js          # Flag name validation (slug format check)
│
├── .env.example
├── .env.local                     # VITE_API_URL=http://localhost:8000
├── vite.config.js
├── tailwind.config.js
├── package.json
└── README.md
```

### 5.3 SDK Structure

```
flagbase-python-sdk/
├── flagbase/
│   ├── __init__.py                # Exports: FlagClient
│   ├── client.py                  # FlagClient class — public API
│   ├── evaluator.py               # Local evaluation logic (cache + HTTP)
│   ├── cache.py                   # In-memory TTL cache (thread-safe)
│   ├── http_client.py             # HTTP calls to FlagBase server (httpx)
│   ├── models.py                  # EvaluationResult, TrackEvent dataclasses
│   ├── exceptions.py              # FlagBaseError, ConnectionError, AuthError
│   └── logger.py                  # SDK internal logging (silent by default)
│
├── tests/
│   ├── test_client.py
│   ├── test_cache.py
│   ├── test_evaluator.py
│   └── test_http_client.py        # Mock HTTP responses
│
├── examples/
│   ├── basic_usage.py
│   ├── flask_integration.py
│   └── fastapi_integration.py
│
├── pyproject.toml                 # Package metadata, build config
├── README.md                      # PyPI landing page — critical for adoption
├── CHANGELOG.md
└── LICENSE                        # MIT License
```

### 5.4 Documentation Structure

```
flagbase-docs/
├── README.md                      # Project overview, quick start
├── docs/
│   ├── getting-started.md         # 5-minute setup guide
│   ├── concepts.md                # Feature flags, rollouts, A/B tests explained
│   ├── self-hosting.md            # Docker Compose deployment guide
│   ├── sdk/
│   │   ├── python.md              # Full Python SDK reference
│   │   └── javascript.md          # Future JS SDK reference
│   ├── api-reference.md           # All endpoints (auto-generated from FastAPI OpenAPI)
│   └── architecture.md            # System design for contributors
└── CONTRIBUTING.md
```

---

## 6. Technology Stack

### 6.1 Backend

| Technology | Version | Purpose | Why Chosen | Alternatives Considered |
|-----------|---------|---------|------------|------------------------|
| **Python** | 3.11+ | Primary language | Aligns with AI/ML learning path. Strong async ecosystem. | Node.js (rejected: breaks Python focus), Go (rejected: too complex for first project) |
| **FastAPI** | 0.110+ | Web framework | Fastest Python web framework. Auto-generates OpenAPI docs. Async-first. Type hints throughout. | Django (too heavy, ORM less modern), Flask (no async, too minimal) |
| **SQLAlchemy** | 2.0+ | ORM | Industry standard Python ORM. Version 2.0 has native async support. | Django ORM (Django-only), SQLModel (FastAPI-native but less mature) |
| **Alembic** | 1.13+ | DB migrations | Standard migrations tool for SQLAlchemy. Explicit version control for schema. | Django migrations (Django-only) |
| **Pydantic** | 2.0+ | Data validation | FastAPI uses Pydantic natively. Validates all request/response data automatically. | Marshmallow (older, more verbose) |
| **aioredis** | 2.0+ | Redis async client | Async Redis client for Python, works with FastAPI's async routes natively. | redis-py (sync only) |
| **python-jose** | 3.3+ | JWT handling | Well-maintained JWT library for Python. HS256 signing. | PyJWT (both acceptable) |
| **passlib[bcrypt]** | 1.7+ | Password hashing | bcrypt is the standard for password hashing. passlib is a clean wrapper. | argon2 (more modern but overkill here) |
| **mmh3** | 4.0+ | MurmurHash | Fast non-cryptographic hash for user bucketing. Used in production flag systems. | hashlib MD5 (cryptographic — unnecessarily slow), FNV hash |
| **httpx** | 0.27+ | HTTP client (SDK) | Async-capable, modern Python HTTP client. Used inside the SDK. | requests (sync only), aiohttp (more complex) |
| **uvicorn** | 0.29+ | ASGI server | Standard production ASGI server for FastAPI. | gunicorn + uvicorn workers (used in production deployment) |
| **pydantic-settings** | 2.0+ | Config management | Reads environment variables with type validation. | python-dotenv (no type validation) |
| **scipy** | 1.12+ | Statistics | z-test calculations for A/B testing statistical significance. | statsmodels (heavier), manual implementation |

### 6.2 Database

| Technology | Version | Purpose | Why Chosen |
|-----------|---------|---------|------------|
| **PostgreSQL** | 15+ | Primary relational database | ACID compliance, strong relational model, excellent indexing, production-standard at every major company. JSON support for custom_attributes. |
| **Redis** | 7+ | Cache + rate limiting | Sub-millisecond reads. Perfect for flag state caching. Also used for rate limiting counters. |

### 6.3 Frontend

| Technology | Version | Purpose | Why Chosen |
|-----------|---------|---------|------------|
| **React** | 18+ | UI framework | Industry standard. Component model fits dashboard well. |
| **Vite** | 5+ | Build tool | Fastest React build tool. Near-instant HMR. |
| **Tailwind CSS** | 3+ | Styling | Utility-first CSS. Fast to build consistent UIs without custom CSS. |
| **shadcn/ui** | latest | Component library | Headless, accessible components styled with Tailwind. Not a dependency — code is owned. |
| **Recharts** | 2+ | Charts | React-native chart library. Clean API, good TypeScript support. |
| **React Router** | 6+ | Client-side routing | Standard React routing. |
| **Axios** | 1.6+ | HTTP client | Interceptors make JWT injection clean. |
| **React Query (TanStack)** | 5+ | Server state management | Handles caching, refetching, loading states for API calls. |

### 6.4 Infrastructure

| Technology | Purpose | Why Chosen |
|-----------|---------|------------|
| **Docker** | Containerise backend | Consistent environments. Required for self-hosting story. |
| **Docker Compose** | Local development + self-host config | One command to spin up backend + Postgres + Redis locally. |
| **Railway** | Host backend + Postgres + Redis | Developer-friendly, generous free tier, managed databases, automatic deploys from GitHub. |
| **Vercel** | Host React frontend | Zero-config React deployment. Global CDN. Free tier sufficient. |
| **GitHub Actions** | CI/CD pipeline | Free for open-source. Standard in industry. |

### 6.5 Development Tools

| Tool | Purpose |
|------|---------|
| **black** | Python code formatter (uncompromising, no config needed) |
| **ruff** | Python linter (replaces flake8, isort, pyupgrade — all in one) |
| **mypy** | Python type checker (enforces type hints) |
| **pytest** | Python test framework |
| **pytest-asyncio** | Async test support for FastAPI routes |
| **httpx** | Test client for FastAPI (replaces requests in tests) |
| **ESLint** | JavaScript linter |
| **Prettier** | JavaScript formatter |

---

## 7. Database Design

> **Scope note:** all nine tables below are part of the long-term schema and can be created in v1's initial migration — this avoids painful schema migrations later. However, only `users`, `projects`, `api_keys`, `flags`, and `flag_rules` need application logic built against them in v1. `ab_tests` and `ab_variants` sit unused until v4. `evaluation_events` and `conversion_events` are written to starting in v1 (so the SDK's `track()` and the evaluation engine work end to end), but are only *read* from starting in v3 (analytics) and v4 (A/B test results).

### 7.1 Tables

#### users
```
Column          Type            Constraints
──────────────────────────────────────────────
id              UUID            PRIMARY KEY, DEFAULT gen_random_uuid()
email           VARCHAR(255)    NOT NULL, UNIQUE
name            VARCHAR(255)    NOT NULL
password_hash   VARCHAR(255)    NOT NULL
is_active       BOOLEAN         NOT NULL, DEFAULT true
created_at      TIMESTAMPTZ     NOT NULL, DEFAULT NOW()
updated_at      TIMESTAMPTZ     NOT NULL, DEFAULT NOW()
```
Indexes: `idx_users_email` (unique index on email — login lookup)

#### projects
```
Column          Type            Constraints
──────────────────────────────────────────────
id              UUID            PRIMARY KEY, DEFAULT gen_random_uuid()
owner_id        UUID            NOT NULL, FOREIGN KEY → users(id) ON DELETE CASCADE
name            VARCHAR(255)    NOT NULL
slug            VARCHAR(100)    NOT NULL, UNIQUE
description     TEXT            NULLABLE
is_active       BOOLEAN         NOT NULL, DEFAULT true
created_at      TIMESTAMPTZ     NOT NULL, DEFAULT NOW()
updated_at      TIMESTAMPTZ     NOT NULL, DEFAULT NOW()
```
Indexes: `idx_projects_owner_id`, `idx_projects_slug` (unique)

#### api_keys
```
Column          Type            Constraints
──────────────────────────────────────────────
id              UUID            PRIMARY KEY
project_id      UUID            NOT NULL, FOREIGN KEY → projects(id) ON DELETE CASCADE
label           VARCHAR(100)    NOT NULL, DEFAULT 'Default'
key_hash        VARCHAR(64)     NOT NULL, UNIQUE  ← SHA-256 hash of the actual key
key_prefix      VARCHAR(20)     NOT NULL           ← e.g. "proj_sk_abc1" (first 12 chars, for display)
is_active       BOOLEAN         NOT NULL, DEFAULT true
last_used_at    TIMESTAMPTZ     NULLABLE
created_at      TIMESTAMPTZ     NOT NULL, DEFAULT NOW()
```
Indexes: `idx_api_keys_key_hash` (for fast authentication lookup), `idx_api_keys_project_id`

#### flags
```
Column                  Type            Constraints
────────────────────────────────────────────────────────
id                      UUID            PRIMARY KEY
project_id              UUID            NOT NULL, FOREIGN KEY → projects(id) ON DELETE CASCADE
name                    VARCHAR(100)    NOT NULL           ← slug format: "new_checkout_ui"
display_name            VARCHAR(255)    NOT NULL
description             TEXT            NULLABLE
is_enabled              BOOLEAN         NOT NULL, DEFAULT false  ← master kill switch
rollout_percentage      INTEGER         NOT NULL, DEFAULT 0, CHECK (0 <= rollout_percentage <= 100)
flag_type               VARCHAR(20)     NOT NULL, DEFAULT 'boolean'  ← 'boolean' or 'multivariate'
is_archived             BOOLEAN         NOT NULL, DEFAULT false
created_at              TIMESTAMPTZ     NOT NULL, DEFAULT NOW()
updated_at              TIMESTAMPTZ     NOT NULL, DEFAULT NOW()

UNIQUE(project_id, name)  ← flag names unique per project
```
Indexes: `idx_flags_project_id`, `idx_flags_project_id_name` (composite unique)

#### flag_rules
```
Column          Type            Constraints
──────────────────────────────────────────────
id              UUID            PRIMARY KEY
flag_id         UUID            NOT NULL, FOREIGN KEY → flags(id) ON DELETE CASCADE
rule_type       VARCHAR(50)     NOT NULL  ← 'user_id', 'email', 'country', 'custom_attribute'
attribute_key   VARCHAR(100)    NULLABLE  ← used when rule_type = 'custom_attribute'
operator        VARCHAR(30)     NOT NULL  ← 'equals', 'not_equals', 'contains', 'in_list', 'not_in_list'
value           JSONB           NOT NULL  ← stores string or array ["user_1","user_2"]
effect          VARCHAR(10)     NOT NULL  ← 'include' or 'exclude'
priority        INTEGER         NOT NULL, DEFAULT 0  ← lower = evaluated first
created_at      TIMESTAMPTZ     NOT NULL, DEFAULT NOW()
```
Indexes: `idx_flag_rules_flag_id`

#### ab_tests
```
Column              Type            Constraints
──────────────────────────────────────────────────
id                  UUID            PRIMARY KEY
flag_id             UUID            NOT NULL, FOREIGN KEY → flags(id) ON DELETE CASCADE
name                VARCHAR(255)    NOT NULL
hypothesis          TEXT            NULLABLE
primary_metric      VARCHAR(100)    NOT NULL  ← event name to track as conversion
status              VARCHAR(20)     NOT NULL, DEFAULT 'draft'  ← 'draft','running','concluded'
winner_variant_id   UUID            NULLABLE, FOREIGN KEY → ab_variants(id)
started_at          TIMESTAMPTZ     NULLABLE
concluded_at        TIMESTAMPTZ     NULLABLE
created_at          TIMESTAMPTZ     NOT NULL, DEFAULT NOW()
```

#### ab_variants
```
Column              Type            Constraints
──────────────────────────────────────────────────
id                  UUID            PRIMARY KEY
ab_test_id          UUID            NOT NULL, FOREIGN KEY → ab_tests(id) ON DELETE CASCADE
name                VARCHAR(50)     NOT NULL  ← 'control', 'variant_a', 'variant_b'
traffic_percentage  INTEGER         NOT NULL  ← must sum to 100 across all variants for a test
description         TEXT            NULLABLE
created_at          TIMESTAMPTZ     NOT NULL, DEFAULT NOW()
```

#### evaluation_events
```
Column          Type            Constraints
──────────────────────────────────────────────
id              BIGSERIAL       PRIMARY KEY  ← bigserial for high write volume
flag_id         UUID            NOT NULL, FOREIGN KEY → flags(id) ON DELETE CASCADE
user_id_hash    VARCHAR(64)     NOT NULL  ← SHA-256 hash of user_id (privacy)
result          BOOLEAN         NOT NULL
reason          VARCHAR(50)     NOT NULL
variant         VARCHAR(50)     NULLABLE  ← populated for A/B tests
ab_test_id      UUID            NULLABLE
timestamp       TIMESTAMPTZ     NOT NULL, DEFAULT NOW()
```
Indexes: `idx_eval_events_flag_id_timestamp` (composite — analytics queries), `idx_eval_events_timestamp`
Partitioning (future): partition by month when volume grows beyond 100M rows

#### conversion_events
```
Column          Type            Constraints
──────────────────────────────────────────────
id              BIGSERIAL       PRIMARY KEY
flag_id         UUID            NOT NULL, FOREIGN KEY → flags(id)
ab_test_id      UUID            NULLABLE, FOREIGN KEY → ab_tests(id)
user_id_hash    VARCHAR(64)     NOT NULL
event_name      VARCHAR(100)    NOT NULL  ← matches primary_metric on ab_tests
variant         VARCHAR(50)     NULLABLE
timestamp       TIMESTAMPTZ     NOT NULL, DEFAULT NOW()
```
Indexes: `idx_conversion_events_flag_id_event_name`, `idx_conversion_events_ab_test_id`

### 7.2 Entity-Relationship Diagram (Text Format)

```
users
  │ (1)
  │ owns
  │ (many)
projects
  │ (1)
  ├──────────────────────────────┐
  │ has                          │ has
  │ (many)                       │ (many)
flags                         api_keys
  │ (1)
  ├──────────────────┬──────────────────┐
  │ has              │ has              │ has
  │ (many)           │ (1)              │ (many)
flag_rules         ab_tests        evaluation_events
                     │ (1)
                     │ has
                     │ (many)
                   ab_variants
                     │ (1)
                     │ referenced by
                   conversion_events
```

### 7.3 Key Design Decisions

**Why UUID for primary keys (not integer)?**
UUIDs prevent enumeration attacks (attacker can't guess sequential IDs), allow client-side ID generation, and work better in distributed systems.

**Why BIGSERIAL for event tables?**
Events are written at very high volume (potentially millions/day). BIGSERIAL (auto-incrementing integer) is faster to insert than UUID generation at high write rates.

**Why JSONB for rule values?**
Rule values can be a single string ("US") or a list (["user_1", "user_2"]). JSONB handles both without needing a separate junction table.

**Why store user_id as a hash in events?**
Privacy by design. We never need to reverse-lookup who a user is from analytics data. Storing hash means we can still count unique users without storing PII.

---

## 8. API Design

> **Scope note:** Auth, Project, Flag, Evaluation, Events, Rules, API Key, and Health routes (8.2–8.4, 8.5–8.8, 8.11) are v1. Analytics Routes (8.9) are v3. A/B Test Routes (8.10) are v4.

### 8.1 Base URL and Versioning

```
Production:  https://api.flagbase.dev/api/v1
Local:       http://localhost:8000/api/v1
```

All responses follow this envelope format:
```json
{
  "success": true,
  "data": { ... },
  "message": "optional message"
}
```

Errors follow:
```json
{
  "success": false,
  "error": {
    "code": "FLAG_NOT_FOUND",
    "message": "Flag 'new_checkout' not found in project",
    "details": {}
  }
}
```

### 8.2 Authentication Routes

**POST /api/v1/auth/register**
- Auth: None
- Request: `{ "email": "user@example.com", "name": "Avdhesh", "password": "min8chars" }`
- Response 201: `{ "user": { "id", "email", "name", "created_at" }, "token": "jwt_string" }`
- Errors: 400 (email already exists), 422 (validation error)
- Validation: email must be valid format; password min 8 chars; name min 2 chars

**POST /api/v1/auth/login**
- Auth: None
- Request: `{ "email": "user@example.com", "password": "password123" }`
- Response 200: `{ "token": "jwt_string", "user": { "id", "email", "name" } }`
- Errors: 401 (invalid credentials), 422 (validation)

**GET /api/v1/auth/me**
- Auth: JWT Bearer
- Request: Header only
- Response 200: `{ "id", "email", "name", "created_at" }`
- Errors: 401 (missing/invalid token)

### 8.3 Project Routes

**GET /api/v1/projects**
- Auth: JWT Bearer
- Response 200: `{ "projects": [ { "id", "name", "slug", "description", "flag_count", "created_at" } ] }`

**POST /api/v1/projects**
- Auth: JWT Bearer
- Request: `{ "name": "My App", "description": "optional" }`
- Response 201: `{ "project": { "id", "name", "slug", "description", "created_at" } }`
- Validation: name 3–100 chars; slug auto-generated from name if not provided

**GET /api/v1/projects/{project_id}**
- Auth: JWT Bearer
- Response 200: Full project object with stats
- Errors: 404, 403 (not owner)

**PATCH /api/v1/projects/{project_id}**
- Auth: JWT Bearer
- Request: `{ "name": "Updated Name", "description": "..." }` (all fields optional)
- Response 200: Updated project object

**DELETE /api/v1/projects/{project_id}**
- Auth: JWT Bearer
- Response 204: No content
- Behaviour: Cascades to all flags, API keys, events

### 8.4 Flag Routes

**GET /api/v1/projects/{project_id}/flags**
- Auth: JWT Bearer
- Query params: `status=enabled|disabled`, `search=keyword`, `page=1`, `limit=20`
- Response 200: `{ "flags": [...], "total": 42, "page": 1 }`

**POST /api/v1/projects/{project_id}/flags**
- Auth: JWT Bearer
- Request: `{ "name": "new_checkout_ui", "display_name": "New Checkout UI", "description": "...", "rollout_percentage": 0 }`
- Response 201: Full flag object
- Validation: name must match `^[a-z0-9_-]+$`; unique within project

**GET /api/v1/flags/{flag_id}**
- Auth: JWT Bearer
- Response 200: Full flag object including rules array

**PATCH /api/v1/flags/{flag_id}**
- Auth: JWT Bearer
- Request: Any subset of `{ "display_name", "description", "is_enabled", "rollout_percentage" }`
- Response 200: Updated flag object
- Side effect: Invalidates Redis cache for this flag

**DELETE /api/v1/flags/{flag_id}**
- Auth: JWT Bearer
- Response 204
- Behaviour: Soft delete (sets is_archived = true). Hard delete as separate endpoint.

### 8.5 Evaluation Route (SDK-Facing)

**POST /api/v1/evaluate**
- Auth: API Key (header: `Authorization: Bearer proj_sk_...`)
- Request:
```json
{
  "flag_name": "new_checkout_ui",
  "user_id": "user_123",
  "context": {
    "email": "user@example.com",
    "country": "IN",
    "custom_attributes": { "plan": "premium", "beta": true }
  }
}
```
- Response 200:
```json
{
  "enabled": true,
  "variant": "control",
  "reason": "rollout_included",
  "flag_name": "new_checkout_ui"
}
```
- Errors: 401 (invalid API key), 404 (flag not found), 429 (rate limited)
- Performance requirement: p99 < 1ms
- Side effect: Async background task writes evaluation_event

### 8.6 Events Route (SDK Tracking)

**POST /api/v1/events**
- Auth: API Key
- Request:
```json
{
  "event_name": "purchase_completed",
  "user_id": "user_123",
  "flag_name": "new_checkout_ui",
  "variant": "treatment"
}
```
- Response 202: `{ "message": "Event received" }` (async — don't wait for DB write)

### 8.7 Rules Routes

**POST /api/v1/flags/{flag_id}/rules**
- Auth: JWT Bearer
- Request: `{ "rule_type": "user_id", "operator": "in_list", "value": ["user_1","user_2"], "effect": "include", "priority": 0 }`
- Response 201: Rule object

**DELETE /api/v1/flags/{flag_id}/rules/{rule_id}**
- Auth: JWT Bearer
- Response 204
- Side effect: Invalidates Redis cache for parent flag

### 8.8 API Key Routes

**GET /api/v1/projects/{project_id}/api-keys**
- Auth: JWT Bearer
- Response 200: List of keys with `key_prefix` shown (not full key)

**POST /api/v1/projects/{project_id}/api-keys**
- Auth: JWT Bearer
- Request: `{ "label": "Production" }`
- Response 201: `{ "key": "proj_sk_abc123xyz...", "label": "Production", "id": "..." }`
- IMPORTANT: `key` is shown only in this response. Never again. Store it immediately.

**DELETE /api/v1/projects/{project_id}/api-keys/{key_id}**
- Auth: JWT Bearer
- Response 204

### 8.9 Analytics Routes `[v3]`

**GET /api/v1/flags/{flag_id}/analytics**
- Auth: JWT Bearer
- Query params: `period=7d|30d|90d`
- Response 200:
```json
{
  "total_evaluations": 45231,
  "unique_users": 8841,
  "enabled_rate": 0.23,
  "time_series": [
    { "date": "2026-06-01", "evaluations": 1240, "enabled": 285 }
  ]
}
```

### 8.10 A/B Test Routes `[v4]`

**POST /api/v1/flags/{flag_id}/ab-tests**
- Auth: JWT Bearer
- Request: `{ "name": "Checkout UI Test", "hypothesis": "New UI increases conversion", "primary_metric": "purchase_completed", "variants": [{"name": "control", "traffic_percentage": 50}, {"name": "treatment", "traffic_percentage": 50}] }`
- Response 201: Full A/B test object

**GET /api/v1/ab-tests/{test_id}/results**
- Auth: JWT Bearer
- Response 200: Results with statistical significance calculations

**POST /api/v1/ab-tests/{test_id}/declare-winner**
- Auth: JWT Bearer
- Request: `{ "variant_id": "uuid" }`
- Response 200: Updated test with winner

### 8.11 Health Route

**GET /health**
- Auth: None
- Response 200: `{ "status": "healthy", "db": "connected", "redis": "connected", "version": "1.0.0" }`
- Response 503: `{ "status": "unhealthy", "db": "error", "redis": "connected" }`

---

*(Sections 9–25 continue below)*

---

## 9. Authentication Architecture

### 9.1 JWT Flow (Dashboard Users)

```
1. User submits email + password to POST /auth/login
2. Server verifies password against bcrypt hash
3. Server generates JWT:
   Payload: { "sub": "user_uuid", "exp": now + 24h, "iat": now, "type": "access" }
   Signed with: HS256 algorithm + SECRET_KEY from environment
4. JWT returned to client
5. Client stores JWT in memory (React state) OR httpOnly cookie
   - Prefer httpOnly cookie in production (prevents XSS)
   - localStorage is acceptable for development
6. Client sends JWT as: Authorization: Bearer <token>
7. FastAPI dependency get_current_user():
   a. Extract token from header
   b. Verify signature using SECRET_KEY
   c. Check expiry
   d. Decode user_id from "sub" claim
   e. Query DB for user (or cache user in Redis by user_id with 5min TTL)
   f. Return user object to route handler
```

### 9.2 API Key Flow (SDK Authentication)

```
1. User generates API key via dashboard → POST /projects/{id}/api-keys
2. Server generates key: "proj_sk_" + secrets.token_urlsafe(32)
3. Server stores: SHA-256(key) in api_keys.key_hash
4. Server stores: first 12 chars of key in api_keys.key_prefix (for display)
5. Full key returned ONCE in response — stored by developer in their .env
6. SDK sends: Authorization: Bearer proj_sk_abc123...
7. FastAPI dependency validate_api_key():
   a. Extract key from header
   b. Compute SHA-256(key)
   c. Query api_keys WHERE key_hash = computed_hash AND is_active = true
   d. Retrieve project_id from matched api_key
   e. Update last_used_at asynchronously
   f. Return project_id to route handler
```

### 9.3 Security Considerations

| Threat | Mitigation |
|--------|-----------|
| Brute force login | Rate limit: 5 failed login attempts per 15 minutes per IP (Redis counter) |
| JWT theft | Short expiry (24h). Future: refresh token rotation pattern. |
| API key exposure | Keys shown once. Stored as hash. Key prefix for identification without exposure. |
| SQL injection | Parameterised queries via SQLAlchemy ORM. No f-string SQL anywhere. |
| XSS | httpOnly cookies for JWT in production. CSP headers. |
| CSRF | SameSite=Strict cookie attribute. CSRF token for state-changing operations. |
| Mass assignment | Pydantic schemas explicitly list allowed fields — no `**kwargs` from request body. |
| Insecure direct object reference | Every resource access checks ownership: `flag.project.owner_id == current_user.id` |

---

## 10. Redis Design `[v2]`

> **Scope note:** Redis caching, the rate limiter, and everything in this section are v2 work — the evaluation engine queries Postgres directly in v1. (Note: the `flagbase:v1:...` prefix inside the cache keys below refers to the *API* version string from Section 8.1, not the project version map in Section 0 — that prefix would remain `v1` even once this caching layer itself ships in project-version v2, since the API hasn't changed.)

### 10.1 Cache Key Structure

All keys follow the pattern: `flagbase:{version}:{type}:{identifier}`

| Key Pattern | Example | Value | TTL | Purpose |
|-------------|---------|-------|-----|---------|
| `flagbase:v1:flag:{project_id}:{flag_name}` | `flagbase:v1:flag:proj_abc:new_checkout` | JSON-serialised flag + rules | 60 seconds | Flag evaluation cache |
| `flagbase:v1:project_flags:{project_id}` | `flagbase:v1:project_flags:proj_abc` | JSON list of all flag names | 300 seconds | Flag list page cache |
| `flagbase:v1:apikey:{key_hash}` | `flagbase:v1:apikey:sha256hash` | JSON `{project_id, is_active}` | 300 seconds | API key auth cache |
| `flagbase:v1:ratelimit:{api_key_prefix}:{minute}` | `flagbase:v1:ratelimit:proj_sk_abc:202406261430` | Integer counter | 60 seconds | Rate limiting |
| `flagbase:v1:user:{user_id}` | `flagbase:v1:user:uuid` | JSON user object | 300 seconds | Auth middleware cache |

### 10.2 Cache Invalidation Strategy

**Flag update (PATCH /flags/{id}):**
1. Update flag in Postgres
2. Delete `flagbase:v1:flag:{project_id}:{flag_name}` from Redis
3. Next evaluation call will cache-miss and repopulate from Postgres
4. Do NOT update Redis directly — repopulate on next read (simpler, no consistency bugs)

**Rule add/delete:**
1. Same as flag update — delete the flag's Redis key
2. Rules are loaded with the flag in the same cache entry

**Project delete:**
1. Delete all Redis keys matching `flagbase:v1:flag:{project_id}:*` (Redis SCAN pattern)
2. Delete `flagbase:v1:project_flags:{project_id}`

**API key revoke:**
1. Delete `flagbase:v1:apikey:{key_hash}` from Redis immediately

### 10.3 Read/Write Flow for Flag Evaluation

```python
async def get_flag_with_cache(project_id, flag_name, redis, db):
    cache_key = f"flagbase:v1:flag:{project_id}:{flag_name}"

    # Try cache first
    cached = await redis.get(cache_key)
    if cached:
        return FlagWithRules.parse_raw(cached)  # cache HIT

    # Cache miss — query Postgres
    flag = await flag_repo.get_by_name(db, project_id, flag_name)
    if not flag:
        return None

    # Populate cache (60 second TTL)
    await redis.setex(cache_key, 60, flag.json())
    return flag
```

### 10.4 Rate Limiting Implementation

Sliding window rate limiting using Redis:
```
Key: flagbase:v1:ratelimit:{api_key_prefix}:{current_minute}
Value: integer counter (INCR)
TTL: 60 seconds

Algorithm:
1. INCR the counter for current minute
2. Set TTL to 60s on first write (EXPIRE only if key is new)
3. If counter > 100: return 429 Too Many Requests
4. Otherwise: proceed
```

---

## 11. Evaluation Engine `[v1 — do not simplify]`

> The most important section in this document. Builds exactly as designed in v1; nothing here is deferred. v1's evaluation path queries Postgres directly (no Redis — that optimization is v2), but the algorithm, rule evaluation, and bucketing logic are unchanged from the original full design.

### 11.1 Complete Algorithm

The evaluation engine is the core of the entire platform. It must be deterministic, fast, and correct.

```
evaluate_flag(flag_name, user_id, context, project_id):

  Step 1: RESOLVE FLAG
  ─────────────────────
  flag = get_flag_with_cache(project_id, flag_name)
  if flag is None:
    return { enabled: false, reason: "flag_not_found" }

  Step 2: MASTER KILL SWITCH
  ──────────────────────────
  if flag.is_enabled == false:
    return { enabled: false, reason: "flag_disabled" }

  Step 3: EVALUATE EXCLUDE RULES (highest priority)
  ───────────────────────────────────────────────────
  for rule in sorted(flag.rules, by=priority) where rule.effect == "exclude":
    if rule_matches(rule, user_id, context):
      return { enabled: false, reason: "rule_match_exclude" }

  Step 4: EVALUATE INCLUDE RULES
  ───────────────────────────────
  for rule in sorted(flag.rules, by=priority) where rule.effect == "include":
    if rule_matches(rule, user_id, context):
      return { enabled: true, reason: "rule_match_include" }

  Step 5: ROLLOUT BUCKETING (consistent hash)
  ────────────────────────────────────────────
  if flag.rollout_percentage == 0:
    return { enabled: false, reason: "rollout_excluded" }

  if flag.rollout_percentage == 100:
    return { enabled: true, reason: "rollout_included" }

  bucket = compute_bucket(flag_name + user_id)  # 0–99
  enabled = bucket < flag.rollout_percentage
  reason = "rollout_included" if enabled else "rollout_excluded"
  return { enabled: enabled, reason: reason }
```

### 11.2 Rule Evaluation

> v1 implements `equals`, `not_equals`, `in_list`, `not_in_list`. The `contains` branch below is `[v2]` — included here for completeness of the long-term design, but not built in v1 (see Section 2.5 for why).

```
rule_matches(rule, user_id, context):

  attribute_value = get_attribute(user_id, context, rule.rule_type, rule.attribute_key)
  rule_value = rule.value  # string or list from JSONB

  match rule.operator:
    "equals":      return attribute_value == rule_value
    "not_equals":  return attribute_value != rule_value
    "in_list":     return attribute_value in rule_value  # rule_value is a list
    "not_in_list": return attribute_value not in rule_value
    "contains":    return rule_value in attribute_value  # substring check — [v2]

get_attribute(user_id, context, rule_type, attribute_key):
  match rule_type:
    "user_id":          return user_id
    "email":            return context.get("email")
    "country":          return context.get("country")
    "custom_attribute": return context.get("custom_attributes", {}).get(attribute_key)
```

### 11.3 Consistent Hashing / Bucketing Algorithm

**Why MurmurHash3 (mmh3)?**
- Non-cryptographic (fast)
- Excellent distribution properties — 10% rollout really gives ~10% of users
- Deterministic — same input always gives same output on any machine
- No need for cryptographic security here

**Implementation:**
```python
import mmh3

def compute_bucket(seed: str) -> int:
    """
    Returns a stable integer 0–99 for any given seed string.
    Seed = flag_name + user_id ensures:
    - Same user sees same result for same flag (consistency)
    - Same user can be in different buckets for different flags (independence)
    """
    hash_value = mmh3.hash(seed, signed=False)  # unsigned 32-bit int
    return hash_value % 100
```

**Why flag_name is included in the seed:**
If seed was just user_id, user "user_123" would always be in the same bucket (e.g., bucket 7). This means they'd always be in the first 10% for every 10% rollout of every flag, and always excluded from the first 10% of flags rolled out to bucket < 10. Combining flag_name + user_id ensures statistical independence across flags.

**Verification:**
```
For 1,000,000 random user_ids with rollout_percentage = 10:
Expected enabled count: ~100,000
Actual enabled count: ~99,847 (within 0.15% — acceptable)
```

### 11.4 Edge Cases

| Edge Case | Behaviour |
|-----------|-----------|
| `rollout_percentage = 0`, no rules | Returns `{enabled: false, reason: "rollout_excluded"}` |
| `rollout_percentage = 100`, no rules | Returns `{enabled: true, reason: "rollout_included"}` (no hash needed) |
| `is_enabled = false` with 100% rollout | Returns `{enabled: false, reason: "flag_disabled"}` — kill switch overrides everything |
| Flag not found in project | Returns `{enabled: false, reason: "flag_not_found"}` — never throws an error |
| User in both include and exclude rule | Exclude rules evaluated first — user gets `false` |
| Empty user_id | Treated as a valid user_id string "". Bucketed consistently. |
| context is None | All rule checks against context attributes return no match — fall through to rollout |
| Redis unavailable | Cache miss → query Postgres directly. Evaluation still works, slower. |
| Postgres unavailable | SDK returns default_value. Server returns 503. |

---

## 12. React Dashboard

> **Scope note:** Routes and pages marked `[v3]`/`[v4]` below are not built in v1. v1 has six working pages (Login, Register, Projects, Project Dashboard, Flags, Flag Detail, API Keys, Account — counting Login/Register as one flow) per Section 0.3 and 2.9.

### 12.1 Route Structure

```
/login                      → LoginPage (public)
/register                   → RegisterPage (public)
/                           → redirect to /projects (private)
/projects                   → ProjectsPage (private)
/projects/:projectId        → ProjectDashboardPage (private)
/projects/:projectId/flags  → FlagListPage (private)
/flags/:flagId              → FlagDetailPage (private)
/projects/:projectId/keys   → APIKeysPage (private)
/flags/:flagId/ab-test      → ABTestPage (private)              [v4]
/projects/:projectId/analytics → AnalyticsPage (private)        [v3]
/account                    → AccountPage (private)
```

### 12.2 Page-by-Page Design

**LoginPage**
- Email + password form
- "Don't have an account? Register" link
- Error toast on invalid credentials
- Redirect to /projects on success
- No navigation sidebar

**RegisterPage**
- Name + email + password + confirm password
- Password strength indicator
- Redirect to /projects on success

**ProjectsPage**
- Grid of project cards (name, flag count, last activity)
- "New Project" button → modal form
- Empty state: "Create your first project" illustration + CTA
- Each card navigates to ProjectDashboardPage

**ProjectDashboardPage**
- 2 stat cards in v1: Active Flags, Total Evaluations Today. `[v4]` 3rd card: A/B Tests Running
- Recent flags list (top 5 by activity)
- Quick actions: "New Flag", "Manage API Keys"

**FlagListPage**
- Table: Flag Name | Status Badge | Rollout % | Evaluations | Last Modified | Actions
- Toggle switch per flag (calls PATCH immediately, optimistic UI)
- Search bar (client-side filter)
- Status filter: All / Enabled / Disabled
- "New Flag" button → modal
- Click flag name → FlagDetailPage

**FlagDetailPage** `[v1 core, extended in v3/v4]`
- Flag name + description (editable inline)
- Big on/off toggle
- Rollout slider (0–100 with numeric input)
- "Targeting Rules" section: list of rules, "Add Rule" button, delete per rule
- Simple evaluation count (single number, e.g. "12,403 evaluations") — full chart is v3
- "Danger Zone": Delete Flag (with confirmation dialog)
- `[v3]` "Evaluation History" chart: 7-day time series
- `[v4]` "A/B Testing" section: create test or view existing test results

**APIKeysPage**
- Table: Label | Key Preview | Last Used | Created | Revoke Button
- "Generate New Key" button
- On generation: modal showing full key once with copy button and warning "This will not be shown again"
- Code snippet showing SDK initialisation with the key

**ABTestPage** `[v4]`
- Current test status (draft / running / concluded)
- Hypothesis text
- Variant table: Variant | Users | Conversions | Conversion Rate | Lift vs Control
- Confidence level progress bar (e.g., "87% — not yet significant")
- "Declare Winner" button (enabled when confidence ≥ 95%)
- Start / Stop test buttons

**AnalyticsPage** `[v3]`
- Line chart: evaluations per day (7d / 30d selector)
- Bar chart: top flags by volume
- Pie chart: enabled vs disabled evaluation ratio

**AccountPage**
- Update name / email form
- Change password form (current + new + confirm)
- Delete account (with "type your email to confirm" pattern)

### 12.3 Global Components

**Sidebar:** Logo → Projects → Account → (within project context: Flags, API Keys, Analytics)

**Toast system:** Success (green), Error (red), Info (blue) — auto-dismiss after 4 seconds

**Confirm Dialog:** Used for all destructive actions. "Are you sure?" with action description.

**Loading Skeleton:** Shown while data is fetching — prevents layout shift. Every table/card has a skeleton variant.

**Empty State:** Every list has a "nothing here yet" state with icon + message + CTA button.

---

## 13. Python SDK

> **Scope note:** v1 ships `is_enabled()` and `track()` as the headline methods, per Section 0.3. `evaluate()` is included in v1 too — it shares almost all of its implementation with `is_enabled()` (same HTTP call, same cache, just returns the full result object instead of unwrapping `.enabled`), so excluding it would mean writing throwaway code rather than saving effort. `get_all_flags()` is deferred to v2: it implies a bootstrapping/bulk-fetch pattern that starts overlapping with polling, which the v1 plan explicitly excludes ("no polling, no advanced synchronization").

### 13.1 Public API

```python
from flagbase import FlagClient

# Initialisation
client = FlagClient(
    api_key="proj_sk_...",
    host="https://api.flagbase.dev",  # optional, defaults to cloud
    cache_ttl=30,                     # seconds, default 30
    timeout=0.5,                      # HTTP timeout in seconds, default 0.5
    default_value=False               # returned if server unreachable
)

# Basic flag check
enabled = client.is_enabled("new_checkout_ui", user_id="user_123")

# Flag check with context
enabled = client.is_enabled(
    "premium_feature",
    user_id="user_123",
    context={
        "email": "user@example.com",
        "country": "IN",
        "custom_attributes": {"plan": "premium"}
    }
)

# Get full evaluation result (with reason)
result = client.evaluate("new_checkout_ui", user_id="user_123")
# result.enabled → True/False
# result.variant → "control" / "treatment" / None     (None until v4 ships A/B testing)
# result.reason  → "rollout_included" / "rule_match_include" / etc.

# Track a conversion event (for A/B testing)
client.track(
    event_name="purchase_completed",
    user_id="user_123",
    flag_name="new_checkout_ui",
    variant="treatment"
)

# [v2] Get all flags for a project (for bootstrapping) — deferred, see scope note above
all_flags = client.get_all_flags()

# Close the client (cleanup HTTP connections)
client.close()
```

### 13.2 Internal Architecture

**FlagClient (client.py)**
- Entry point. Wraps evaluator and HTTP client.
- Validates constructor arguments.
- Provides `is_enabled()`, `evaluate()`, `track()`, `close()` in v1. `get_all_flags()` in v2.

**Evaluator (evaluator.py)**
- Checks local cache first.
- On cache miss: delegates to HTTPClient.
- Updates cache on successful response.
- On any exception from HTTPClient: returns default_value.

**TTLCache (cache.py)**
- Thread-safe in-memory dictionary: `{flag_name: (result, expiry_timestamp)}`
- `get(key)` → returns value if not expired, else None
- `set(key, value, ttl)` → stores with expiry
- `invalidate(key)` → removes entry
- Uses `threading.Lock` for thread safety

**HTTPClient (http_client.py)**
- Thin wrapper around `httpx.Client`
- Sets `Authorization: Bearer {api_key}` header on every request
- Configurable timeout (default 500ms)
- Raises `FlagBaseConnectionError` on timeout or network error
- Raises `FlagBaseAuthError` on 401 response
- Does NOT retry (retry logic is in Evaluator)

### 13.3 Error Handling Philosophy

The SDK must **never crash the host application.** Every error is caught and results in the default_value being returned.

```
Network timeout    → log warning → return default_value
HTTP 401           → log error ("check your API key") → return default_value
HTTP 404 (flag)    → log info ("flag not found") → return default_value
HTTP 429 (rate)    → log warning → return default_value
Any exception      → log error → return default_value
```

### 13.4 Retry Strategy

The SDK does not retry on the evaluation path (to preserve low latency). Instead:
- Timeout is set aggressively low (500ms default)
- Local cache means most calls don't hit the network
- Failed calls return default_value immediately

For the `track()` method (conversion events), the SDK uses a background thread with retry:
- Non-blocking: `track()` returns immediately
- Background thread sends the event HTTP request
- Retries: 3 attempts with 1s, 2s, 4s backoff
- Events are fire-and-forget — no guarantee of delivery (acceptable for analytics)

---

## 14. Analytics Engine `[v3]`

> Event *writing* (the evaluation engine inserting into `evaluation_events`, the SDK's `track()` inserting into `conversion_events`) happens starting in v1. Everything in this section about *reading* and presenting that data — metrics, aggregation queries, dashboard charts — is v3.

### 14.1 Event Collection

Every flag evaluation generates an `EvaluationEvent` written asynchronously via FastAPI's `BackgroundTasks`:

```python
@router.post("/evaluate")
async def evaluate_flag(request, background_tasks: BackgroundTasks, db, redis):
    result = await evaluation_service.evaluate(...)
    background_tasks.add_task(
        analytics_service.record_evaluation,
        flag_id=flag.id,
        user_id_hash=sha256(request.user_id),
        result=result.enabled,
        reason=result.reason,
        variant=result.variant
    )
    return result
```

Using `BackgroundTasks` means the HTTP response is returned to the SDK immediately — analytics writes don't add latency to the evaluation path.

### 14.2 Metrics Calculated

| Metric | SQL Approach |
|--------|-------------|
| Total evaluations (period) | `COUNT(*) WHERE flag_id = ? AND timestamp > ?` |
| Unique users exposed | `COUNT(DISTINCT user_id_hash) WHERE result = true` |
| Enabled rate | `SUM(result::int) / COUNT(*).0` |
| Evaluations per day | `GROUP BY DATE(timestamp)` |
| Top flags by volume | `GROUP BY flag_id ORDER BY COUNT(*) DESC LIMIT 10` |

### 14.3 Performance Strategy

Analytics queries can be expensive on large event tables. Mitigation:
- Composite index on `(flag_id, timestamp)` — most queries filter by both
- Query only the `period` range (7d, 30d, 90d) — never full table scan
- Cache analytics results in Redis for 5 minutes (analytics don't need real-time)
- Future: materialised views for daily aggregations

---

## 15. A/B Testing Engine `[v4]`

### 15.1 Variant Assignment

Variant assignment uses the same consistent hashing as rollout, but partitions the hash space into segments:

```
Total hash space: 0–99

Example: 2 variants, 50/50 split
  control:   bucket 0–49
  treatment: bucket 50–99

Example: 3 variants, 33/34/33 split
  control:     bucket 0–32
  treatment_a: bucket 33–66
  treatment_b: bucket 67–99
```

```python
def assign_variant(ab_test_id, user_id, variants):
    """
    Deterministic variant assignment.
    Same user always gets same variant for same test.
    """
    bucket = compute_bucket(str(ab_test_id) + user_id)
    cumulative = 0
    for variant in sorted(variants, by=name):  # sort for determinism
        cumulative += variant.traffic_percentage
        if bucket < cumulative:
            return variant
```

### 15.2 Statistical Significance (Two-Proportion Z-Test)

When enough data is collected, the platform computes whether the conversion rate difference between control and treatment is statistically significant.

**Formula:**
```
Given:
  n_c = users in control
  n_t = users in treatment
  c_c = conversions in control
  c_t = conversions in treatment

  p_c = c_c / n_c     (control conversion rate)
  p_t = c_t / n_t     (treatment conversion rate)
  p_pool = (c_c + c_t) / (n_c + n_t)  (pooled proportion)

  SE = sqrt(p_pool * (1 - p_pool) * (1/n_c + 1/n_t))  (standard error)
  z = (p_t - p_c) / SE                                   (z-statistic)

  p_value from two-tailed z-test using scipy.stats.norm.sf(abs(z)) * 2
  confidence = (1 - p_value) * 100
```

**Implementation uses `scipy.stats.proportions_ztest` for accuracy.**

### 15.3 Significance Thresholds

| Confidence | Meaning | Dashboard Display |
|-----------|---------|------------------|
| < 80% | Not significant | "Collecting data..." (grey) |
| 80–89% | Trending | "Trending (80%+)" (yellow) |
| 90–94% | Suggestive | "Almost significant (90%+)" (orange) |
| ≥ 95% | Significant | "Statistically significant ✓" (green, declare winner enabled) |

**Minimum sample size check:**
Before computing significance, verify each variant has at least 100 exposures. Below this threshold, display "Insufficient data."

### 15.4 Winner Selection

When "Declare Winner" is clicked:
1. Set `ab_tests.winner_variant_id` to selected variant's ID
2. Set `ab_tests.status = 'concluded'`, `concluded_at = NOW()`
3. If winning variant is "treatment": automatically set `flag.rollout_percentage = 100`
4. If winning variant is "control": automatically set `flag.is_enabled = false`
5. Invalidate Redis cache for the flag

---

## 16. Deployment Architecture

### 16.1 Docker (Backend)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run database migrations then start server
CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### 16.2 Docker Compose (Local Development + Self-Hosting)

```yaml
version: "3.9"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://flagbase:password@db:5432/flagbase
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: flagbase
      POSTGRES_PASSWORD: password
      POSTGRES_DB: flagbase
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U flagbase"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

### 16.3 Environment Variables

```bash
# Required — Backend
SECRET_KEY=              # 32+ random chars — used for JWT signing
DATABASE_URL=            # postgresql+asyncpg://user:pass@host:5432/dbname
REDIS_URL=               # redis://host:6379/0
ENVIRONMENT=             # "development" or "production"

# Optional — Backend
CORS_ORIGINS=            # comma-separated, e.g. "https://app.flagbase.dev"
LOG_LEVEL=               # "DEBUG" / "INFO" / "WARNING" (default: "INFO")
RATE_LIMIT_PER_MINUTE=  # default: 100

# Required — Frontend
VITE_API_URL=            # https://api.flagbase.dev

# SDK (set by developer in their app)
FLAGBASE_API_KEY=        # proj_sk_...
```

### 16.4 Railway Deployment

**Services to create on Railway:**
1. `flagbase-api` — Docker deployment from GitHub repo
2. `flagbase-db` — Railway PostgreSQL plugin (managed)
3. `flagbase-redis` — Railway Redis plugin (managed)

Railway auto-injects `DATABASE_URL` and `REDIS_URL` when services are linked.

**Deploy steps:**
1. Push code to GitHub
2. Connect Railway project to GitHub repo
3. Add Postgres and Redis plugins
4. Set environment variables (SECRET_KEY, CORS_ORIGINS, ENVIRONMENT=production)
5. Railway auto-deploys on every push to `main`

### 16.5 Vercel Deployment (Frontend)

```bash
# vercel.json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [{ "source": "/(.*)", "destination": "/" }]
}
```

The rewrite rule is critical — it ensures React Router handles all routes instead of Vercel returning 404.

---

## 17. Logging Strategy

> **Scope note:** basic logging (Python's `logging` module, the level table below, request/response logging) is v1 — this is baseline hygiene, not extra scope, and costs little to build correctly from the start. The structured-JSON production format and cache-miss-rate logging (which assumes Redis exists) are v2, alongside the rest of the "production engineering" work.

### 17.1 Log Levels

| Level | When to use |
|-------|-------------|
| DEBUG | Detailed internals (cache hits, DB queries) — development only |
| INFO | Normal operations (request received, flag evaluated, user registered) |
| WARNING | Unexpected but recoverable (cache miss rate high, rate limit hit) |
| ERROR | Something failed but app continues (DB write failed, invalid API key) |
| CRITICAL | App cannot continue (DB connection lost, Redis unavailable) |

### 17.2 Log Format (Structured JSON in production)

```json
{
  "timestamp": "2026-06-26T14:30:00Z",
  "level": "INFO",
  "service": "flagbase-api",
  "message": "Flag evaluated",
  "flag_name": "new_checkout_ui",
  "project_id": "uuid",
  "result": true,
  "reason": "rollout_included",
  "latency_ms": 0.34,
  "request_id": "uuid"
}
```

### 17.3 What to Log

- Every HTTP request: method, path, status code, latency, request_id
- Every flag evaluation: flag_name, result, reason, latency
- `[v2]` Every cache miss (to monitor cache effectiveness — no cache exists in v1)
- Every authentication failure (for security monitoring)
- Every database query that exceeds 100ms (slow query detection)
- Application startup: version, environment, DB connection status

### 17.4 What NOT to Log

- User passwords (ever)
- Full API keys (log only prefix)
- User emails in bulk (log user_id only)
- Full request/response bodies (may contain sensitive data)

---

## 18. Testing Strategy

### 18.1 Test Pyramid

```
        ┌───────────┐
        │  E2E (5%) │  ← Playwright: full user flows
        ├───────────┤
        │Integration│  ← FastAPI test client + test DB (35%)
        │  (35%)    │
        ├───────────┤
        │   Unit    │  ← Evaluation engine, hashing, stats (60%)
        │   (60%)   │
        └───────────┘
```

### 18.2 Unit Tests (Most Important)

**Evaluation Engine Tests (test_evaluation.py) — test every case:**

```
test_flag_disabled_returns_false
test_rollout_0_returns_false
test_rollout_100_returns_true
test_rollout_10_percent_is_consistent
test_rollout_10_percent_distributes_correctly (1M users, expect ~10%)
test_exclude_rule_overrides_rollout
test_include_rule_overrides_rollout
test_exclude_rule_overrides_include_rule
test_flag_not_found_returns_false
test_empty_rules_falls_through_to_rollout
test_rule_user_id_equals_match
test_rule_user_id_in_list_match
test_rule_country_equals_match
test_custom_attribute_match
test_none_context_does_not_crash
```

**Hashing Tests:**
```
test_bucket_is_deterministic (same inputs always same output)
test_bucket_range (always 0–99)
test_different_flags_different_buckets_for_same_user
test_distribution_uniformity (chi-square test on 100k users)
```

**Statistics Tests** `[v4]` — written once the A/B testing engine exists:
```
test_z_test_significant_result
test_z_test_not_significant_result
test_minimum_sample_size_check
test_winner_declaration_updates_flag
```

### 18.3 Integration Tests

- Test complete API flows with `httpx.AsyncClient` against a real test database
- Test database: separate PostgreSQL database (`flagbase_test`) created fresh per test session
- Every route has at least: happy path, auth failure (401), not found (404), validation error (422)

### 18.4 SDK Tests

- Mock the HTTP client — test SDK behaviour in isolation from the server
- Test: cache hit returns without HTTP call
- Test: HTTP failure returns default_value
- Test: expired cache triggers HTTP call
- Test: track() is non-blocking

### 18.5 Running Tests

```bash
# Backend
pytest tests/ -v --cov=app --cov-report=html

# SDK
pytest flagbase-python-sdk/tests/ -v

# Specific file
pytest tests/test_evaluation.py -v -k "test_rollout"
```

---

## 19. CI/CD Pipeline

### 19.1 GitHub Actions Workflow

**File: `.github/workflows/ci.yml`**

```
Trigger: Push to any branch, Pull Request to main

Jobs:
1. lint-and-type-check
   - ruff check app/
   - black --check app/
   - mypy app/

2. test
   - Spin up PostgreSQL and Redis as services
   - Run pytest with coverage
   - Fail if coverage < 80%

3. build-docker (on push to main only)
   - docker build .
   - Push to GitHub Container Registry (GHCR)

4. deploy (on push to main only, after build succeeds)
   - Trigger Railway deployment via Railway API
   - Trigger Vercel deployment via Vercel API
```

### 19.2 Branch Strategy

```
main        → production deployments (protected branch, PR required)
develop     → integration branch
feature/*   → individual feature branches
fix/*       → bug fix branches
```

---

## 20. Monitoring

### 20.1 Health Monitoring

- `GET /health` endpoint polled every 30 seconds by Railway
- If health check fails 3 times: Railway auto-restarts the service

### 20.2 Metrics to Track (Future: Prometheus + Grafana)

| Metric | Alert Threshold |
|--------|----------------|
| `evaluation_latency_p99` | > 5ms |
| `evaluation_error_rate` | > 1% |
| `cache_hit_rate` | < 90% |
| `db_connection_pool_utilisation` | > 80% |
| `api_error_rate_5xx` | > 0.1% |
| `redis_memory_usage` | > 80% |

### 20.3 Uptime Monitoring

Use UptimeRobot (free tier) to ping `GET /health` every 5 minutes. Alert via email on downtime.

---

## 21. Documentation Plan

### 21.1 README.md (GitHub — most important for open source)

Structure:
1. What is FlagBase? (2–3 sentences + screenshot)
2. Quick Start (Docker Compose — up and running in 2 minutes)
3. SDK installation and 5-line example
4. Architecture diagram
5. Features list
6. Contributing guide
7. License

### 21.2 API Reference

FastAPI auto-generates OpenAPI 3.0 spec at `/docs` (Swagger UI) and `/redoc`.
Export this as a static `openapi.json` and host on the documentation site.

### 21.3 SDK Documentation

- PyPI README is the primary SDK documentation
- Code examples for: Flask, FastAPI, Django, plain Python script
- All public methods documented with type hints and docstrings

### 21.4 Architecture Documentation

A `ARCHITECTURE.md` explaining:
- Why key technology choices were made
- The evaluation engine algorithm with examples
- The caching strategy and invalidation flow
- How to contribute a new rule type

---

## 22. Development Roadmap

> This roadmap is the authoritative week-by-week plan. It supersedes any version-ambiguous phasing implied elsewhere in this document. Weeks are estimates for one student working part-time alongside coursework — treat them as a sanity check on scope, not a deadline to enforce mechanically.

### FlagBase v1 — Weeks 1–9

**Phase 1: Foundation (Weeks 1–2) — Learn, not build.**
- FastAPI official tutorial (fastapi.tiangolo.com) — complete from start to finish
- SQLAlchemy / SQLModel tutorial — understand ORM patterns
- JWT: understand HS256 signing, token claims, expiry
- React: build 2–3 throwaway mini-projects to solidify hooks and fetch
- **Deliverable:** Can build a CRUD API with auth from scratch, no tutorial needed

**Phase 2: Database Schema + Project Skeleton (Week 3)**
- Set up repository: `flagbase-backend/`, `flagbase-frontend/`, `flagbase-python-sdk/`
- Set up Docker Compose with Postgres (Redis container can be added now or deferred to v2 — either is fine, since v1 doesn't read/write to it)
- Create all SQLAlchemy models (all nine tables — see Section 7's scope note on why)
- Run first Alembic migration — verify all tables created
- Write seed script: 1 user, 1 project, 2 flags, 1 API key
- Set up `pytest` with `conftest.py` fixtures
- **Deliverable:** `docker-compose up` starts everything. `pytest` runs (no tests yet). DB has all tables.

**Phase 3: Core API + Evaluation Engine (Weeks 4–6)**
- Implement auth routes (register, login, me)
- Implement project CRUD routes
- Implement flag CRUD routes
- Implement API key routes
- Implement evaluation endpoint (the core) — reads directly from Postgres, no cache
- Implement flag rule CRUD (operators scoped per Section 2.5: equals/not_equals/in_list/not_in_list only)
- Write all unit tests for the evaluation engine — this is the highest-priority test suite in the whole project
- Test every endpoint with curl or Postman
- **Deliverable:** Full working API. curl to `/evaluate` returns correct flag result. All evaluation edge cases pass tests.

**Phase 4: React Dashboard (Weeks 7–8)**
- Set up Vite + React + Tailwind
- Implement auth context + login/register pages
- Implement projects list + create project
- Implement flag list + toggle + create flag
- Implement flag detail page with rollout slider + rule builder (no chart, no A/B section — see Section 12.2)
- Implement API key management page
- **Deliverable:** Full dashboard working against local backend. User can register, create project, create flag, toggle it, see it change.

**Phase 5: Python SDK + Deploy + Document (Week 9)**
- Build FlagClient class with v1 public API: `is_enabled()`, `evaluate()`, `track()`, `close()`
- Build TTL cache (thread-safe), HTTP client wrapper, error handling (all paths return `default_value`)
- Write all SDK unit tests (mock HTTP)
- Package with `pyproject.toml`; publish to TestPyPI, then PyPI
- Docker deploy (backend + frontend); write the README
- **Deliverable:** `pip install flagbase` works. Live deployed instance. GitHub repo public with README + screenshots. **This is the placement-ready milestone.**

### FlagBase v2 — Production Engineering (following weeks, scope-dependent)
- Add Redis: caching layer for evaluation path (Section 10), cache invalidation on writes
- Rate limiting (sliding window via Redis)
- Structured JSON logging in production
- Background tasks for event writes (don't block the evaluation response on a DB write)
- Pagination and richer filtering on list endpoints
- Audit logs (who changed what flag, when)
- Multi-environment support: `environments` table, environment-scoped API keys, separate flag state per environment, "promote" action
- **Deliverable:** Same product, but it behaves like a system that's seen real traffic.

### FlagBase v3 — Platform Capabilities
- Analytics API (Section 8.9) + AnalyticsPage with charts
- Evaluation history chart on FlagDetailPage
- SDK refinement (e.g. background polling instead of pure TTL cache, if pursued)
- Webhooks (flag enabled/disabled/rollout changed events, HMAC-signed, retry with backoff)
- **Deliverable:** A dashboard a non-engineer would actually choose to use.

### FlagBase v4 — A/B Testing
- `ab_tests` / `ab_variants` data model activated
- Variant assignment (deterministic, same bucketing approach as rollout)
- Conversion event ingestion and aggregation
- Two-proportion z-test statistical significance engine
- Winner declaration flow
- ABTestPage in the dashboard
- **Deliverable:** A real, working experimentation platform — the single most differentiating feature for interviews.

### FlagBase v5 — Enterprise Features
- Teams, roles (Owner/Editor/Viewer), invitations
- SSO, IP allowlisting, scheduled flag changes, flag dependencies
- JavaScript SDK
- Kubernetes deployment, WebSocket/streaming evaluation, OpenFeature compatibility
- **Deliverable:** Optional. Pursued only if the project is being actively maintained beyond the placement-prep timeline, e.g. as an open-source side project post-internship.

### Milestones Summary

| Milestone | Version | Success Criteria |
|-----------|---------|-------------------|
| M1: API working | v1, end of Phase 3 | All endpoints return correct data, evaluation engine passes all tests |
| M2: Dashboard working | v1, end of Phase 4 | Full user flow works in browser |
| M3: SDK published, live deploy | v1, end of Phase 5 | `pip install flagbase` works against a live server; GitHub repo public with README + screenshots — **placement-ready** |
| M4: Production-hardened | v2 | Redis caching live, rate limiting enforced, multi-environment support working |
| M5: Platform-grade dashboard | v3 | Analytics charts and webhooks working end to end |
| M6: Experimentation platform | v4 | A full A/B test can be created, run, and have a winner declared with real statistical backing |
| M7: Enterprise-shaped | v5 | Optional — teams/RBAC functioning if pursued |

---

## 23. Future Improvements

> Most of what used to live in this section now has a concrete home in v2, v3, v4, or v5 (see Section 0 and the Development Roadmap). Nothing has been deleted — items are either pointed to their version below, or, where they remain genuinely open-ended (no committed version, may never be built), kept here as true "future" ideas beyond the five-version roadmap.

### 23.1 Items now assigned to a version (pointer only — see linked section for full design)

| Item | Now lives in | Section |
|------|---------------|---------|
| Webhooks | v3 | [Section 15... see 0.3] |
| Multi-environment support | v2 | [Section 0.3](#03-version-map), [Section 7](#7-database-design) |
| Audit logs | v2 | [Section 0.3](#03-version-map) |
| Teams and collaboration (roles, invitations) | v5 | [Section 0.3](#03-version-map) |
| JavaScript SDK | v5 | [Section 0.3](#03-version-map) |
| SSO, IP allowlisting, scheduled changes, flag dependencies | v5 | [Section 0.3](#03-version-map) |

Full original detail on each, preserved for reference:

**Webhooks** — Emit webhook events on: flag enabled, flag disabled, rollout changed, A/B winner declared. Configurable per project. Payload includes event type, flag details, timestamp, triggered by. HMAC-SHA256 signature for webhook verification. Retry with exponential backoff on delivery failure.

**Multi-environment support** — Each project has multiple environments: Development, Staging, Production. Flags exist per-project but have separate states per environment. API keys are scoped to an environment. "Promote flag state from Staging to Production" one-click action.

**Teams and collaboration** — Project owners can invite team members by email. Roles: Owner, Editor (can toggle flags), Viewer (read-only).

**Audit logs** — Every flag state change recorded: user, old value, new value, timestamp. Viewable in dashboard per flag. Exportable as CSV.

**JavaScript SDK** — `npm install flagbase-js`. Client-side evaluation with browser-compatible caching. React hook: `useFlag("new_checkout_ui", userId)`.

**Enterprise features** — SSO (SAML or OAuth via Google Workspace/GitHub), IP allowlisting for API keys, scheduled flag changes ("enable this flag at 9am IST on Tuesday"), flag dependencies ("flag B can only be enabled if flag A is enabled").

### 23.2 Genuinely open-ended (beyond v5, no committed version)

These are real ideas worth keeping on record, but they don't pass the three-question filter cleanly enough yet to assign a version — either the value is speculative, the scope is unbounded, or they depend on FlagBase having real production usage data that doesn't exist yet.

**AI/ML Integration** — explicitly scoped as a separate, later project (per existing direction: web development fundamentals first, AI/ML integration after). Ideas on record: anomaly detection (a model flags unusual error rates or latency during a rollout and auto-disables the flag), smart rollout (auto-increase rollout percentage when metrics look healthy — a feedback loop), and natural-language flag creation ("gradually roll out the new payment page to 10% of users in India" → creates the flag and rule automatically).

**Performance improvements at scale** — read replica for Postgres so analytics queries don't hit the primary; TimescaleDB for the `evaluation_events` table once it's genuinely time-series-shaped at volume; CDN-hosted flag snapshots for sub-5ms global evaluation latency. None of this matters until there's real traffic to optimize for — premature here, but worth knowing the next steps exist.

---

## 24. Engineering Best Practices

### 24.1 Naming Conventions

**Python (PEP 8):**
- Variables and functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`
- Files: `snake_case.py`

**JavaScript/React:**
- Variables and functions: `camelCase`
- React components: `PascalCase`
- Files (components): `PascalCase.jsx`
- Files (utilities): `camelCase.js`
- CSS classes (Tailwind): lowercase kebab handled by Tailwind itself

**Database:**
- Table names: `snake_case`, plural (`flags`, `evaluation_events`)
- Column names: `snake_case`
- Index names: `idx_{table}_{column(s)}`
- Foreign key names: `fk_{table}_{referenced_table}`

**API endpoints:**
- Resources: plural nouns (`/flags`, `/projects`, `/api-keys`)
- Actions: POST for create, GET for read, PATCH for partial update, DELETE for delete
- Kebab-case for multi-word: `/api-keys`, `/ab-tests`
- No verbs in endpoint names (not `/createFlag` — use `POST /flags`)

### 24.2 Git Workflow

**Branching:**
```
main          → protected, deployable always
develop       → integration branch, PRs from feature branches
feature/xyz   → individual features (e.g., feature/ab-testing-engine)
fix/xyz       → bug fixes (e.g., fix/cache-invalidation-race)
```

**Commit Message Format (Conventional Commits):**
```
<type>(<scope>): <short description>

Types:
  feat      → new feature (correlates with MINOR in semver)
  fix       → bug fix (correlates with PATCH)
  perf      → performance improvement
  refactor  → code change that neither fixes nor adds feature
  test      → adding or fixing tests
  docs      → documentation changes
  chore     → tooling, config, dependencies
  ci        → CI/CD changes

Examples:
  feat(evaluation): implement consistent hash bucketing algorithm
  fix(cache): invalidate redis key on rule deletion
  test(evaluation): add edge case tests for 0% rollout
  docs(sdk): add Flask integration example
  perf(evaluation): reduce cache miss rate by increasing TTL to 120s
```

### 24.3 Clean Architecture Principles Applied

**Separation of concerns:**
- `api/` = HTTP concerns only (parse request, call service, return response)
- `services/` = business logic only (no HTTP, no direct DB queries)
- `repositories/` = database concerns only (SQLAlchemy queries)
- `models/` = data structure only (no methods beyond simple properties)

**Dependency injection:**
- Database session injected via FastAPI `Depends(get_db)` — never imported directly
- Redis injected via `Depends(get_redis)`
- Services receive repositories as arguments — never instantiate them internally
- This makes unit testing trivial (mock the repository, test the service)

**No business logic in route handlers:**
```python
# WRONG — logic in handler
@router.post("/flags/{id}/toggle")
async def toggle_flag(flag_id: UUID, db: Session = Depends(get_db)):
    flag = db.query(Flag).get(flag_id)
    flag.is_enabled = not flag.is_enabled
    db.commit()
    await redis.delete(f"flag:{flag.project_id}:{flag.name}")
    return flag

# CORRECT — delegate to service
@router.post("/flags/{id}/toggle")
async def toggle_flag(flag_id: UUID, db=Depends(get_db), redis=Depends(get_redis)):
    flag = await flag_service.toggle_flag(db, redis, flag_id)
    return FlagResponse.from_orm(flag)
```

### 24.4 Code Review Checklist (Use for Every PR)

- [ ] Does every new function have a docstring?
- [ ] Are all inputs validated by Pydantic before reaching service layer?
- [ ] Does every new route check ownership (user owns the resource)?
- [ ] Does every flag/rule modification invalidate Redis cache?
- [ ] Are there unit tests for the new logic?
- [ ] Are there no hardcoded secrets or URLs?
- [ ] Does the PR description explain *why*, not just *what*?

---

## 25. Interview Preparation Notes

> **How to use this section as the project progresses:** the answers below describe the *full* system across all five versions. While only v1 is built, don't claim the v2–v5 pieces (Redis caching, rate limiting, A/B testing, audit logs) as done — say what's built, and use the roadmap framing for the rest. That's a stronger interview answer than either overclaiming or sounding unprepared: "I built v1 with the full evaluation engine and SDK; the caching layer and A/B testing are scoped into v2 and v4 of my roadmap, here's why I sequenced it that way" shows real engineering judgment.

### 25.1 How to Introduce the Project

> "I built FlagBase — an open-source feature flag platform, with A/B testing as a planned extension. It's the same kind of system Razorpay or CRED would use to gradually roll out a payment flow change. I built it from scratch: a FastAPI backend, React dashboard, and a pip-installable Python SDK. The technically interesting part is the evaluation engine, which uses consistent hashing so the same user always gets the same result for a given flag, even with rules and percentage rollouts layered on top. I scoped the build into versions — v1 is the complete core (auth, flags, targeting rules, evaluation engine, SDK), and I'm extending it through caching, multi-environment support, and eventually a full A/B testing engine with statistical significance testing."

*(Once v2+ ships, update this pitch to include the shipped pieces — e.g. "...with Redis caching keeping p99 evaluation latency under a millisecond" once that's actually true and measured, not estimated.)*

### 25.2 Architectural Decision Q&A

**Q: Why did you use Redis alongside PostgreSQL instead of just PostgreSQL?** `[v2]`
> "The flag evaluation endpoint is called on every page load of every app using the SDK. If we hit Postgres every time, we'd add several milliseconds of latency to every request. Redis gives sub-millisecond reads with a short TTL. PostgreSQL is still the source of truth — Redis is just a fast read layer." *(Answerable once v2 ships; until then, the honest answer is "v1 reads Postgres directly — Redis caching is the first thing I added in v2, once the core was correct and tested.")*

**Q: Why FastAPI over Django?** `[v1 — answerable now]`
> "FastAPI is async-native and built on modern Python standards. Django is a batteries-included framework designed for monolithic web apps — it brings a lot of things I don't need (template engine, admin panel, form handling). FastAPI lets me be explicit about everything, has automatic OpenAPI documentation generation, and its Pydantic integration means all request validation is declarative. For a pure API service, FastAPI is simply the right tool."

**Q: How does consistent hashing work in your rollout system?** `[v1 — answerable now]`
> "I use MurmurHash3 — a non-cryptographic hash with excellent distribution. I hash `flag_name + user_id` together and take it modulo 100 to get a bucket number 0–99. If the bucket is less than the rollout percentage, the flag is enabled. Including the flag name in the hash seed is important — without it, the same user would be in the same bucket for every flag, which would mean they're always in the first 10% of every 10% rollout. By mixing in the flag name, different flags produce statistically independent bucket assignments for the same user."

**Q: How do you handle cache invalidation?** `[v2]`
> "I use a delete-on-write strategy. When a flag is updated in Postgres, I immediately delete its Redis key. The next evaluation call cache-misses, reads from Postgres, and repopulates Redis. I chose this over update-on-write because it's simpler and avoids cache consistency bugs."

**Q: How does your A/B testing statistical significance work?** `[v4]`
> "I implement a two-proportion z-test using scipy. Given conversion rates for control and treatment variants, I compute a z-statistic by measuring how many standard errors the difference is from zero, then look up the corresponding p-value. If the p-value is below 0.05, we have 95% confidence the difference is real and not random noise. I also enforce a minimum sample size per variant before computing significance — small samples produce unreliable p-values."

**Q: How would you scale this to handle a high volume of evaluations per second?** `[v1 — answerable now as a design discussion]`
> "The architecture scales horizontally — add more FastAPI instances behind a load balancer. Right now the bottleneck would be Postgres taking every evaluation read directly; that's exactly why caching is the first thing in my v2 roadmap. Past that, I'd look at a message queue for event writes so they don't compete with the read path, table partitioning on `evaluation_events` by month, and read replicas for analytics queries." *(This is honestly framed as "here's my plan," not "here's what I built" — which is fine; interviewers value a clear plan.)*

### 25.3 Concepts to Know Deeply (Study These)

| Concept | Why It Comes Up | Version |
|---------|----------------|---------|
| Consistent hashing | Core algorithm in the project | v1 |
| Database indexing | Explain your index choices | v1 |
| p99 latency vs p50 | Performance discussions | v1 |
| JWT vs session tokens | Auth architecture Q&A | v1 |
| SQL EXPLAIN ANALYZE | How to diagnose slow queries | v1 |
| Cache invalidation strategies | Asked at every system design interview | v2 |
| Rate limiting algorithms | You implemented one | v2 |
| CAP theorem | Distributed systems discussion | v2 |
| Background tasks vs message queues | Analytics pipeline design | v2/v3 |
| Two-proportion z-test | A/B testing engine | v4 |

### 25.4 Numbers to Know (Memorise These)

| Metric | Value | Version |
|--------|-------|---------|
| Evaluation p99 latency target | < 1ms | v1 target, v2 likely needed to actually hit it |
| SDK local cache TTL | 30 seconds | v1 |
| SDK HTTP timeout | 500ms | v1 |
| JWT expiry | 24 hours | v1 |
| Redis TTL for flags | 60 seconds | v2 |
| Rate limit | 100 req/min per API key | v2 |
| Min sample size for A/B | 100 users per variant | v4 |
| A/B significance threshold | 95% confidence (p < 0.05) | v4 |

> Don't memorise v2/v4 numbers as "what I built" until they're actually built — memorise them as "what I've designed and plan to measure against."

### 25.5 Weaknesses to Acknowledge Honestly

Interviewers respect honesty. For a v1-stage project, frame these as **deliberate, scoped decisions with a stated plan**, not unnoticed gaps — that distinction is the difference between "this person made a judgment call" and "this person ran out of time."

- **No caching layer yet** — every evaluation hits Postgres directly. "This is the first thing in my v2 roadmap — I wanted the evaluation engine correct and fully tested before optimizing it."
- **No multi-environment support** — flags exist at project level, not per environment. "I deliberately deferred this to v2. Doing it properly needs a real schema change and touches the evaluation engine — I didn't want to build it half-right just to hit a v1 deadline."
- **No real-time dashboard updates** — dashboard refreshes on page load, not live. "WebSocket subscriptions on flag changes are part of the v5 roadmap, alongside streaming evaluation."
- **No A/B testing yet** — the experimentation system is fully designed (data model, statistics engine, dashboard) but scoped to v4. "I treated it as its own version because it's genuinely a separate system — its own schema, its own statistics, its own UI — and bolting it onto v1 would have meant neither piece was actually finished."
- **Single-region deployment** — "for global scale I'd look at edge-hosted flag snapshots, but that's a v5+ problem; it doesn't matter until there's real geographic traffic to optimize for."

---

*End of FlagBase Project Specification Document v2.0*

---

**Document Maintenance Notes:**
- Update Section 8 (API Design) when any endpoint signature changes
- Update Section 7 (Database Design) immediately when adding migrations
- Update Section 22 (Roadmap) to mark completed phases
- Update Section 25 (Interview Notes) as you encounter real interview questions, and move Q&A pairs from "design discussion" framing to "what I built" framing as each version actually ships
- Update Section 0 (Project Scope) if the version boundaries themselves change — it's the source of truth for what's in/out of each version
- Version this document: bump minor version for additions, major version for architectural changes
