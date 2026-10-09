# GrowthOS: Google Ads Module, Components and AI Module Integration

Prepared for Mihir Patil, 8 October 2026. Draft v1.

The Google Ads module is the Google connector inside the GrowthOS Ads Layer Manager. It pulls campaign data from Google, normalizes it, executes approved changes, and exposes a clean contract that the AI module (Module 4) consumes. This document lists every component to build, how they connect, and exactly where the AI module plugs in.

## 1. Scope and sources

The Google Ads module design comes from the GrowthOS PRD, specifically the Ads Layer Manager (Module 3) and the platform-wide rules. The AI module side is described only from earlier work in this project, not from the PRD's Module 4 chapter: the Metrics Engine, the Digest and Anomaly Engine, the rule that deterministic computation and LLM narration stay strictly separate, and tenant templates with Domino's India (qsr\_delivery) as the demo tenant.

What the AI module team owns is not redesigned here. Anything marked Proposed is an interface suggestion that must be agreed with the owners of the other modules, because the AI module's builder does not have their schemas or APIs.

In scope for the MVP:

- Google Ads Search campaigns, ad groups, keywords, search terms, text ads
- Budgets, bidding configuration, conversion tracking, performance metrics
- Natural-language campaign planning, approval workflow, deployment, optimization recommendations
- Feeding normalized performance data to the AI module

Out of scope for the MVP: Performance Max and Display/Video campaigns, autonomous ad account creation, guaranteed auction wins, other ad platforms (Meta is a sibling connector, TikTok and LinkedIn come later).

## 2. Position in GrowthOS

GrowthOS follows the loop Acquire, Observe, Understand, Convert, Retain, Learn, Optimize. The Google Ads module owns the Acquire step for Google. The architectural rules from the PRD apply directly:

- No direct database access between modules. Synchronous needs go over versioned REST APIs, asynchronous needs over Kafka events.
- Customer identity is resolved centrally, not in the Ads module.
- Reasoning happens in the AI module. Execution stays inside the owning module, so only the Ads module ever calls the Google Ads API.
- Every important action is audited and every recommendation carries evidence and a confidence score.

The Ads module therefore does three jobs: connect and sync, plan and execute, and publish data and events for others.

## 3. Component overview

| # | Component | Purpose | Needed for MVP |
| --- | --- | --- | --- |
| 1 | Account Connection Service | OAuth, token vault, MCC linking | Yes |
| 2 | Google Ads Connector | Implements the common AdsConnector interface | Yes |
| 3 | Sync Scheduler and Workers | Pulls reports, handles rate limits and retries | Yes |
| 4 | Normalization Layer | Converts Google data to the GrowthOS schema | Yes |
| 5 | Storage | PostgreSQL, ClickHouse, Redis, S3 | Yes |
| 6 | Campaign Planning Engine | Turns a business goal into a campaign definition | Yes |
| 7 | Keyword and Audience Research | Keyword sets, negatives, audience suggestions | Yes |
| 8 | Validation Engine | Checks a plan before deployment | Yes |
| 9 | Approval and Deployment Engine | State machine, approval modes, execution | Yes |
| 10 | Optimization Engine | Budget, bid and pause recommendations | Yes |
| 11 | Attribution and Conversion Bridge | Links clicks to on-site behavior and purchases | Yes |
| 12 | Public API and Event Publisher | REST endpoints and Kafka events | Yes |
| 13 | Audit, Security, Observability | Logs, RBAC, secrets, monitoring | Yes |
| 14 | Ads Console UI | Connect, review, approve, monitor | Yes, minimal |

## 4. Component details

### 4.1 Account Connection Service

Responsibilities: run the OAuth 2.0 consent flow, store refresh tokens encrypted in a managed secrets store, and record which Google Ads customer accounts a workspace may use. Tokens never reach the browser.

Key points:

- Google Ads API calls need a developer token, which is approved by Google in access levels. Apply early and build against a test account first, because approval takes time and gates real accounts.
- Support both direct accounts and manager (MCC) accounts, which means storing the login customer ID alongside the target customer ID.
- Handle revoked or expired tokens by marking the connection AUTHENTICATION\_FAILED, pausing syncs and alerting the workspace.

### 4.2 Google Ads Connector

Implements the common interface from the PRD so Meta and future platforms stay interchangeable: authenticate, create\_campaign, update\_campaign, pause\_campaign, enable\_campaign, fetch\_metrics, manage\_budget, manage\_audience, manage\_creatives.

Internally it wraps the Google Ads API: GAQL queries (via search stream for large reports) for reads, and mutate operations for writes. Pin an API version in configuration and keep an upgrade checklist, since Google retires old versions on a schedule. Use the validate-only option on mutates for dry runs.

### 4.3 Sync Scheduler and Workers

Asynchronous workers keep the user-facing API fast. Each sync job is keyed by workspace, account and report type so it is idempotent.

- Reports: campaign, ad group, keyword, search term, geography, device, hour of day, and ad status (including disapprovals).
- Cadence: recent days refresh frequently (target freshness under 15 minutes per the PRD), older days are re-pulled to absorb Google's late conversion adjustments.
- Backfill on first connection, with a bounded history window.
- Per-account and per-developer-token rate limiting through an internal queue, with exponential backoff (the PRD retry ladder: 30 seconds, 2 minutes, 10 minutes, 30 minutes).
- A failed sync must never corrupt stored state: write to staging, then upsert.

### 4.4 Normalization Layer

Google reports money in micros, uses account-level time zones and currencies, and names fields differently from Meta. The layer converts everything into one GrowthOS schema so the AI module never sees Google-specific quirks.

Per day, per campaign (and per ad group and keyword at finer grain):

| Field | Notes |
| --- | --- |
| workspace\_id, platform, account\_id | Tenant and source |
| campaign\_id, campaign\_name, status | Status mapped to GrowthOS states |
| date, timezone | Account time zone kept explicitly |
| spend, currency | Converted from micros, original currency kept |
| impressions, clicks, conversions, conversion\_value | Google-reported |
| ctr, cpc, cpm, cpa, roas | Derived, but recomputable |
| synced\_at, source\_version | For freshness and lineage |

Store Google-reported conversions and GrowthOS-attributed conversions in separate columns so the two never silently mix.

### 4.5 Storage

Following the PRD stack: PostgreSQL for connections, campaign definitions, approvals and audit metadata; ClickHouse for time-series performance data; Redis for hot reads and rate-limit counters; S3-compatible storage for raw report snapshots and creative assets. Every table carries workspace\_id and is isolated per tenant.

### 4.6 Campaign Planning Engine

Input: a natural-language goal such as "Increase weekend pizza orders from college students in Mumbai, CPA under ₹250". Output: a structured, editable campaign definition containing objective, geography, audience, budget, schedule, bid strategy, keywords, ad copy requirements and conversion goal.

Design rules:

- Always show the interpreted configuration to the user before anything is deployed.
- Keep business intent separate from platform implementation, so the same goal can become a Google Search plan and a Meta plan.
- The LLM may draft and explain, but required fields (objective, budget, destination URL) are validated by code.

### 4.7 Keyword and Audience Research

Keywords are grouped as high intent, medium intent, discovery, branded, competitor and long-tail, with a recommended negative keyword list. Inputs: the goal, landing page content, historical search-term data and conversion performance. Audience suggestions use geography, demographics and customer segments where Customer Intelligence or Loyalty can supply them (Proposed, see section 8).

### 4.8 Validation Engine

Blocks deployment unless these pass: connected account, valid authentication, valid objective, valid budget (above platform minimum), valid destination URL, valid audience, valid ad copy (length and policy basics), platform compatibility. Failures return structured, human-readable errors.

### 4.9 Approval and Deployment Engine

A state machine from the PRD: DRAFT, VALIDATING, AWAITING\_APPROVAL, APPROVED, DEPLOYING, ACTIVE, with failure states VALIDATION\_FAILED, DEPLOYMENT\_FAILED, PLATFORM\_REJECTED and AUTHENTICATION\_FAILED. Every deployment request is versioned.

Three operating modes apply to every change:

- Manual: the system only recommends.
- Approval: the system proposes and waits for a person.
- Autonomous: the system executes inside configured limits (for example maximum budget increase 15 percent, maximum daily spend, minimum ROAS). Anything outside the limits falls back to approval. Autonomous mode is off by default.

Every executed change records who or what triggered it, the before and after values, and supports rollback for reversible operations.

### 4.10 Optimization Engine

The Ads module's own recommendation layer, running the PRD's loop: collect performance, analyze, identify opportunity, recommend, check policy, approve or execute, measure, repeat. Typical recommendations are budget reallocation between campaigns, pausing a campaign that stays below a ROAS floor, adding negative keywords from search-term waste, and flagging keywords that hit their daily budget cap while converting well.

Guardrails against noise: minimum sample size, statistical significance, historical baseline, campaign maturity (learning periods) and seasonality. Budget changes respect configured caps. The engine never claims it can guarantee winning an auction.

### 4.11 Attribution and Conversion Bridge

This is what makes optimization about business outcomes rather than clicks.

- Capture the Google click ID (gclid) and UTM parameters on landing, through the Behavior Intelligence SDK, and keep them on the session.
- Associate downstream events (product view, checkout, purchase) with the click, so the ads data can be joined to behavior.
- Optionally upload offline or enhanced conversions back to Google so its bidding learns from real purchases. Respect consent and legal limits.
- Models for the MVP: last-touch, first-touch and campaign-level attribution.

### 4.12 Public API and Event Publisher

Detailed in section 5. All endpoints are versioned, workspace-authorized and audited.

### 4.13 Audit, Security and Observability

- RBAC: only roles such as Owner, Admin and Marketing Manager can connect accounts, approve and deploy. Analysts and Viewers read only.
- Immutable audit records for connections, plans, approvals, deployments, budget changes and automated actions.
- Metrics, logs and traces for sync lag, API error rate, rate-limit hits, queue depth, deployment success rate, and token health, with alerts on failures.

### 4.14 Ads Console UI

Minimal for the MVP: connect account, view synced campaigns and metrics, review and edit an AI-drafted plan, approve or reject recommendations, see deployment status and audit history. Advanced users can inspect the raw platform configuration behind any summary.

## 5. APIs and events

REST endpoints (all under /api/v1/ads, from the PRD surface):

| Endpoint | Purpose |
| --- | --- |
| POST /accounts/connect, GET /accounts | Link and list ad accounts |
| POST /campaigns/plan | Natural language to draft plan |
| POST /campaigns, GET and PATCH /campaigns/{id} | Create, read, edit |
| POST /campaigns/{id}/pause, /activate | Status control |
| GET /campaigns/{id}/metrics | Normalized performance |
| GET /recommendations, POST /recommendations/{id}/approve | Ads-side recommendations |

Events published to Kafka: ads.account.connected, ads.campaign.created, ads.campaign.deployed, ads.campaign.activated, ads.campaign.paused, ads.campaign.failed, ads.metrics.updated, ads.recommendation.generated, ads.recommendation.approved, ads.optimization.executed, ads.budget.changed. Payloads carry unique event IDs so consumers can process them idempotently.

## 6. Integration with the AI module

The AI module here means the Module 4 work already in progress: the Metrics Engine, the Digest and Anomaly Engine, and the principle that numbers are computed deterministically and the LLM only narrates them. The Google Ads module should plug into exactly those pieces and change nothing about that principle.

### 6.1 What the AI module needs from Google Ads

- A normalized performance feed per tenant (section 4.4), with daily grain at campaign level and optional finer grain.
- Freshness and completeness metadata, so the Digest can say when data is stale or partial instead of guessing.
- Campaign state and change history (budgets, status, bid strategy), so anomalies can be explained by what changed.
- Attribution-joined outcomes (spend against GrowthOS-attributed purchases), which are the basis for true CAC and ROAS.

### 6.2 Connection points

| AI module part | Google Ads input | Result |
| --- | --- | --- |
| Metrics Engine | Daily normalized rows | New deterministic metrics: spend, CPA, ROAS, CTR, CVR, blended CAC, budget pacing |
| Metrics Engine | Attributed purchases from the SDK | ROAS and CAC from GrowthOS data, shown next to Google-reported values |
| Anomaly Engine | Metric time series plus change history | Detectors for spend spikes, CPA or ROAS drift, impression drops, disapproved ads, pacing breaks |
| Digest | Anomaly findings with numbers attached | LLM narrates findings, never computes them |
| Tenant templates | Per-vertical thresholds | qsr\_delivery template gets ad thresholds, for example weekend and evening seasonality for Domino's India |

Because the Metrics Engine and anomaly detectors are deterministic, the Ads data adds new inputs and new metric definitions only. The Digest keeps its current contract: structured facts in, narrative out.

### 6.3 Data contract (Proposed)

The cleanest boundary is the one the PRD already prescribes: the AI module does not touch the Ads module's database.

- Pull path: the AI module calls GET /campaigns/{id}/metrics and a bulk metrics endpoint with date, workspace and grain parameters.
- Push path: the AI module subscribes to ads.metrics.updated and re-runs affected metrics and anomaly checks, instead of polling.
- Versioned schema: a schema version field on every payload so metric definitions can evolve without silent breakage.
- Tenant scoping: every request and event carries workspace\_id, and the AI module only reads the tenant it is serving.

### 6.4 Acting on AI findings (Proposed)

Start read-only. When write-back is added, keep the loop explicit:

1. The AI module produces a recommendation with evidence and a confidence score, from deterministic metrics.
2. It is submitted to the Ads module as a structured action request (target campaign, change type, parameters). The AI module never calls Google itself.
3. The Ads module validates it against account limits and approval mode, then queues it for approval or, in Autonomous mode inside policy, executes it.
4. The result is published as an event, and the AI module records expected against actual outcome for future recommendations.

Whether the AI module emits these requests, or the Ads Optimization Engine (4.10) does, is an open decision; see section 13.

## 7. End-to-end flow

Example: Domino's India weekend campaign.

1. Manager enters the goal. Planning Engine drafts a Google Search plan with keywords, negatives, budget and a CPA target.
2. Validation passes, the manager approves, the Deployment Engine publishes through the Google Ads API.
3. Sync workers pull performance daily and intraday. Normalization writes to ClickHouse and publishes ads.metrics.updated.
4. The SDK ties gclid-tagged sessions to checkouts and purchases. Attributed outcomes are joined to spend.
5. The AI module's Metrics Engine recomputes CPA, ROAS and CAC. The anomaly detectors flag a Saturday-evening CPA jump.
6. The Digest narrates it with the figures and the recent budget change as context.
7. A recommendation is raised, approved, executed by the Ads module, and its outcome measured.

## 8. Integration with other modules (Proposed)

- Behavior Intelligence SDK to Ads: click IDs, UTMs, checkout abandonment signals. A campaign with healthy traffic but poor checkout conversion should not receive more budget; the signal tells the AI to say so.
- Customer Intelligence and Customer Graph to Ads: high-LTV and churn segments as audience inputs, for example Customer Match lists where Google allows it and consent exists.
- Loyalty to Ads: membership and reward-usage signals to exclude existing members from acquisition spend or to target lapsed members.
- Ads to everyone: ads.\* events for analytics, governance and audit.

Identity resolution stays central. The Ads module consumes resolved identifiers and never merges profiles itself.

## 9. Security, scale and edge cases

- Security: OAuth 2.0, encrypted token storage with rotation, workspace isolation, RBAC, TLS and encryption at rest, audit logs, no tokens in frontend clients.
- Scale: asynchronous workers per account, horizontally scalable connectors, rate limits enforced per platform and account, queues that keep Google API limits away from user-facing latency.
- Edge cases: expired tokens, API rate limits, Google outages, campaign rejection, invalid creatives or landing pages, budgets below platform minimum, duplicate campaigns, insufficient conversion data, delayed or retroactively adjusted conversions, attribution mismatch between Google and GrowthOS, conflicting optimization rules. A platform failure must never corrupt GrowthOS campaign state.

## 10. Build phases

1. Foundations: account connection, token vault, schemas, mock Google responses.
2. Read path: sync workers, normalization, ClickHouse tables, metrics endpoints.
3. AI integration, read-only: feed Metrics Engine and anomaly detectors, extend the qsr\_delivery template, Digest coverage.
4. Planning and deployment: plan drafting, validation, approval states, deployment, audit.
5. Attribution bridge: gclid capture, SDK joins, optional conversion upload.
6. Optimization and write-back: recommendations, approval mode, guarded autonomous mode.

Phase 3 delivers the most visible value with the least risk, so it comes before any write-back.

## 11. Testing

- Unit tests for normalization (micros, time zones, currency) and every deterministic metric, in the same style as the AI module's existing test suites.
- Contract tests between the Ads module and the AI module on the metrics schema.
- Recorded-response fixtures for the Google Ads API, plus a Google test account for integration tests.
- Failure tests: expired tokens, rate limits, partial failures, duplicate event delivery.
- Synthetic data replay for anomaly detectors, as already done for the Digest.

## 12. Success metrics and definition of done

Targets taken from the PRD: deployment success above 98 percent, API synchronization success above 99 percent, metric freshness under 15 minutes, duplicate campaign rate under 0.1 percent, OAuth success above 99 percent, campaign creation under 5 minutes.

Done when: accounts connect through OAuth, performance syncs and normalizes, the AI module computes ads metrics and anomalies from it, a campaign can be drafted, approved and deployed, all changes are audited, failures and rate limits are handled, and monitoring plus documentation exist.

## 13. Open questions

- Who owns the Ads module build, and what is its real data-access interface today? This document proposes one; it needs confirming.
- Which Google Ads access level and test account will be available first?
- Should action requests come from the AI module or from the Ads Optimization Engine, so recommendations are not generated twice?
- Is GrowthOS-attributed conversion data authoritative for ROAS, with Google-reported shown alongside, or the reverse?
- Which currency, time zone and weekend definition does the Domino's India demo tenant use?

## Appendix: Barebone Pipeline (Minimal MVP)

To make the entire Ads-to-AI pipeline work end-to-end with no production concerns, build only these parts. Everything else is stubbed.

### Strictly Required

**1. Account Connection (Section 4.1)**

- OAuth flow to get and store refresh token
- Read the test client customer ID from Google Ads console
- Store in plaintext or a simple env file (non-prod is fine)
- One endpoint: POST /api/v1/accounts/connect with OAuth code → returns success

**2. Google Ads Connector (Section 4.2)**

- Thin wrapper around the official google-ads Python library
- Two methods: fetch\_metrics(customer\_id, date\_range) and create\_campaign(plan)
- For now, just read-only. fetch\_metrics does GAQL search for campaigns, ad groups, keywords, search terms
- Mock create\_campaign (accept and log, don't call Google yet)
- One endpoint: GET /api/v1/accounts/{account\_id}/sync → triggers a fetch

**3. Sync Workers (Section 4.3)**

- Background job that runs every 2 hours: pull yesterday's reports
- Call the connector's fetch\_metrics
- Write raw results to S3 or local disk (backup)
- Pass to normalization
- No retry logic, no rate limiting, no incremental sync. Single job, single thread

**4. Normalization Layer (Section 4.4)**

- Convert Google's response to the 12-field schema (workspace\_id, platform, account\_id, campaign\_id, date, spend, impressions, clicks, conversions, ctr, cpc, cpa)
- Hardcode currency as INR, timezone as Asia/Kolkata
- Derive ctr, cpc, cpa from spend and counts
- Load into PostgreSQL table `ads_campaigns_daily`

**5. Storage (Section 4.5)**

- PostgreSQL: one table `ads_campaigns_daily` with the 12 fields + created\_at
- ClickHouse: mirror the same table for analytics (optional, can skip for barebone)
- No secrets vault. Hardcode or use .env

**6. Metrics API Endpoint (Section 5)**

- GET /api/v1/campaigns/{campaign\_id}/metrics?start\_date=X&end\_date=Y
- Query `ads_campaigns_daily`, return JSON
- GET /api/v1/campaigns/metrics/bulk?workspace=X → return all campaigns for a workspace
- No pagination, no filtering, just raw rows

**7. Event Publisher (Section 5)**

- After sync, publish one event: ads.metrics.updated with { workspace\_id, account\_id, date, record\_count }
- Kafka or HTTP POST to a local webhook endpoint (you'll define for the AI module)
- Fire and forget, no retry

### Can Wait (or Stub)

- Campaign Planning Engine (4.6): POST /campaigns/plan returns a dummy template. No AI drafting.
- Keyword and Audience Research (4.7): Skip entirely.
- Validation Engine (4.8): Accept anything, no checks.
- Approval and Deployment Engine (4.9): Accept campaign def, log it, pretend it deployed. Don't call Google.
- Optimization Engine (4.10): Skip entirely.
- Attribution Bridge (4.11): Skip. No gclid or conversions yet.
- Audit and Security (4.13): Log to stdout, no encryption, no RBAC.
- Console UI (4.14): None. Use curl or Postman.

### Implementation Checklist

- [ ] Google Cloud Console: create project, enable Ads API, OAuth credentials
- [ ] Google Ads Console: create test manager and test client accounts, note IDs
- [ ] OAuth token storage (hardcoded or .env file)
- [ ] Install google-ads library in your dev environment
- [ ] Write connector.py: fetch\_metrics method that calls GAQL
- [ ] Write normalization.py: convert rows to 12-field schema
- [ ] PostgreSQL table ads\_campaigns\_daily
- [ ] FastAPI: implement the 7 endpoints above
- [ ] Sync job: hourly pull of yesterday's data
- [ ] Event publish: after sync, send ads.metrics.updated
- [ ] Test: pull data, verify in DB, hit metrics endpoint, see event

### Code Structure (Suggested)

```
ads-module/
├── connector.py          # Google Ads API wrapper
├── normalize.py          # Convert Google → GrowthOS schema
├── models.py             # SQLAlchemy table for ads_campaigns_daily
├── api.py                # FastAPI endpoints
├── sync.py               # Background job
├── publish.py            # Event sender
├── main.py               # App entry, scheduler setup
├── requirements.txt      # google-ads, fastapi, sqlalchemy, psycopg2
└── .env                  # Client ID, secret, refresh token, customer IDs
```

### Expected Data Flow

```
Sync Job (hourly)
  ↓
Connector.fetch_metrics(test_customer_id, yesterday)
  ↓
Google Ads API → GAQL → Campaigns + metrics
  ↓
Normalize to 12 fields
  ↓
INSERT into ads_campaigns_daily
  ↓
Publish ads.metrics.updated event
  ↓
AI Module GET /campaigns/metrics/bulk → reads ads_campaigns_daily → computes metrics
```

No approval, no deployment, no optimization, no creative. Just data flow.

### Timeline

- Days 1–2: Console setup, account creation, OAuth token
- Days 3–4: Connector, first GAQL call, verify data
- Days 5–6: Normalization, PostgreSQL table, insert
- Days 7–8: FastAPI endpoints, sync job
- Days 9–10: Event publishing, end-to-end test

You can hand this to the AI module team by day 10. They call the metrics endpoint, subscribe to the event, and start building their Metrics Engine and anomaly detectors on real Google Ads data.
