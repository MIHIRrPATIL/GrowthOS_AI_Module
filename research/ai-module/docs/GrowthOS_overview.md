# GrowthOS Product Requirements Document (PRD)

---

# 1\. Overview

## Product Name

**GrowthOS**

---

## Vision

GrowthOS is an AI-native Growth Operating System that enables businesses to acquire customers, optimize conversions, retain users, and understand customer behavior through a unified reasoning engine.

Unlike conventional marketing tools that present fragmented dashboards and isolated metrics, GrowthOS transforms high-level business objectives into actionable execution plans. Users interact with the platform using natural language, while the AI orchestrates campaign creation, customer intelligence, behavioral analysis, workflow automation, and continuous optimization across the entire customer lifecycle.

GrowthOS serves as the operational intelligence layer for modern businesses by connecting advertising platforms, websites, mobile applications, customer interactions, loyalty programs, and internal business systems into a single semantic decision-making platform.

---

## Problem Statement

Modern organizations rely on numerous disconnected tools to manage growth, including advertising platforms, analytics software, customer data platforms, loyalty systems, heatmap tools, CRM solutions, and reporting dashboards.

This fragmentation creates several challenges:

* Marketing teams spend significant time switching between platforms.  
* Business decisions rely on interpreting dashboards instead of receiving recommendations.  
* Customer data is fragmented across multiple systems.  
* Growth opportunities are identified reactively rather than proactively.  
* Manual optimization limits operational efficiency.  
* Executives lack unified visibility into customer acquisition, conversion, retention, and lifetime value.

GrowthOS addresses these challenges by replacing fragmented analytics with an AI reasoning platform capable of understanding business objectives, synthesizing data from multiple sources, recommending actions, and optionally executing approved optimizations.

---

## Target Audience

GrowthOS is designed for organizations ranging from rapidly growing startups to enterprise businesses that require centralized growth intelligence.

Primary users include:

* Startup founders  
* CEOs  
* Chief Marketing Officers  
* Marketing Managers  
* Growth Teams  
* Product Managers  
* Customer Success Teams  
* Marketing Agencies  
* Data Analysts  
* Engineering Teams

The platform follows a Progressive Abstraction model, ensuring that every stakeholder receives information appropriate to their technical expertise.

---

## Value Proposition

GrowthOS provides a unified AI-powered operating system for business growth by combining:

* Customer acquisition  
* Conversion optimization  
* Customer retention  
* Customer intelligence

into a single explainable reasoning platform.

Instead of merely reporting historical metrics, GrowthOS continuously answers business questions such as:

* Why are conversions decreasing?  
* Which campaigns should receive more budget?  
* Which customers are likely to churn?  
* Which landing page should be optimized?  
* Which loyalty rewards generate repeat purchases?  
* What actions should be taken next?

The platform delivers recommendations together with confidence scores and supporting evidence, enabling organizations to make faster and more informed decisions.

---

## One-Line Summary

**GrowthOS is an AI-native Growth Operating System that continuously acquires customers, optimizes conversions, improves retention, and explains business growth through semantic intelligence.**

---

# 1.0 Illustrative Example

Throughout this document, Domino's Pizza is used as the reference organization.

Domino's wants to launch a weekend campaign targeting college students in Mumbai while simultaneously improving online ordering conversions and increasing repeat purchases.

Instead of manually configuring advertising campaigns, tracking tools, loyalty programs, and customer analytics, Domino's describes its objective using natural language.

GrowthOS automatically plans, executes, monitors, and optimizes the complete growth lifecycle.

| User Action | Event/Input | System Behavior | Result |
| ----- | ----- | ----- | ----- |
| Marketing Manager enters "Increase weekend pizza orders among college students in Mumbai." | Natural language prompt | AI generates campaign objective, audience, keywords, creatives, bidding strategy, and budget recommendations | Draft campaign created |
| Campaign approved | Approval event | GrowthOS deploys campaigns to Google Ads and Meta Ads | Campaigns go live |
| Customer clicks Google advertisement | Ad click | Tracking identifiers associated with customer profile | Attribution initialized |
| Customer browses Domino's website | Website SDK events | Session events, scrolling behavior, clicks, dwell time, and navigation recorded | Behavioral timeline created |
| Customer abandons checkout | Exit event | AI identifies probable abandonment reasons and recommends UX improvements | Conversion recommendation generated |
| Customer completes purchase | Purchase event | Customer Graph updated with purchase history, attribution, and loyalty eligibility | Loyalty points awarded |
| Returning customer revisits after seven days | Session event | AI predicts high repeat purchase probability and triggers personalized offer | Increased retention opportunity |
| CEO requests weekly summary | Natural language query | AI generates executive report with explanations, KPIs, forecasts, and recommended actions | Strategic business insight delivered |

This example demonstrates how all four intelligence layers cooperate through a shared AI reasoning engine.

---

# 1.1 Locked MVP Decisions

The following architectural decisions are locked for the MVP release.

| Category | MVP Decision |
| ----- | ----- |
| Deployment | Cloud-native multi-tenant SaaS |
| Platforms | Web application with browser extension and JavaScript SDK |
| Authentication | OAuth 2.0, Google Sign-In, Microsoft Sign-In, Email Authentication |
| Organizations | Multi-workspace architecture |
| AI Model | Large Language Model with Retrieval-Augmented Generation and deterministic business rule engine |
| Event Pipeline | Real-time event streaming with asynchronous processing |
| Customer Graph | Unified customer graph storing behavioral, transactional, campaign, and loyalty relationships |
| Integrations | Google Ads, Meta Ads, Shopify, Stripe, GA4, Webhooks |
| APIs | REST APIs with versioning and webhook support |
| SDKs | JavaScript SDK, Mobile SDK (Phase 2), Server SDK |
| Loyalty Platform | Browser extension with centralized loyalty wallet |
| Payments | Stripe Billing |
| Analytics | Event-driven analytics with semantic reasoning layer |
| Storage | Relational database for operational data and graph database for customer relationships |
| Security | RBAC, encryption at rest, encryption in transit, audit logs |
| Deployment Model | Kubernetes-based containerized microservices |
| Observability | Centralized logging, metrics, tracing, alerting |

The above decisions are considered architectural constraints and should not be modified without a formal architecture review.

---

# 1.2 Personas

## Founder

**Responsibilities**

* Product strategy  
* Growth  
* Fundraising  
* Business decisions

**Goals**

* Increase revenue  
* Validate growth  
* Minimize operational effort

**Pain Points**

* Fragmented tools  
* Lack of business visibility  
* Slow experimentation

**Technical Proficiency**

Medium

GrowthOS Experience:

Receives AI-generated business recommendations, forecasts, and strategic insights without requiring technical expertise.

---

## Chief Executive Officer (CEO)

**Responsibilities**

* Company performance  
* Strategic planning  
* Financial growth

**Goals**

* Improve profitability  
* Increase customer acquisition efficiency  
* Monitor organizational KPIs

**Pain Points**

* Difficult-to-interpret dashboards  
* Delayed reporting  
* Limited visibility

**Technical Proficiency**

Low

GrowthOS Experience:

Executive dashboard with semantic summaries, AI recommendations, forecasts, and confidence scores.

---

## Marketing Manager

**Responsibilities**

* Campaign execution  
* Advertising budgets  
* Performance optimization

**Goals**

* Improve ROAS  
* Reduce CPA  
* Increase conversions

**Pain Points**

* Manual campaign optimization  
* Platform switching  
* Audience research

**Technical Proficiency**

Medium

GrowthOS Experience:

Natural language campaign creation, AI optimization, automated budget recommendations, and approval workflows.

---

## Growth Analyst

**Responsibilities**

* Performance analysis  
* Funnel optimization  
* Experimentation

**Goals**

* Identify opportunities  
* Improve conversion rates  
* Produce reports

**Pain Points**

* Manual reporting  
* Data inconsistencies  
* Complex segmentation

**Technical Proficiency**

High

GrowthOS Experience:

Detailed dashboards, filters, event exploration, customer segmentation, and AI-assisted analysis.

---

## Product Manager

**Responsibilities**

* Product optimization  
* Feature prioritization  
* Customer journey improvement

**Goals**

* Reduce friction  
* Increase engagement  
* Improve activation

**Pain Points**

* Limited behavioral visibility  
* Difficult experiment analysis

**Technical Proficiency**

Medium to High

GrowthOS Experience:

Behavior analytics, funnel intelligence, UX recommendations, and session insights.

---

## Engineer

**Responsibilities**

* Platform integration  
* SDK implementation  
* API management

**Goals**

* Reliable integrations  
* Stable deployments  
* Observability

**Pain Points**

* Debugging integrations  
* Tracking implementation issues

**Technical Proficiency**

High

GrowthOS Experience:

Raw event explorer, SDK diagnostics, webhook monitoring, API logs, and system observability tools.

---

## Marketing Agency

**Responsibilities**

* Multi-client campaign management  
* Performance reporting  
* Client growth

**Goals**

* Scale operations  
* Standardize reporting  
* Improve client outcomes

**Pain Points**

* Managing multiple advertising platforms  
* Manual reporting  
* Client communication

**Technical Proficiency**

Medium

GrowthOS Experience:

Multi-workspace support, client segmentation, white-label reporting, and centralized optimization.

---

# 1.3 Success Metrics

GrowthOS success is measured using both platform adoption metrics and measurable customer business outcomes.

## Product Adoption KPIs

| KPI | Target |
| ----- | ----- |
| Workspace Activation Rate | \>80% |
| SDK Installation Success | \>95% |
| Connected Advertising Platforms | Average 2+ per workspace |
| Weekly Active Organizations | \>70% |
| AI Recommendation Adoption | \>60% |
| Autonomous Workflow Adoption | \>30% |
| Loyalty Program Activation | \>40% |
| Average Daily Queries to AI | 25+ per organization |

---

## Customer Business Impact KPIs

| KPI | Target |
| ----- | ----- |
| Increase in ROAS | \+20% |
| Reduction in CPA | \-15% |
| Improvement in Conversion Rate | \+10% |
| Increase in Repeat Purchases | \+15% |
| Increase in Customer Lifetime Value | \+12% |
| Reduction in Customer Churn | \-10% |
| Reduction in Manual Campaign Management Time | \-60% |
| AI Recommendation Accuracy | \>90% confidence agreement |

---

## AI Quality Metrics

The AI Growth Brain will be evaluated using operational quality metrics.

| Metric | Objective |
| ----- | ----- |
| Recommendation Acceptance Rate | \>65% |
| False Positive Recommendation Rate | \<5% |
| Average Response Time | \<5 seconds |
| Explanation Completeness | 100% |
| Confidence Score Availability | 100% |
| Automation Success Rate | \>98% |

These metrics ensure that GrowthOS is evaluated not only by platform usage but also by measurable improvements in customer business performance and AI decision quality.

---

# 2\. Scope

## Included Functionality (MVP)

GrowthOS MVP delivers a unified AI-native growth platform across four intelligence layers:

### Acquisition Intelligence

* Semantic campaign creation  
* Google Ads integration  
* Meta Ads integration  
* AI campaign recommendations  
* Audience discovery  
* Keyword recommendations  
* Budget optimization  
* Campaign performance monitoring

### Conversion Intelligence

* JavaScript Website SDK  
* Event collection  
* Session intelligence  
* Heatmaps  
* Funnel analytics  
* Behavioral analytics  
* AI conversion recommendations

### Retention Intelligence

* Loyalty program management  
* Browser extension  
* Unified loyalty wallet  
* Reward rules  
* Referral programs  
* Personalized offers

### Customer Intelligence

* Unified customer graph  
* Dynamic customer profiles  
* Segmentation  
* Customer journey visualization  
* Churn prediction  
* Lifetime value estimation

### Platform Capabilities

* AI Growth Brain  
* Progressive Abstraction  
* Manual / Approval / Autonomous modes  
* Explainable AI recommendations  
* Confidence scoring  
* Workspace management  
* RBAC  
* Audit logs

---

## Out of Scope (MVP)

The following capabilities are intentionally excluded.

* Native CRM  
* Email marketing platform  
* SMS gateway  
* AI image generation  
* AI video generation  
* Social media publishing  
* Affiliate management  
* Marketplace integrations  
* ERP integrations  
* Accounting software  
* Offline POS integrations  
* Data warehouse replacement  
* Native BI engine  
* Multi-region deployment  
* Custom ML model training

These capabilities are planned for future releases.

---

## Supported Platforms

* Web Application  
* Browser Extension  
* JavaScript SDK  
* REST APIs  
* Webhooks

Phase 2

* Android SDK  
* iOS SDK  
* Desktop application

---

## Supported Integrations

Advertising

* Google Ads  
* Meta Ads

Commerce

* Shopify  
* Stripe

Analytics

* Google Analytics 4

Communication

* Slack  
* Email  
* Webhooks

Future integrations will follow a connector-based architecture.

---

## Technical Assumptions

* Internet connectivity required  
* OAuth authentication  
* Event-driven architecture  
* Cloud-hosted deployment  
* Multi-tenant architecture  
* API-first implementation  
* AI recommendations generated asynchronously where appropriate

---

## MVP Limitations

* English language only  
* Google Ads & Meta Ads only  
* Website SDK only  
* Single AI model  
* Browser extension supported only on Chromium browsers  
* Autonomous mode disabled by default  
* Maximum event retention: 12 months

---

# 3\. Epic Overview

| Epic | Description | Priority | Dependencies |
| ----- | ----- | ----- | ----- |
| Workspace & Organization | Tenant creation, authentication, RBAC | P0 | None |
| AI Growth Brain | Central reasoning engine | P0 | Workspace |
| Acquisition Intelligence | Semantic campaign planning | P0 | AI Brain |
| Campaign Deployment Engine | Deploy campaigns to advertising platforms | P0 | Acquisition |
| Website SDK & Event Collection | Behavioral tracking | P0 | Workspace |
| Conversion Intelligence | Session analysis & optimization | P0 | SDK |
| Customer Graph | Unified customer knowledge graph | P1 | SDK |
| Customer Intelligence | Profiling & segmentation | P1 | Customer Graph |
| Loyalty & Retention | Rewards ecosystem | P1 | Customer Intelligence |
| Progressive Abstraction | Multi-layer experience | P1 | AI Brain |
| Automation Engine | Workflows & approvals | P1 | All modules |
| Governance & Observability | Audit, logs, monitoring | P1 | Platform |

---

# 4\. Detailed Functional Requirements

---

# Epic 1 — Workspace & Organization

## Overview

Organizations require isolated workspaces where teams securely manage campaigns, customers, integrations, and AI recommendations.

### User Workflow

1. Create organization.  
2. Invite members.  
3. Assign roles.  
4. Connect advertising accounts.  
5. Configure workspace preferences.

### Business Logic

* Every organization owns isolated resources.  
* Users may belong to multiple workspaces.  
* Billing is workspace-specific.

### Validation

* Unique workspace name.  
* Verified email required.  
* OAuth authentication mandatory for integrations.

### Permissions

Supported roles:

* Owner  
* Admin  
* Marketing Manager  
* Analyst  
* Viewer  
* Engineer

Each role has predefined RBAC permissions.

### APIs

* Create Workspace  
* Invite Member  
* Update Role  
* List Organizations

### Edge Cases

* Duplicate invitations  
* Revoked OAuth tokens  
* Suspended workspace

### Notifications

* Invitation emails  
* Role changes  
* Failed integrations

### Audit

Every authentication, invitation, permission change, and workspace update is recorded.

### Acceptance Criteria

* Workspace isolation enforced.  
* RBAC applied.  
* Audit logs generated.  
* OAuth integrations successfully connected.

---

# Epic 2 — AI Growth Brain

## Overview

The AI Growth Brain is the central reasoning layer responsible for understanding business objectives, generating recommendations, explaining insights, and coordinating actions across GrowthOS.

### User Workflow

Users ask questions in natural language.

Example:

> "Why did conversions decrease yesterday?"

The AI retrieves business context, analyzes data, generates explanations, confidence scores, and recommended actions.

### Business Logic

Recommendations always include:

* Explanation  
* Evidence  
* Confidence Score  
* Suggested Actions

Recommendations never execute automatically unless Autonomous Mode is enabled.

### AI Behavior

The AI reasons across:

* Campaigns  
* Customer Graph  
* Behavioral Events  
* Loyalty Data  
* Historical Performance

### Edge Cases

* Missing data  
* Conflicting metrics  
* Low-confidence predictions

### Notifications

Critical recommendations generate alerts.

### Acceptance Criteria

* Every recommendation is explainable.  
* Confidence score always displayed.  
* Low-confidence recommendations clearly identified.

---

# Epic 3 — Acquisition Intelligence

## Overview

GrowthOS enables semantic campaign creation by translating business goals into optimized advertising campaigns.

### User Workflow

User enters:

> "Increase pizza sales among college students in Mumbai this weekend."

GrowthOS generates:

* Campaign Objective  
* Keywords  
* Audiences  
* Budget  
* Bidding Strategy  
* Creatives  
* Placements

### Business Logic

Campaigns remain editable before deployment.

AI validates platform compatibility.

### Validation

Required:

* Objective  
* Budget  
* Destination URL

### AI Behavior

AI performs:

* Audience discovery  
* Keyword research  
* Budget estimation  
* Competitor analysis  
* Bid recommendations

### Integrations

* Google Ads  
* Meta Ads

### Edge Cases

* Unsupported campaign objectives  
* Budget below platform minimum  
* Invalid landing pages

### Acceptance Criteria

* Campaign generated within seconds.  
* Recommendations editable.  
* Platform validation completed before publishing.

---

# Epic 4 — Campaign Deployment Engine

## Overview

This module converts approved campaign plans into executable advertising platform configurations.

### User Workflow

User approves campaign.

GrowthOS validates assets and deploys through connected APIs.

Deployment status updates in real time.

### Business Logic

Campaign deployment occurs only after:

* Asset validation  
* Budget validation  
* Authentication validation

Failed deployments automatically retry.

### APIs

* Google Ads API  
* Meta Marketing API

### Error Handling

* Expired OAuth  
* API rate limits  
* Invalid assets  
* Network failures

### Notifications

Users receive deployment status via:

* Email  
* In-app notification  
* Slack

### Audit

Every deployment request is versioned.

### Acceptance Criteria

* Successful deployment tracked.  
* Partial failures reported.  
* Retry mechanism operational.

---

# Epic 5 — Website SDK & Event Collection

## Overview

The Website SDK captures user interactions required for behavioral analysis and customer intelligence.

### User Workflow

Merchant installs JavaScript snippet.

Events begin streaming automatically.

### SDK Behavior

Captured events include:

* Page View  
* Click  
* Scroll  
* Hover  
* Session Duration  
* Exit Intent  
* Form Interaction  
* Checkout Events  
* Purchase Events

### Business Logic

Events are timestamped and associated with customer identifiers when available.

Anonymous users receive temporary session identifiers.

### Validation

Reject malformed events.

Deduplicate duplicate submissions.

### Edge Cases

* Offline users  
* Ad blockers  
* Duplicate SDK installation

### APIs

* Event ingestion endpoint  
* Batch upload endpoint

### Acceptance Criteria

* Events processed in near real time.  
* Anonymous sessions supported.  
* Duplicate events prevented.

---

# Epic 6 — Conversion Intelligence

## Overview

Conversion Intelligence analyzes behavioral events and identifies opportunities to improve user experience and increase conversions.

### User Workflow

Users open a funnel report or ask:

> "Why are customers abandoning checkout?"

GrowthOS generates behavioral insights and UX recommendations.

### Business Logic

AI correlates:

* Session behavior  
* Funnels  
* Heatmaps  
* Campaign attribution  
* Purchase history

### AI Behavior

Recommendations include:

* Checkout improvements  
* Landing page optimization  
* CTA placement  
* Pricing concerns  
* UX friction

Every recommendation includes confidence scores.

### Reporting

* Funnel visualization  
* Heatmaps  
* Session summaries  
* Behavioral trends

### Edge Cases

* Low sample size  
* Conflicting user behavior  
* Missing tracking events

### Acceptance Criteria

* AI identifies major conversion bottlenecks.  
* Recommendations are explainable.  
* Reports update continuously as new events arrive.

---

# Epic 7 — Customer Graph

## Overview

The Customer Graph serves as the unified source of truth for every customer interacting with the business. It consolidates advertising attribution, browsing behavior, purchases, loyalty activity, referrals, and engagement into a continuously evolving graph model.

### User Workflow

As customers interact with advertisements, websites, and loyalty programs, GrowthOS continuously updates their unified profile.

### Business Logic

Every customer receives a persistent profile linked across multiple identifiers, including anonymous sessions, authenticated accounts, devices, advertising attribution, and loyalty membership. Identity resolution merges profiles using configurable confidence rules.

### Validation

* Prevent duplicate customer identities.  
* Merge profiles only above configurable confidence thresholds.  
* Preserve historical identifiers.

### APIs

* Customer Lookup  
* Customer Merge  
* Customer Timeline  
* Identity Resolution

### AI Behavior

The AI continuously enriches customer profiles with inferred interests, purchasing patterns, preferred channels, and engagement scores.

### Edge Cases

* Multiple devices  
* Shared devices  
* Anonymous-to-authenticated transitions  
* Duplicate identities

### Audit Logging

All profile merges and identity resolutions are versioned and reversible.

### Acceptance Criteria

* Unified customer profile created.  
* Cross-session identity resolution supported.  
* Complete customer timeline available.  
* Customer graph updates in near real time.

---

# Epic 8 — Customer Intelligence

## Overview

Customer Intelligence transforms raw customer data into actionable business insights by predicting customer behavior, segmenting audiences, and recommending engagement strategies.

### User Workflow

Marketing teams query the AI using natural language or create dynamic customer segments through filters.

### Business Logic

Customer segments update automatically based on behavioral events, purchases, loyalty status, and predicted outcomes.

### AI Behavior

The AI generates:

* Customer Lifetime Value (LTV)  
* Churn Probability  
* Purchase Intent  
* Preferred Marketing Channel  
* Next Best Action  
* Recommended Offer

Every prediction includes supporting evidence and confidence scores.

### Validation

Predictions require minimum historical data before becoming available.

### Reporting

* Customer segmentation  
* Cohort analysis  
* Retention trends  
* LTV distribution  
* Churn analysis

### Edge Cases

* Sparse customer history  
* Seasonal purchasing behavior  
* Rapid behavioral changes

### Acceptance Criteria

* Dynamic segmentation operational.  
* AI predictions explainable.  
* Customer recommendations continuously updated.

---

# Epic 9 — Loyalty & Retention Intelligence

## Overview

Retention Intelligence enables organizations to build configurable loyalty programs while providing customers with a unified loyalty experience through a browser extension and centralized wallet.

### User Workflow

Organizations configure loyalty rules using natural language or predefined templates.

Customers automatically receive rewards during eligible purchases.

### Business Logic

Supported reward types include:

* Points  
* Cashback  
* Coupons  
* Referral rewards  
* Membership tiers  
* Promotional bonuses

Reward calculations execute immediately after qualifying events.

### Browser Extension

The extension automatically detects supported merchants during checkout and displays:

* Available points  
* Eligible rewards  
* Referral offers  
* Membership benefits

### Validation

Prevent duplicate rewards, fraudulent referrals, and repeated redemption attempts.

### Integrations

* Website SDK  
* Customer Graph  
* Payment Platforms

### Edge Cases

* Partial refunds  
* Order cancellations  
* Expired rewards

### Acceptance Criteria

* Loyalty programs configurable.  
* Browser extension functional.  
* Rewards calculated accurately.  
* Redemption fully auditable.

---

# Epic 10 — Progressive Abstraction Experience

## Overview

GrowthOS follows a Progressive Abstraction design philosophy, ensuring every user receives information appropriate to their responsibilities and technical proficiency.

### User Workflow

Users automatically receive personalized interfaces based on assigned roles.

Advanced users can progressively drill into underlying data.

### Abstraction Layers

**Executive Layer**

* Revenue  
* Growth  
* AI Summary  
* Strategic Recommendations

**Manager Layer**

* Campaigns  
* Funnels  
* Customer Segments  
* Optimization Suggestions

**Analyst Layer**

* Events  
* Metrics  
* Heatmaps  
* Filters  
* Cohorts

**Engineer Layer**

* SDK Logs  
* API Requests  
* Webhooks  
* Event Payloads  
* System Diagnostics

### Business Logic

No business information is hidden. Higher abstraction layers summarize lower-level data rather than restricting access.

### Acceptance Criteria

* Role-based interfaces operational.  
* Drill-down supported.  
* Consistent navigation across abstraction levels.

---

# Epic 11 — Automation Engine

## Overview

The Automation Engine enables organizations to automate operational workflows while maintaining configurable levels of human oversight.

### Operating Modes

**Manual Mode**

AI generates recommendations only.

**Approval Mode**

AI proposes actions requiring explicit user approval.

**Autonomous Mode**

Approved automation rules execute without manual intervention.

### Supported Automations

* Budget optimization  
* Campaign pausing  
* Campaign scaling  
* Customer segmentation  
* Loyalty issuance  
* Notifications  
* Workflow execution

### Business Logic

Every automation executes through rule evaluation.

Conflicting automations are prioritized using deterministic precedence rules.

### Validation

Automation rules require:

* Trigger  
* Condition  
* Action  
* Approval policy

### Notifications

Automation execution generates audit events and optional notifications.

### Edge Cases

* API failures  
* Duplicate triggers  
* Conflicting workflows

### Acceptance Criteria

* All three operating modes supported.  
* Automation history available.  
* Rollback supported for reversible operations.

---

# Epic 12 — Governance, Observability & Platform Operations

## Overview

GrowthOS provides enterprise-grade governance, monitoring, auditing, and operational visibility across every platform component.

### Capabilities

* Audit logging  
* API monitoring  
* SDK diagnostics  
* Event validation  
* System health  
* Integration status  
* AI recommendation history

### Business Logic

Every user action, AI recommendation, automation execution, deployment, configuration change, and integration update generates immutable audit events.

### Monitoring

System dashboards monitor:

* Event ingestion  
* API latency  
* Queue health  
* AI response time  
* Failed integrations  
* SDK health  
* Automation failures

### Error Handling

Automatic retries occur for transient failures.

Critical failures generate operational alerts.

### Compliance

Support:

* GDPR  
* SOC 2 readiness  
* Data retention policies  
* Right-to-delete workflows

### Acceptance Criteria

* Complete audit history available.  
* Platform health continuously monitored.  
* Compliance workflows operational.  
* Operational alerts generated within SLA.

---

# Cross-Epic Functional Requirements

The following requirements apply to every GrowthOS module.

| Category | Requirement |
| ----- | ----- |
| Authentication | OAuth 2.0 with secure token refresh |
| Authorization | Role-Based Access Control (RBAC) |
| Audit Logging | Immutable audit events for all critical actions |
| AI Recommendations | Must include explanation and confidence score |
| Error Handling | Structured error responses with retry support |
| Notifications | Configurable delivery preferences |
| APIs | Versioned REST APIs with consistent schemas |
| Webhooks | Idempotent event delivery |
| Observability | Metrics, logs, and distributed tracing |
| Security | Encryption in transit and at rest |

---

# AI Behavior Requirements

The AI Growth Brain must operate consistently across every intelligence layer.

## Explainability

Every recommendation must include:

* Business reasoning  
* Supporting evidence  
* Confidence score  
* Recommended action  
* Expected business impact

---

## Confidence Scores

Confidence scores range from **0–100%**.

Example:

| Recommendation | Confidence |
| ----- | ----- |
| Increase Campaign Budget | 96% |
| Checkout Friction Detected | 91% |
| Customer Likely to Churn | 84% |
| Landing Page Requires Redesign | 79% |

Recommendations below configurable thresholds are clearly labeled as low confidence and never executed automatically.

---

## Recommendation Lifecycle

Every recommendation follows the same lifecycle.

1. Data Collection  
2. Context Retrieval  
3. AI Reasoning  
4. Confidence Calculation  
5. Recommendation Generation  
6. User Approval (if required)  
7. Execution  
8. Outcome Evaluation  
9. Continuous Learning

---

## Enterprise Design Principles

GrowthOS adheres to the following product principles:

* AI-first interaction model  
* Semantic business intelligence  
* Explainable recommendations  
* Progressive abstraction  
* Human-in-the-loop automation  
* Enterprise security by default  
* API-first architecture  
* Event-driven platform  
* Continuous optimization  
* Auditability across all actions

These principles guide future product development and ensure consistency across all platform capabilities.

---

# Analytics

GrowthOS provides role-specific analytics through its Progressive Abstraction framework. Every dashboard is powered by the AI Growth Brain, ensuring that metrics are accompanied by explanations, recommendations, and confidence scores rather than isolated visualizations.

---

## Executive Dashboard

**Purpose**

Provide business leaders with an at-a-glance understanding of organizational growth.

### KPIs

* Revenue  
* Marketing Spend  
* Return on Ad Spend (ROAS)  
* Customer Acquisition Cost (CAC)  
* Customer Lifetime Value (LTV)  
* Active Customers  
* Churn Rate  
* Conversion Rate  
* Net Revenue Growth  
* AI Opportunity Score

### AI Insights

Examples include:

* "Revenue increased 14% week-over-week due to improved Meta campaign performance."  
* "Checkout abandonment is expected to increase unless shipping costs are optimized."  
* "Mumbai campaigns have reached audience saturation."

### Available Actions

* View explanation  
* Approve recommendations  
* Export executive report  
* Share summary

---

## Marketing Dashboard

**Purpose**

Enable marketing teams to monitor campaign performance and optimization opportunities.

### Metrics

* Impressions  
* Reach  
* Clicks  
* CTR  
* CPC  
* CPM  
* CPA  
* ROAS  
* Conversion Volume  
* Budget Utilization

### AI Features

* Campaign recommendations  
* Budget optimization  
* Audience expansion  
* Keyword suggestions  
* Creative fatigue detection  
* Competitor activity alerts

### Filters

* Date range  
* Campaign  
* Platform  
* Audience  
* Geography  
* Device  
* Product

---

## Customer Dashboard

**Purpose**

Provide a complete understanding of customer behavior and engagement.

### Metrics

* New Customers  
* Returning Customers  
* Purchase Frequency  
* Average Order Value  
* Loyalty Status  
* Churn Risk  
* Lifetime Value  
* Referral Activity

### AI Insights

* High-value customer segments  
* Predicted repeat purchases  
* Customers requiring engagement  
* Personalized offer recommendations

---

## AI Recommendation Dashboard

This dashboard centralizes every recommendation generated by the AI Growth Brain.

Each recommendation includes:

* Recommendation title  
* Business explanation  
* Supporting evidence  
* Confidence score  
* Estimated business impact  
* Current status  
* Approval history  
* Execution history

### Recommendation Status

* Draft  
* Awaiting Approval  
* Approved  
* Executed  
* Rejected  
* Archived

---

## Reporting

GrowthOS supports scheduled and on-demand reporting.

Supported report types:

* Executive Summary  
* Marketing Performance  
* Campaign Performance  
* Funnel Analysis  
* Customer Intelligence  
* Loyalty Performance  
* AI Recommendation History  
* Operational Health

Reports may be delivered as:

* PDF  
* CSV  
* Excel  
* REST API  
* Webhook payload

---

## Filters

Every analytical view supports consistent filtering.

Supported filters include:

* Workspace  
* Date  
* Campaign  
* Customer Segment  
* Geography  
* Device  
* Traffic Source  
* Loyalty Tier  
* Marketing Channel  
* Product  
* Conversion Type

---

## Exports

Users can export:

* Dashboards  
* Reports  
* Event Data  
* Customer Segments  
* Recommendation History  
* Campaign Performance  
* Funnel Reports

Exports respect user permissions and workspace boundaries.

---

## Operational Metrics

Platform health dashboards monitor:

* Event ingestion rate  
* Queue processing time  
* AI response latency  
* API success rate  
* SDK health  
* Webhook delivery success  
* Automation execution rate  
* Recommendation generation latency

---

# Notifications

GrowthOS delivers notifications through multiple channels while ensuring reliable delivery and complete auditability.

---

## Email Notifications

Supported events include:

* Campaign deployment  
* Campaign failure  
* Budget threshold reached  
* AI recommendations  
* Loyalty redemption  
* Weekly reports  
* Monthly business summaries  
* Workspace invitations

Emails are configurable per workspace.

---

## Webhooks

Organizations may subscribe to events including:

* Campaign Created  
* Campaign Updated  
* Recommendation Generated  
* Recommendation Approved  
* Customer Created  
* Loyalty Reward Issued  
* Purchase Completed  
* Automation Executed

Webhook payloads include unique event identifiers to support idempotent processing.

---

## Slack Notifications

Slack integration supports:

* AI recommendations  
* Campaign alerts  
* Deployment status  
* Operational incidents  
* Approval requests

Interactive actions allow users to approve recommendations directly from Slack.

---

## Browser Notifications

Supported notifications include:

* Pending approvals  
* Failed deployments  
* Loyalty redemptions  
* High-priority AI recommendations  
* Platform incidents

Users can customize notification preferences.

---

## Retry Logic

Transient failures follow exponential backoff.

Retry policy:

* Initial attempt  
* Retry after 30 seconds  
* Retry after 2 minutes  
* Retry after 10 minutes  
* Final retry after 30 minutes

Permanent failures generate operational alerts.

---

## Delivery Guarantees

GrowthOS targets at-least-once delivery for asynchronous notifications.

Duplicate events are prevented using unique event identifiers.

Failed deliveries remain visible in operational dashboards until resolved.

---

## Operational Alerts

Critical alerts include:

* Integration failure  
* Event ingestion backlog  
* AI service degradation  
* SDK health issues  
* Webhook failures  
* Authentication failures  
* Storage thresholds  
* Automation execution failures

Alerts include severity levels:

* Informational  
* Warning  
* Critical

---

# Security

GrowthOS is designed using enterprise security principles.

---

## Authentication

Supported authentication methods:

* Google OAuth  
* Microsoft OAuth  
* Email & Password  
* Multi-Factor Authentication (MFA)

Session tokens automatically expire after configurable inactivity periods.

---

## Authorization

Role-Based Access Control (RBAC) governs access.

Default roles:

* Owner  
* Admin  
* Marketing Manager  
* Analyst  
* Engineer  
* Viewer

Permissions are enforced at both API and UI levels.

---

## Encryption

All data is encrypted:

**In Transit**

* TLS 1.3

**At Rest**

* AES-256

Sensitive credentials are stored using managed secrets.

---

## Audit Logs

Every critical operation generates immutable audit records.

Examples:

* Login  
* Permission changes  
* Campaign deployment  
* Recommendation approval  
* Automation execution  
* SDK registration  
* API key creation

Audit logs are searchable and exportable.

---

## Compliance

GrowthOS is designed for:

* GDPR  
* SOC 2 readiness  
* Data retention policies  
* Right-to-access requests  
* Right-to-delete requests

Compliance workflows are configurable per workspace.

---

## Monitoring

Security monitoring includes:

* Failed login attempts  
* Suspicious API activity  
* OAuth failures  
* Privilege escalation  
* Rate-limit violations  
* Data export activity

Anomaly detection generates immediate alerts for high-risk events.

---

## Disaster Recovery

Objectives:

* Recovery Time Objective (RTO): \< 2 hours  
* Recovery Point Objective (RPO): \< 15 minutes

Daily encrypted backups are maintained with geographically redundant storage.

---

## AI Governance

AI recommendations must satisfy the following requirements:

* Explainable reasoning  
* Confidence score  
* Supporting evidence  
* Human approval when required  
* Complete recommendation history  
* Version tracking

The AI Growth Brain never executes autonomous actions outside approved organizational policies.

---

# Acceptance Narrative

## Domino's End-to-End Journey

Domino's creates a new GrowthOS workspace and connects its Google Ads, Meta Ads, Shopify, Stripe, and Slack integrations.

The Marketing Manager enters the following prompt:

> "Increase weekend pizza orders among college students in Mumbai while improving repeat purchases."

The AI Growth Brain analyzes historical campaign performance, audience data, purchasing behavior, and competitor trends.

GrowthOS generates:

* Search campaigns for Google Ads  
* Awareness campaigns for Meta Ads  
* Recommended keywords  
* Audience segments  
* Budget allocation  
* Bidding strategy  
* Creative recommendations

The manager reviews the proposed campaign and approves deployment.

The Campaign Deployment Engine validates assets, verifies authentication, and publishes campaigns through the connected advertising APIs.

Customers begin interacting with the advertisements.

The Website SDK captures behavioral events including page views, product interactions, scrolling behavior, checkout progression, and purchases.

Behavioral data continuously updates the Customer Graph.

Conversion Intelligence detects increased abandonment during the payment step and recommends simplifying the checkout flow.

The Product Manager approves the recommendation.

The updated checkout experience increases conversion rates.

Customers completing purchases automatically receive loyalty rewards.

The browser extension recognizes returning Domino's customers and surfaces available rewards during future checkouts.

Customer Intelligence predicts users with high churn probability and recommends personalized offers.

The Automation Engine sends discount offers only after manager approval.

At the end of the week, the CEO asks:

> "How did the weekend campaign perform?"

The AI generates an executive summary explaining campaign performance, customer acquisition costs, conversion improvements, loyalty engagement, projected lifetime value, and recommended next steps, complete with confidence scores and supporting evidence.

---

# Definition of Done

The GrowthOS MVP is considered complete when the following conditions are satisfied.

## Product

* All twelve epics implemented.  
* Progressive Abstraction operational.  
* Manual, Approval, and Autonomous modes supported.  
* AI recommendations explainable.  
* Confidence scores displayed.

---

## Engineering

* APIs documented.  
* SDKs operational.  
* Integrations validated.  
* Unit tests passing.  
* Integration tests passing.  
* Performance benchmarks achieved.

---

## Quality Assurance

* Critical workflows validated.  
* Regression suite passing.  
* Cross-browser compatibility verified.  
* Error handling tested.  
* Edge cases validated.

---

## Security

* RBAC enforced.  
* Encryption enabled.  
* Audit logging operational.  
* Compliance workflows validated.  
* Penetration testing completed.

---

## Operations

* Monitoring dashboards operational.  
* Alerting configured.  
* Backup strategy verified.  
* Disaster recovery tested.  
* Deployment pipeline automated.

---

## AI Quality

* Recommendations include explanations.  
* Confidence scores generated.  
* Recommendation history maintained.  
* Approval workflows validated.  
* Autonomous execution restricted by organizational policies.

---

## Business Readiness

* User documentation completed.  
* Administrator documentation completed.  
* API documentation published.  
* SDK documentation published.  
* Onboarding flow validated.  
* Sample workspace available.

---

## MVP Success Criteria

The MVP is considered successful when organizations can:

* Launch advertising campaigns using natural language.  
* Track customer behavior through the Website SDK.  
* Build unified customer profiles.  
* Configure loyalty programs.  
* Receive explainable AI recommendations.  
* Automate approved growth workflows.  
* Monitor business performance through progressive abstraction.  
* Improve measurable business outcomes using a single AI-native Growth Operating System.

---

# **GrowthOS — Module Architecture & Interaction Overview**

---

# **1\. Purpose**

This document defines the four primary modules of GrowthOS and explains how they interact to form a unified AI-native Growth Operating System.

The four modules are:

1. **Loyalty & Rewards Platform**  
2. **Behavior Intelligence SDK**  
3. **Ads Layer Manager**  
4. **AI Growth Brain & Customer Intelligence**

The modules are independently responsible for specific business capabilities but operate as a unified system through shared APIs, events, customer data, and the AI Growth Brain.

---

# **2\. System-Level Concept**

GrowthOS is structured around a simple business lifecycle:

**Acquire → Understand → Convert → Retain → Learn → Optimize**

The four modules support this lifecycle:

| Module | Primary Responsibility | Growth Lifecycle |
| ----- | ----- | ----- |
| Ads Layer Manager | Acquire customers | Acquisition |
| Behavior Intelligence SDK | Understand customer behavior and conversion | Conversion |
| Loyalty & Rewards | Retain customers | Retention |
| AI Growth Brain | Understand, predict, reason, and orchestrate | Intelligence |

The AI Growth Brain sits at the highest logical level and connects the other three modules.

---

# **3\. Module Hierarchy**

                    ![][image1]  
         

The hierarchy is **logical rather than strictly technical**.

The three operational modules can function independently, but the AI Growth Brain provides the intelligence and orchestration layer that connects them.

---

# **4\. Module 1 — Loyalty & Rewards Platform**

## **Purpose**

The Loyalty & Rewards module provides GrowthOS with its customer-retention infrastructure.

It enables businesses to create loyalty programs and customers to earn, manage, and redeem rewards.

## **Core Capabilities**

* Loyalty programs  
* Points  
* Rewards  
* Membership tiers  
* Referrals  
* Personalized offers  
* Unified loyalty wallet  
* Browser extension  
* Checkout widget  
* Loyalty analytics

## **Primary Inputs**

* Purchases  
* Customer identity  
* Customer segments  
* Behavioral signals  
* AI recommendations

## **Primary Outputs**

* Loyalty events  
* Reward transactions  
* Customer loyalty status  
* Redemption events  
* Retention signals

## **Example**

Domino's configures:

> "Give customers 10 points for every ₹100 spent and double points on weekends."

The Loyalty module evaluates purchases, awards points, and publishes the resulting loyalty events.

---

# **5\. Module 2 — Behavior Intelligence SDK**

## **Purpose**

The Behavior Intelligence SDK is the behavioral data collection and conversion intelligence layer.

It allows businesses to understand what users do on their websites and applications.

## **Core Capabilities**

* Event tracking  
* Session tracking  
* Funnel analysis  
* Heatmaps  
* Product interaction tracking  
* Checkout analysis  
* Behavioral signals  
* Conversion analysis  
* UX friction detection

## **Primary Inputs**

* Website interactions  
* Application interactions  
* Campaign attribution  
* Customer identifiers  
* Commerce events

## **Primary Outputs**

* Behavioral events  
* Sessions  
* Funnels  
* Intent signals  
* Conversion signals  
* UX insights

## **Example**

Domino's users repeatedly reach checkout but abandon after seeing delivery charges.

The SDK captures the behavior and produces:

> `checkout_abandonment_signal`

The AI Growth Brain can then determine whether the problem should be addressed through UX changes, advertising adjustments, or loyalty incentives.

---

# **6\. Module 3 — Ads Layer Manager**

## **Purpose**

The Ads Layer Manager provides the acquisition infrastructure for GrowthOS.

It allows businesses to create and manage advertising campaigns using natural-language business objectives.

## **Core Capabilities**

* Google Ads  
* Meta Ads  
* Campaign creation  
* Keyword research  
* Audience discovery  
* Budget optimization  
* Bid optimization  
* Campaign deployment  
* Campaign monitoring  
* Cross-platform optimization

## **Primary Inputs**

* Business goals  
* Customer segments  
* Behavioral signals  
* Historical campaign performance  
* Product information  
* Customer LTV

## **Primary Outputs**

* Campaigns  
* Ad groups/ad sets  
* Audiences  
* Keywords  
* Campaign metrics  
* Optimization events

## **Example**

Domino's enters:

> "Increase weekend orders from college students in Mumbai."

The Ads Layer Manager generates campaign strategies for Google and Meta, proposes budgets and audiences, and deploys the campaigns after approval.

---

# **7\. Module 4 — AI Growth Brain & Customer Intelligence**

## **Purpose**

The AI Growth Brain is the central intelligence and orchestration layer.

It does not replace the other modules. Instead, it interprets their data and coordinates actions between them.

## **Core Capabilities**

* Natural-language business queries  
* Customer profiles  
* Customer Graph  
* Segmentation  
* LTV prediction  
* Churn prediction  
* Purchase propensity  
* Business reasoning  
* Recommendations  
* Forecasting  
* Automation  
* Cross-module orchestration

## **Primary Inputs**

The AI Growth Brain consumes data from all three operational modules.

Ads  
 ↓  
Campaign Performance

SDK  
 ↓  
Behavioral Intelligence

Loyalty  
 ↓  
Retention Intelligence

It combines these with customer and business data to produce decisions.

## **Primary Outputs**

* Insights  
* Predictions  
* Recommendations  
* Segments  
* Automation plans  
* Cross-module actions  
* Business explanations

---

# **8\. How the Modules Interact**

The modules communicate through two primary mechanisms:

### **APIs**

Used for synchronous operations such as:

* Retrieve customer profile  
* Get loyalty balance  
* Create campaign  
* Query analytics  
* Approve recommendation

### **Events**

Used for asynchronous communication such as:

* Purchase completed  
* Checkout abandoned  
* Reward redeemed  
* Campaign performance changed  
* Customer churn detected

This prevents modules from becoming tightly coupled.

---

# **9\. Core Data Flow**

                CUSTOMER  
                    │  
                    ▼  
             Behavior SDK  
                    │  
                    ▼  
            Behavioral Events  
                    │  
                    ▼  
             Customer Graph  
                    │  
          ┌─────────┴─────────┐  
          ▼                   ▼  
     AI Growth Brain       Analytics  
          │  
    ┌─────┴──────┐  
    ▼            ▼  
   Ads         Loyalty  
    │            │  
    ▼            ▼  
Acquisition   Retention  
    │            │  
    └─────┬──────┘  
          ▼  
       Customer  
          │  
          ▼  
       New Data  
          │  
          └──────→ AI Growth Brain

This creates a continuous optimization loop.

---

# **10\. Cross-Module Example — Domino's**

Consider a Domino's customer.

### **Step 1 — Acquisition**

The customer clicks a Meta advertisement.

**Ads Layer Manager**

Records:

Campaign: Weekend Pizza  
Source: Meta  
Audience: College Students

---

### **Step 2 — Behavior**

The customer visits Domino's website.

**Behavior SDK**

Records:

Product Viewed  
Cart Created  
Checkout Started

The customer abandons checkout.

---

### **Step 3 — Intelligence**

**AI Growth Brain**

Combines:

* Campaign data  
* Customer behavior  
* Historical conversion data

It determines:

> "The campaign generates high-quality traffic, but mobile checkout abandonment is unusually high."

Confidence:

**91%**

---

### **Step 4 — Retention**

The customer is identified as a high-value returning customer.

**Loyalty Module**

makes a ₹200 reward available.

---

### **Step 5 — Re-engagement**

The Ads Layer Manager receives a high-intent customer segment from the AI Growth Brain.

It can use that segment for an appropriate remarketing strategy where supported.

---

### **Step 6 — Learning**

The customer eventually purchases.

The system records:

Advertisement  
      ↓  
Website Session  
      ↓  
Checkout  
      ↓  
Loyalty Reward  
      ↓  
Purchase

The AI Growth Brain uses the outcome to improve future recommendations.

---

# **11\. Information Hierarchy**

GrowthOS should maintain a clear hierarchy of responsibility.

               Business Goal  
                     │  
                     ▼  
              AI Growth Brain  
                     │  
              Decision / Plan  
                     │  
       ┌─────────────┼─────────────┐  
       ▼             ▼             ▼  
      Ads           SDK         Loyalty  
       │             │             │  
 Acquisition      Behavior      Retention  
       │             │             │  
       └─────────────┼─────────────┘  
                     ▼  
                 New Data  
                     │  
                     ▼  
              AI Growth Brain

The AI Growth Brain **decides and orchestrates**.

The other three modules **execute specialized responsibilities and generate data**.

---

# **12\. Shared Customer Intelligence Layer**

Although Customer Intelligence belongs to Module 4, it acts as the shared intelligence context for the entire platform.

For example:

Customer Profile

├── Acquisition Source  
├── Campaign History  
├── Website Behavior  
├── Purchase History  
├── Product Affinity  
├── Loyalty Status  
├── LTV  
├── Churn Probability  
└── Purchase Intent

Each operational module can consume the relevant customer signals without owning the entire customer profile.

---

# **13\. Operating Modes Across Modules**

All modules support the GrowthOS operating model.

### **Manual**

The system provides information and recommendations.

### **Approval**

The system proposes an action and waits for approval.

### **Autonomous**

The system executes the action when it satisfies configured policies.

Example:

AI Recommendation  
       ↓  
Policy Check  
       ↓  
Confidence Check  
       ↓  
Permission Check  
       ↓  
Execute

The AI Growth Brain must never bypass module-level permissions or business policies.

---

# **14\. Communication Principles**

The four modules must follow these architectural principles:

1. **No direct database access between modules.**  
2. **Use APIs for synchronous operations.**  
3. **Use events for asynchronous communication.**  
4. **Customer identity is resolved centrally.**  
5. **AI reasoning happens centrally in the Growth Brain.**  
6. **Execution remains within the responsible module.**  
7. **All important actions are auditable.**  
8. **Every AI recommendation includes evidence and confidence.**

---

# **15\. Final Architecture Summary**

GrowthOS can be understood as four layers of responsibility:![][image2]

  

The fundamental GrowthOS loop is:

**Acquire → Observe → Understand → Convert → Retain → Learn → Optimize → Acquire Again**

This loop is what differentiates GrowthOS from a collection of independent marketing tools. The four modules are specialized, but the AI Growth Brain makes them operate as one integrated growth system.

---

# **16\. Architectural Principle**

> **The three operational modules generate and execute growth activity. The AI Growth Brain converts the resulting data into intelligence, decisions, and coordinated actions.**

This principle should remain stable as GrowthOS expands to additional advertising platforms, mobile applications, loyalty mechanisms, data sources, and autonomous growth capabilities.

# **GrowthOS — Module 1: Loyalty & Rewards Platform**

---

# **Current work update:**

# **1\. Module Definition**

The **Loyalty & Rewards Platform** is the customer-retention layer of GrowthOS.

It enables businesses to create, manage, and automate loyalty programs while providing customers with a unified loyalty experience across participating businesses.

Businesses can define loyalty rules such as:

* Earn points for purchases  
* Redeem points for rewards  
* Referral rewards  
* Cashback  
* Membership tiers  
* Promotional bonuses  
* Birthday rewards  
* Product-specific rewards  
* First-purchase rewards  
* Repeat-purchase incentives

Customers interact with these programs through the **GrowthOS customer experience**, primarily through a browser extension and checkout-integrated widget.

The module connects directly with the **Customer Intelligence module**, allowing loyalty actions to be personalized based on customer behavior, purchase history, predicted lifetime value, and engagement.

### **Core Principle**

The module should make loyalty program creation as simple as:

> "Give customers 10 points for every ₹100 spent, give 500 bonus points on their birthday, and give double points on weekends."

GrowthOS converts this into executable loyalty rules.

---

# **2\. Problem Statement**

Businesses currently use separate loyalty systems, coupon platforms, referral systems, and customer engagement tools.

This creates:

* Fragmented customer experiences  
* Difficult loyalty configuration  
* Limited personalization  
* Poor visibility into reward effectiveness  
* Manual reward management  
* Loyalty programs that operate independently from marketing and customer intelligence

GrowthOS should provide a centralized loyalty infrastructure that connects rewards with advertising, customer behavior, purchases, and customer intelligence.

---

# **3\. Scope**

## **3.1 Included in MVP**

### **Business-side functionality**

* Loyalty program creation  
* Point-based rewards  
* Reward configuration  
* Reward redemption  
* Membership tiers  
* Referral rewards  
* Promotional campaigns  
* Customer loyalty profiles  
* Reward expiration  
* Loyalty analytics  
* Fraud prevention  
* Program configuration  
* Rule-based reward issuance

### **Customer-side functionality**

* Unified loyalty wallet  
* View points  
* View available rewards  
* View transaction history  
* Redeem rewards  
* View membership tier  
* View participating businesses  
* Checkout reward widget  
* Browser extension

### **AI functionality**

* Natural-language loyalty configuration  
* Personalized reward recommendations  
* Customer reward recommendations  
* Loyalty performance analysis  
* Churn-based reward recommendations

---

# **4\. Out of Scope for MVP**

The following are intentionally excluded from the initial implementation:

* Cryptocurrency rewards  
* Blockchain-based loyalty tokens  
* Native loyalty payment cards  
* Physical loyalty cards  
* Full CRM functionality  
* Native email marketing  
* Native SMS infrastructure  
* Complex enterprise partner marketplaces  
* Advanced gamification  
* Native mobile loyalty application

These may be introduced in later versions.

---

# **5\. Core Responsibilities**

The Loyalty & Rewards module owns:

* Loyalty programs  
* Reward rules  
* Points ledger  
* Reward issuance  
* Reward redemption  
* Referral tracking  
* Membership tiers  
* Loyalty wallet  
* Loyalty transactions  
* Checkout loyalty experience  
* Loyalty analytics

The module does **not** own:

* Customer identity resolution  
* Advertising campaigns  
* Website behavioral tracking  
* Customer churn prediction

Those responsibilities belong to other GrowthOS modules.

---

# **6\. Technology Stack**

| Layer | Technology |
| ----- | ----- |
| Backend Language | Python |
| Backend Framework | FastAPI |
| Frontend | Next.js \+ TypeScript |
| Browser Extension | TypeScript \+ React |
| Primary Database | PostgreSQL |
| Cache | Redis |
| Event Streaming | Kafka |
| Object Storage | S3-compatible storage |
| Authentication | OAuth 2.0 / JWT |
| APIs | REST \+ Webhooks |
| Payments | Stripe integration |
| Infrastructure | Docker \+ Kubernetes |
| Monitoring | Prometheus \+ Grafana |
| Observability | OpenTelemetry |
| AI Integration | GrowthOS AI Growth Brain |

PostgreSQL is the source of truth for loyalty balances, reward transactions, program configuration, and redemption records.

Kafka is used for asynchronous loyalty events and integration with other GrowthOS modules.

Redis is used for low-latency reads such as loyalty balance and reward availability.

---

# **7\. High-Level Architecture**

                   Business Admin  
                         │  
                         ▼  
                  GrowthOS Dashboard  
                         │  
                         ▼  
                Loyalty API / Service  
                         │  
             ┌───────────┼───────────┐  
             ▼           ▼           ▼  
        Rule Engine   PostgreSQL    Redis  
             │  
             ▼  
           Kafka  
             │  
      ┌──────┼─────────────┐  
      ▼      ▼             ▼  
 Customer   AI Brain    Analytics  
  Graph  
      │  
      ▼  
Customer Experience  
      │  
 ┌────┴─────────┐  
 ▼              ▼  
Browser       Checkout  
Extension      Widget

---

# **8\. Core Entities**

The module should maintain the following primary entities.

### **Loyalty Program**

Defines the loyalty program belonging to a business.

Key fields:

* program\_id  
* organization\_id  
* name  
* status  
* currency  
* points\_expiry\_policy  
* created\_at  
* updated\_at

### **Loyalty Rule**

Defines how customers earn or receive rewards.

Examples:

* ₹100 spent → 10 points  
* Referral completed → 500 points  
* Birthday → 1,000 points

### **Customer Wallet**

Stores the customer's loyalty balance for a business.

Key fields:

* wallet\_id  
* customer\_id  
* organization\_id  
* available\_points  
* lifetime\_points  
* tier  
* created\_at

### **Reward**

Defines a redeemable benefit.

Examples:

* ₹100 discount  
* Free delivery  
* Free pizza  
* 20% discount

### **Loyalty Transaction**

Immutable record of every points movement.

Transaction types:

* EARN  
* REDEEM  
* EXPIRE  
* ADJUST  
* REFUND  
* BONUS

### **Referral**

Tracks customer referral activity and reward eligibility.

---

# **9\. Loyalty Rule Engine**

The Rule Engine is responsible for evaluating loyalty conditions.

Example:

> Customer spends ₹500.

Rule:

₹100 \= 10 points

500 / 100 × 10

\= 50 points

The engine generates a loyalty transaction.

Rules must support:

* Conditions  
* Triggers  
* Actions  
* Eligibility  
* Expiration  
* Maximum limits

Example:

WHEN purchase\_completed  
IF order\_value \>= ₹500  
THEN award 100 points

Rules must be deterministic and auditable.

---

# **10\. Natural Language Loyalty Configuration**

Business users should not need to understand rule engines.

Example:

> "Give users 20 points for every ₹100 spent and double the points on Sundays."

GrowthOS converts this into a structured rule configuration.

The AI must display the interpreted rule before activation.

Example:

Base Reward:  
20 points / ₹100

Sunday Multiplier:  
2×

Activation:  
After successful purchase

Status:  
Awaiting Approval

The business user must approve the generated configuration before activation.

---

# **11\. Unified Loyalty Wallet**

The customer wallet provides a centralized view of loyalty programs.

Example:

| Business | Points | Tier | Available Rewards |
| ----- | ----- | ----- | ----- |
| Domino's | 1,240 | Gold | ₹200 Off |
| Nike | 840 | Silver | 15% Off |
| Starbucks | 2,100 | Gold | Free Beverage |

The wallet must maintain separate balances for each business.

Points from one business must never be transferable to another unless an explicit cross-business program is introduced.

---

# **12\. Browser Extension**

The GrowthOS browser extension provides the customer-facing loyalty experience.

When a customer visits a supported merchant website, the extension detects the merchant and displays the customer's available loyalty benefits.

At checkout, the extension can display:

* Current points  
* Available rewards  
* Eligible coupons  
* Membership tier  
* Personalized offers

Example:

Domino's Checkout

You have:

1,240 points

Available reward:  
₹200 OFF

\[Apply Reward\]

The extension must not automatically apply a reward without customer consent unless the customer has explicitly enabled automatic redemption.

---

# **13\. Checkout Widget**

Businesses may optionally embed a GrowthOS loyalty widget directly into checkout.

The widget communicates with the Loyalty API and displays the customer's loyalty state.

Required capabilities:

* Authentication  
* Wallet retrieval  
* Reward retrieval  
* Reward application  
* Redemption confirmation  
* Error handling

The widget should be lightweight and asynchronously loaded so that GrowthOS does not block checkout rendering.

---

# **14\. Loyalty and Customer Intelligence Integration**

The Loyalty module consumes customer intelligence signals.

Example:

Customer:

High LTV  
Low engagement  
High churn probability

AI recommendation:

> "Offer this customer a 20% discount because their churn probability is 78% and their historical LTV is ₹8,400."

The Loyalty module receives the recommendation and, depending on operating mode, either:

* displays it to the business,  
* requests approval, or  
* executes it automatically.

---

# **15\. Fraud Prevention**

The module must detect suspicious loyalty activity.

Examples:

* Repeated referral abuse  
* Multiple accounts using the same referral  
* Excessive reward redemption  
* Repeated transaction replay  
* Abnormally rapid point accumulation  
* Refund-based reward exploitation

Suspicious transactions should be flagged rather than silently deleted.

Businesses should be able to review and reverse fraudulent rewards.

---

# **16\. Refund and Cancellation Logic**

Loyalty transactions must remain financially consistent with purchases.

Example:

Customer receives:

100 points

for a ₹1,000 purchase.

The customer later receives a full refund.

GrowthOS must create a compensating transaction:

\-100 points

The original transaction must remain immutable.

This provides a complete audit trail.

---

# **17\. APIs**

Initial API surface:

POST   /loyalty/programs  
GET    /loyalty/programs/{id}

POST   /loyalty/rules  
GET    /loyalty/rules

GET    /customers/{id}/wallet  
GET    /customers/{id}/rewards

POST   /loyalty/rewards/redeem

GET    /loyalty/transactions

POST   /loyalty/referrals

POST   /loyalty/events

All APIs must be versioned.

Example:

/api/v1/loyalty/...

---

# **18\. Events**

The module publishes events to the GrowthOS event pipeline.

Examples:

loyalty.program.created  
loyalty.points.earned  
loyalty.points.redeemed  
loyalty.points.expired  
loyalty.reward.issued  
loyalty.reward.redeemed  
loyalty.referral.completed  
loyalty.tier.changed

These events are consumed by Customer Intelligence, Analytics, and the AI Growth Brain.

---

# **19\. Security & Privacy**

The module must enforce:

* Workspace isolation  
* RBAC  
* OAuth authentication  
* TLS encryption  
* Encryption at rest  
* API rate limiting  
* Audit logging  
* Consent management  
* Customer data deletion  
* Reward transaction immutability

Sensitive payment information must not be stored by the Loyalty module.

Payment data remains with the payment provider.

---

# **20\. Scalability**

The Loyalty module must support high-volume transactional workloads.

The architecture should allow horizontal scaling of:

* API servers  
* Rule evaluation workers  
* Event consumers  
* Notification workers

Redis should be used for frequently accessed wallet information while PostgreSQL remains the source of truth.

Kafka decouples loyalty events from downstream processing.

The system must support idempotency to prevent duplicate rewards when the same purchase event is delivered multiple times.

---

# **21\. Example Use Cases**

## **Use Case 1 — Domino's Purchase**

Customer purchases ₹800 worth of food.

Rule:

10 points per ₹100

GrowthOS awards:

80 points

---

## **Use Case 2 — Referral**

A Domino's customer refers a friend.

Friend completes their first order.

GrowthOS:

1. Validates referral.  
2. Confirms qualifying purchase.  
3. Awards referral reward.  
4. Records transaction.  
5. Updates customer profile.

---

## **Use Case 3 — Personalized Retention**

AI identifies a high-value customer with increasing churn probability.

GrowthOS recommends:

> "Offer free delivery on the customer's next order."

The business approves the recommendation.

The reward becomes available at checkout.

---

## **Use Case 4 — Browser Extension**

A customer visits Domino's checkout.

GrowthOS detects:

1,240 points  
₹200 reward available

The extension displays the reward and allows the customer to apply it.

---

## **Use Case 5 — Weekend Promotion**

Domino's configures:

> "Double loyalty points every Saturday and Sunday."

The Rule Engine automatically applies the multiplier to qualifying purchases.

---

# **22\. Dependencies**

The Loyalty module depends on:

### **Internal**

* Customer Graph  
* AI Growth Brain  
* Behavior Intelligence SDK  
* Authentication  
* Event Pipeline  
* Analytics

### **External**

* Payment providers  
* Merchant commerce platforms  
* Browser APIs

The Loyalty module must communicate with other GrowthOS modules through stable APIs and events rather than direct database access.

---

# **23\. MVP Definition of Done**

The Loyalty & Rewards module is considered MVP-complete when:

* Businesses can create loyalty programs.  
* Businesses can configure point rules.  
* Customers can earn points.  
* Customers can redeem rewards.  
* Loyalty transactions are immutable and auditable.  
* Refunds correctly reverse earned points.  
* Browser extension displays loyalty information.  
* Checkout widget supports reward redemption.  
* Referral rewards work.  
* Customer profiles receive loyalty events.  
* AI can recommend loyalty actions.  
* RBAC and tenant isolation are enforced.  
* APIs and webhooks are documented.  
* Automated tests cover critical loyalty flows.  
* Monitoring and audit logging are operational.

---

# **24\. Module Success Metrics**

| Metric | MVP Target |
| ----- | ----- |
| Reward Calculation Accuracy | \>99.9% |
| Duplicate Reward Rate | \<0.01% |
| Redemption Success Rate | \>99% |
| Checkout Widget Availability | \>99.9% |
| Loyalty Event Processing | \<2 seconds |
| Fraud Detection Precision | \>90% |
| Customer Reward Adoption | \>20% |
| Repeat Purchase Lift | \>10% |

---

# **25\. Module Summary**

The Loyalty & Rewards Platform provides the **retention infrastructure of GrowthOS**.

It enables businesses to create loyalty programs using simple natural language, manages the underlying rules and transactions, provides customers with a unified loyalty wallet, integrates directly into checkout, and uses Customer Intelligence to personalize rewards.

The module is intentionally designed as an independent service with well-defined APIs and events so that it can operate independently while continuously exchanging intelligence with the other three GrowthOS modules.

**Core principle:**

> **Businesses define the outcome. GrowthOS manages the loyalty mechanics.**

# **GrowthOS — Module 2: Behavior Intelligence SDK**

---

# **1\. Module Definition**

The **Behavior Intelligence SDK** is the behavioral data collection and conversion intelligence layer of GrowthOS.

It enables businesses to understand how users interact with their websites and applications by collecting structured behavioral events and transforming them into meaningful customer and business signals.

The SDK captures events such as:

* Page views  
* Clicks  
* Scrolls  
* Product views  
* Search interactions  
* Cart activity  
* Checkout progression  
* Form interactions  
* Session duration  
* Navigation  
* Exit intent  
* Rage clicks  
* Dead clicks  
* Device and browser information

The module is not intended to simply reproduce traditional analytics tools. Its primary purpose is to convert large volumes of behavioral events into **actionable semantic intelligence**.

Example:

Instead of reporting:

> "42% of users abandoned checkout."

GrowthOS should be able to determine:

> "Checkout abandonment increased primarily on mobile users after the delivery-fee step. 68% of affected users viewed the delivery information immediately before leaving."

---

# **2\. Problem Statement**

Businesses generate enormous amounts of behavioral data but typically rely on fragmented analytics systems that provide isolated metrics.

Common problems include:

* Lack of unified behavioral data  
* Excessive raw event volume  
* Difficult session analysis  
* Limited understanding of user intent  
* Manual funnel investigation  
* Poor connection between advertising and website behavior  
* Difficulty identifying conversion friction  
* No unified connection between behavior and customer value

GrowthOS should transform raw interaction data into a continuously updated behavioral intelligence layer that can be consumed by the AI Growth Brain and Customer Graph.

---

# **3\. Scope**

## **3.1 Included in MVP**

### **Data Collection**

* Page views  
* Clicks  
* Scroll events  
* Form interactions  
* Product views  
* Search events  
* Cart events  
* Checkout events  
* Purchase events  
* Session lifecycle  
* Device information  
* Browser information  
* UTM attribution

### **Behavioral Intelligence**

* Sessionization  
* Funnel analysis  
* Heatmaps  
* Conversion analysis  
* Engagement scoring  
* Rage-click detection  
* Dead-click detection  
* Exit-intent detection  
* Product engagement  
* Checkout abandonment

### **Developer Features**

* JavaScript SDK  
* Event API  
* SDK configuration  
* Debug mode  
* Event validation  
* SDK health monitoring

### **AI Features**

* Conversion recommendations  
* Behavioral anomaly detection  
* User intent inference  
* UX friction detection  
* Funnel explanations  
* Semantic session summaries

---

# **4\. Out of Scope for MVP**

The following are excluded from the initial release:

* Full session video recording  
* Keystroke recording  
* Screen recording  
* Native mobile SDK  
* Call tracking  
* Email tracking  
* Server infrastructure monitoring  
* Full product analytics replacement  
* Automatic website code modification  
* Automatic A/B testing deployment

Mobile SDK support can be introduced in a subsequent release.

---

# **5\. Core Responsibilities**

The Behavior Intelligence SDK owns:

* Behavioral event collection  
* Event validation  
* Session tracking  
* Client-side event buffering  
* Event ingestion  
* Behavioral aggregation  
* Funnel computation  
* Heatmap generation  
* Conversion signals  
* SDK diagnostics

It does **not** own:

* Customer identity as the system of record  
* Advertising campaigns  
* Loyalty balances  
* Customer LTV models

Those capabilities belong to other GrowthOS modules.

---

# **6\. Technology Stack**

| Layer | Technology |
| ----- | ----- |
| SDK Language | TypeScript |
| SDK Build | Rollup / ESBuild |
| Backend Language | Python |
| Backend Framework | FastAPI |
| Event Streaming | Apache Kafka |
| Stream Processing | Kafka Streams / Python consumers |
| Hot Storage | Redis |
| Operational Database | PostgreSQL |
| Event Storage | S3-compatible Object Storage |
| Analytics Store | ClickHouse |
| Customer Graph | Neo4j |
| APIs | REST \+ Webhooks |
| Authentication | API Keys / OAuth |
| Infrastructure | Docker \+ Kubernetes |
| Monitoring | Prometheus \+ Grafana |
| Observability | OpenTelemetry |

### **Important architectural decision**

**Raw behavioral events must not be stored indefinitely in PostgreSQL.**

The expected volume of SDK events can reach millions or billions of events.

The event architecture therefore uses:

SDK  
 ↓  
Ingestion API  
 ↓  
Kafka  
 ↓  
Stream Processing  
 ↓  
 ┌──────────────┬───────────────┐  
 ↓              ↓               ↓  
S3          ClickHouse       Derived Events  
Raw Data    Analytics        Customer Signals

PostgreSQL stores configuration and operational metadata rather than the full raw event stream.

---

# **7\. High-Level Architecture**

                    Customer Website  
                            │  
                            ▼  
                    GrowthOS SDK  
                            │  
                   Local Event Buffer  
                            │  
                            ▼  
                    Event Ingestion API  
                            │  
                            ▼  
                          Kafka  
                            │  
             ┌──────────────┼──────────────┐  
             ▼              ▼              ▼  
         S3 Data Lake   ClickHouse    Stream Processor  
             │              │              │  
             │              │              ▼  
             │              │        Derived Signals  
             │              │              │  
             └──────────────┼──────────────┘  
                            ▼  
                     Customer Graph  
                            │  
                            ▼  
                     AI Growth Brain

---

# **8\. SDK Design**

Businesses install the SDK using a lightweight JavaScript snippet.

Example:

\<script\>  
  GrowthOS.init({  
    projectId: "merchant\_project\_id"  
  });  
\</script\>

The SDK automatically begins collecting supported events after initialization and consent requirements are satisfied.

The SDK must be asynchronous and must never block:

* Page rendering  
* Checkout  
* Navigation  
* User interactions

---

# **9\. Event Taxonomy**

GrowthOS should maintain a canonical event taxonomy.

### **Core Events**

page.viewed  
session.started  
session.ended  
element.clicked  
element.hovered  
scroll.depth\_reached  
form.started  
form.completed  
product.viewed  
product.searched  
cart.item\_added  
cart.item\_removed  
checkout.started  
checkout.step\_completed  
checkout.abandoned  
purchase.completed

### **Behavioral Signals**

user.rage\_click  
user.dead\_click  
user.exit\_intent  
user.high\_intent  
user.low\_engagement  
user.repeated\_navigation

Events must use a standardized schema.

Example:

{  
  event\_id  
  event\_name  
  timestamp  
  anonymous\_id  
  customer\_id  
  session\_id  
  page\_url  
  device  
  browser  
  properties  
}

---

# **10\. Client-Side Event Processing**

Events should not be transmitted individually whenever possible.

The SDK should:

1. Capture event.  
2. Validate event.  
3. Add timestamp and identifiers.  
4. Add session context.  
5. Store temporarily in memory/local buffer.  
6. Batch events.  
7. Send asynchronously.

Example:

20 events  
      ↓  
Batch  
      ↓  
Compressed payload  
      ↓  
Ingestion API

Batching reduces network overhead and improves performance.

---

# **11\. Offline and Network Failure Handling**

If the user's network temporarily fails, events should be stored locally within configured limits.

When connectivity returns:

Local Buffer  
     ↓  
Retry  
     ↓  
Server

Events must contain unique IDs so retries do not create duplicate records.

The SDK should discard buffered events after the configured maximum storage period.

---

# **12\. Session Intelligence**

GrowthOS creates sessions using configurable inactivity thresholds.

Default:

**30 minutes of inactivity \= new session.**

A session contains:

* Entry page  
* Exit page  
* Duration  
* Pages visited  
* Events  
* Products viewed  
* Cart activity  
* Checkout activity  
* Conversion status

The system should distinguish between:

* Anonymous sessions  
* Authenticated sessions  
* Returning users

When an anonymous visitor logs in, historical anonymous activity may be linked to the authenticated customer according to identity-resolution rules.

---

# **13\. Behavioral Analytics**

The module transforms raw events into behavioral metrics.

Examples:

### **Engagement**

* Session duration  
* Pages/session  
* Scroll depth  
* Interaction rate

### **Product**

* Product views  
* Product dwell time  
* Repeat views  
* Add-to-cart rate

### **Checkout**

* Checkout start rate  
* Step completion  
* Abandonment rate  
* Payment failure rate

### **UX**

* Rage clicks  
* Dead clicks  
* Navigation loops  
* Failed interactions

---

# **14\. Heatmaps**

The system should generate aggregated interaction maps.

Supported MVP heatmaps:

* Click heatmap  
* Scroll heatmap  
* Interaction density

Heatmaps should be aggregated rather than exposing raw individual user behavior by default.

Businesses can filter heatmaps by:

* Device  
* Geography  
* Date  
* Campaign  
* Customer segment  
* Page

---

# **15\. Funnel Intelligence**

Businesses can define funnels such as:

Landing Page  
     ↓  
Product View  
     ↓  
Add to Cart  
     ↓  
Checkout  
     ↓  
Purchase

GrowthOS calculates:

* Conversion rate  
* Drop-off rate  
* Step-to-step conversion  
* Time between steps  
* Segment differences

The AI can explain significant changes.

Example:

> "Mobile checkout conversion decreased 11% because abandonment increased after the delivery-fee step."

---

# **16\. AI Conversion Intelligence**

The AI Growth Brain consumes processed behavioral data rather than directly querying billions of raw events for every request.

Example:

Raw Events  
   ↓  
Aggregation  
   ↓  
Behavioral Signals  
   ↓  
AI Context  
   ↓  
Recommendation

Example recommendation:

> "Reduce checkout abandonment by moving delivery charges earlier in the ordering flow."

Every recommendation must include:

* Evidence  
* Confidence score  
* Affected segment  
* Expected impact  
* Recommended action

---

# **17\. Data Reduction Strategy**

Because behavioral data can become extremely large, GrowthOS uses multiple data tiers.

| Data | Storage | Retention |
| ----- | ----- | ----- |
| Raw interaction events | S3 | 7–30 days |
| Standard behavioral events | S3 / ClickHouse | 30–90 days |
| Aggregated metrics | ClickHouse | 12–24 months |
| Customer signals | PostgreSQL / Neo4j | Long-term |
| AI insights | PostgreSQL | Long-term |

Retention should be configurable by organization.

Raw events should be compressed and partitioned by:

* Organization  
* Date  
* Event type

---

# **18\. Privacy & Consent**

The SDK must support consent-aware tracking.

The merchant should be able to configure:

* Required consent  
* Anonymous tracking  
* Analytics-only tracking  
* Marketing tracking  
* Data retention

The SDK must provide mechanisms for:

* Data deletion  
* Customer opt-out  
* Consent state propagation  
* Identifier reset

Sensitive information such as passwords, payment details, and authentication tokens must never be captured.

Input fields containing sensitive data must be excluded from tracking.

---

# **19\. Performance Requirements**

The SDK must have minimal impact on the host website.

Target requirements:

| Metric | Target |
| ----- | ----- |
| Initial SDK impact | \<50 KB gzipped |
| Event capture overhead | \<5 ms |
| Main-thread blocking | Near zero |
| Event delivery | \<2 seconds when online |
| API availability | \>99.9% |
| Duplicate event rate | \<0.01% |

The SDK must fail silently if GrowthOS services become unavailable.

A GrowthOS outage must never break the customer's website.

---

# **20\. APIs**

Initial API surface:

POST /api/v1/events  
POST /api/v1/events/batch

GET  /api/v1/sessions/{id}  
GET  /api/v1/funnels/{id}  
GET  /api/v1/heatmaps/{id}

POST /api/v1/funnels  
GET  /api/v1/behavior/insights

GET  /api/v1/sdk/projects  
POST /api/v1/sdk/projects

The event ingestion APIs must support:

* Batching  
* Compression  
* Idempotency  
* Rate limiting  
* Schema validation

---

# **21\. Events Published to Other Modules**

The module publishes derived events and signals such as:

behavior.session.started  
behavior.session.completed  
behavior.product.interest\_detected  
behavior.checkout.started  
behavior.checkout.abandoned  
behavior.purchase.completed  
behavior.high\_intent.detected  
behavior.churn\_signal.detected  
behavior.conversion\_anomaly.detected

These events are consumed by:

* Customer Intelligence  
* Ads Layer Manager  
* Loyalty & Rewards  
* AI Growth Brain

---

# **22\. Example Use Cases**

## **Use Case 1 — Domino's Product Interest**

A user views the same pizza four times during two sessions.

GrowthOS detects repeated product interest and creates:

Signal:  
High Product Intent

Confidence:  
91%

Customer Intelligence can use this signal for segmentation.

---

## **Use Case 2 — Checkout Abandonment**

Thousands of customers begin checkout but leave after viewing delivery charges.

GrowthOS identifies a statistically significant drop-off.

AI recommendation:

> "Delivery pricing is strongly correlated with checkout abandonment for mobile users."

---

## **Use Case 3 — Advertising Attribution**

A customer arrives through a Meta advertisement.

The SDK captures campaign attribution and associates subsequent behavior with the campaign.

GrowthOS can determine:

Meta Campaign  
      ↓  
Landing Page  
      ↓  
Product View  
      ↓  
Checkout  
      ↓  
Purchase

This allows the Ads Layer Manager to optimize campaigns using downstream conversion behavior.

---

## **Use Case 4 — UX Friction**

Users repeatedly click a non-interactive element expecting it to open a product detail page.

GrowthOS identifies a dead-click cluster.

AI recommendation:

> "Make the product image clickable. 23% of mobile sessions show repeated interaction with the image."

---

## **Use Case 5 — High-Value Customer**

A returning customer frequently views premium products but has not purchased recently.

Customer Intelligence identifies:

High LTV  
High Intent  
High Churn Risk

The AI Growth Brain can recommend a personalized loyalty reward or targeted advertising campaign.

---

# **23\. Dependencies**

### **Internal**

* Customer Graph  
* AI Growth Brain  
* Customer Intelligence  
* Ads Layer Manager  
* Loyalty & Rewards  
* Authentication  
* Event Pipeline  
* Analytics

### **External**

* Merchant websites  
* Browser APIs  
* Consent-management systems  
* Cloud infrastructure

The SDK must communicate with other GrowthOS modules through APIs and events rather than directly accessing their databases.

---

# **24\. Scalability Strategy**

The module must be designed for high-volume event ingestion from the beginning.

Scaling mechanisms include:

* Stateless ingestion servers  
* Kafka partitioning  
* Horizontal consumer scaling  
* Batch ingestion  
* Event compression  
* S3 partitioning  
* ClickHouse distributed storage  
* Redis caching  
* Asynchronous processing

The architecture should support scaling from:

10M events/month  
        ↓  
100M events/month  
        ↓  
1B+ events/month

without requiring a fundamental architectural redesign.

---

# **25\. Module Success Metrics**

| Metric | MVP Target |
| ----- | ----- |
| Event Delivery Success | \>99.9% |
| Duplicate Events | \<0.01% |
| SDK Crash/Failure Rate | \<0.1% |
| Event Processing Latency | \<2 seconds |
| Funnel Accuracy | \>99% |
| Identity Association Accuracy | \>95% |
| SDK Performance Impact | \<1% |
| Behavioral Insight Adoption | \>50% |

---

# **26\. MVP Definition of Done**

The Behavior Intelligence SDK is considered MVP-complete when:

* JavaScript SDK can be installed on merchant websites.  
* Standard events are collected successfully.  
* Events are validated and deduplicated.  
* Events are batched and streamed through Kafka.  
* Raw events are stored in object storage.  
* Analytics events are queryable through ClickHouse.  
* Sessions are generated correctly.  
* Funnels can be created and analyzed.  
* Click and scroll heatmaps are available.  
* Checkout abandonment can be detected.  
* Behavioral signals are generated.  
* Customer Graph receives relevant events.  
* Ads attribution can be connected to downstream behavior.  
* Consent and opt-out mechanisms are functional.  
* Sensitive fields are protected.  
* SDK failure cannot break the merchant website.  
* Monitoring and alerting are operational.  
* Documentation and SDK integration guides are complete.

---

# **27\. Module Summary**

The Behavior Intelligence SDK is the **behavioral data foundation of GrowthOS**.

Its purpose is not to store every user interaction indefinitely. Its purpose is to capture behavioral activity efficiently, transform high-volume raw events into meaningful signals, and provide those signals to the Customer Intelligence and AI Growth Brain layers.

The architecture therefore separates:

**Collection → Streaming → Storage → Aggregation → Intelligence.**

This allows GrowthOS to process potentially billions of behavioral events while maintaining low latency, controlled storage costs, privacy safeguards, and reliable integration with the rest of the platform.

**Core principle:**

> **Capture behavior at scale, reduce it into meaningful signals, and turn those signals into growth decisions.**

# **GrowthOS — Module 2 part 2** 

# **Behavior Intelligence — Event Collection & Browser Extension Architecture**

---

# **Part 1 — Module Context and POC Scope**

## **1\. Purpose**

The Behavior Intelligence module is responsible for understanding how users interact with a business's website or application.

The module will eventually provide GrowthOS with behavioral intelligence that can be used to understand:

* How users navigate a website  
* Which products or pages users interact with  
* How users engage with important sections  
* Where users experience friction  
* Where users abandon a journey  
* How users behave before conversion  
* Which behaviors indicate purchase intent  
* Which behaviors indicate frustration  
* Which website experiences negatively affect conversion

The module is ultimately intended to become the behavioral intelligence foundation used by the AI Growth Brain.

---

# **2\. POC Strategy**

For the initial proof of concept, GrowthOS will use a **browser extension** rather than a merchant-installed SDK.

The extension allows the team to validate the behavioral analytics engine without first building the full merchant SDK integration system.

The POC will focus exclusively on:

**Browser → Event Collection → Event Processing → Behavioral Signal Generation**

The following components are intentionally excluded from the current POC architecture:

* Kafka  
* Snowflake  
* dbt  
* PostgreSQL  
* Neo4j  
* AI Growth Brain  
* Production SDK  
* Cloud event streaming  
* Long-term analytics infrastructure

These components will be designed later.

---

# **3\. Why Browser Extension for the POC**

A browser extension provides a fast way to validate the fundamental behavioral intelligence system.

The extension can access browser-level information and observe interactions on supported webpages without requiring the merchant to modify their website.

This allows the team to validate:

* Mouse tracking  
* Click tracking  
* Scroll tracking  
* Page usage  
* Session tracking  
* Element interaction  
* Element visibility  
* Performance signals  
* Form behavior  
* Product behavior  
* Checkout behavior  
* Behavioral signal generation

Once the POC is validated, the same event schema and behavioral signal architecture can be implemented inside the production JavaScript SDK.

---

# **4\. POC-to-Production Strategy**

The extension is a **data collection mechanism for the POC**, not the final architecture for merchant-side behavioral analytics.

The production architecture will eventually use:

**Merchant Website → GrowthOS SDK → Event Infrastructure**

The important architectural decision is that the **event schema should remain consistent between the extension and the future SDK.**

Therefore:

POC

Browser Extension  
       ↓  
Event Collection  
       ↓  
Event Normalization  
       ↓  
Behavioral Signals

will eventually become:

Production

GrowthOS SDK  
       ↓  
Event Collection  
       ↓  
Event Normalization  
       ↓  
Behavioral Signals

The downstream behavioral intelligence system should not need to fundamentally change when the collection mechanism changes.

---

# **5\. Core POC Principle**

The system should not attempt to send every raw browser event directly to a backend.

Instead:

**Raw Browser Events → Lightweight Processing → Structured Events → Behavioral Signals**

This reduces unnecessary data volume and allows the system to focus on information that is useful for growth intelligence.

---

# **6\. What the POC Should Analyze**

The POC will analyze the following behavioral categories:

### **Page Behavior**

* Page visits  
* Page exits  
* Time spent on page  
* Active time  
* Idle time  
* Page visibility  
* Navigation behavior  
* Refreshes

### **Mouse and Pointer Behavior**

* Pointer movement  
* Clicks  
* Double clicks  
* Hover  
* Pointer entry  
* Pointer exit  
* Mouse button interactions  
* Right-click behavior

### **Scroll Behavior**

* Scroll depth  
* Scroll velocity  
* Scroll direction  
* Scroll pauses  
* Maximum scroll depth

### **Element Behavior**

* Element visibility  
* Element interaction  
* CTA interaction  
* Hero section engagement  
* Product interaction  
* Navigation interaction

### **Forms**

* Form viewed  
* Form started  
* Field focused  
* Field blurred  
* Validation errors  
* Form abandoned  
* Form submitted

### **Commerce**

* Product viewed  
* Product interaction  
* Product variant selection  
* Add to cart  
* Remove from cart  
* Cart viewed  
* Checkout started  
* Checkout progression  
* Checkout abandonment  
* Purchase completion

### **Browser and Device Context**

* Device type  
* Browser  
* Operating system  
* Screen size  
* Viewport size  
* Connection information where available

### **Page Performance**

* Page loading  
* Rendering  
* Resource failures  
* Long tasks  
* Layout shifts  
* Core Web Vitals-related signals

---

# **7\. Important Architectural Principle**

GrowthOS should distinguish between:

**Raw Events**

and

**Behavioral Signals**

For example:

Raw Events

click  
click  
click  
click  
click

becomes:

Behavioral Signal

RAGE\_CLICK

Similarly:

product\_viewed  
product\_viewed  
long\_dwell  
variant\_selected

becomes:

HIGH\_PRODUCT\_INTENT

The long-term goal is for the GrowthOS intelligence layer to reason primarily over **behavioral signals and derived metrics**, rather than repeatedly processing millions of low-level browser events.

---

# **8\. POC Technology Stack**

| Component | Technology |
| ----- | ----- |
| Browser Extension | Chrome Extension |
| Extension Standard | Manifest V3 |
| Programming Language | TypeScript |
| Extension UI | React |
| Build Tool | Vite |
| DOM Tracking | Browser DOM APIs |
| Mouse Tracking | Pointer Events API |
| Element Visibility | IntersectionObserver |
| Page Performance | Performance APIs |
| Local Storage | IndexedDB |
| Extension Communication | Chrome Runtime Messaging |
| Background Processing | Chrome Extension Service Worker |
| Testing | Vitest \+ Playwright |

---

# **9\. POC High-Level Architecture**

                   USER BROWSER  
                         │  
                         ▼  
                MERCHANT WEB PAGE  
                         │  
                         ▼  
              GROWTHOS EXTENSION  
                         │  
              ┌──────────┴──────────┐  
              │                     │  
              ▼                     ▼  
        Content Script        Extension Service  
                                  Worker  
              │                     │  
              ▼                     │  
       Event Collectors             │  
              │                     │  
              ▼                     │  
       Event Normalizer             │  
              │                     │  
              ▼                     │  
       Behavioral Signal Engine     │  
              │                     │  
              ▼                     │  
          IndexedDB ◄───────────────┘

The extension architecture is intentionally local for the POC.

No external streaming infrastructure is required at this stage.

---

# **10\. Extension Components**

## **10.1 Content Script**

The content script operates within the context of the merchant webpage.

It is responsible for collecting browser and webpage interactions.

The content script will interact with:

* DOM  
* Pointer Events  
* Scroll Events  
* Visibility APIs  
* Performance APIs  
* Forms  
* Product elements  
* Checkout elements

The content script should perform lightweight processing only.

---

# **11\. Event Collectors**

The extension should use separate collectors rather than placing all tracking logic inside a single file.

Recommended collectors:

Mouse Collector  
Scroll Collector  
Page Collector  
Visibility Collector  
Performance Collector  
Form Collector  
Commerce Collector  
Navigation Collector  
Session Collector

Each collector produces standardized internal events.

Example:

Mouse Collector  
       ↓  
click event

Scroll Collector  
       ↓  
scroll\_depth event

Page Collector  
       ↓  
page\_viewed event

Commerce Collector  
       ↓  
product\_viewed event  
---

# **12\. Event Normalizer**

The Event Normalizer converts different browser events into a common GrowthOS event structure.

A canonical event should contain fields such as:

event\_id  
event\_type  
timestamp  
session\_id  
anonymous\_id  
page\_url  
page\_id  
element  
coordinates  
properties

Example:

{  
  "event\_id": "uuid",  
  "event\_type": "click",  
  "timestamp": 1724590000,  
  "session\_id": "session\_123",  
  "page\_url": "/pizza",  
  "element": {  
    "tag": "button",  
    "id": "add-to-cart",  
    "role": "button"  
  },  
  "coordinates": {  
    "x": 421,  
    "y": 382  
  }  
}

The exact schema can evolve during implementation, but the event model must remain consistent across the future SDK and POC extension.

---

# **13\. Local Event Processing**

The extension should process events before storing or transmitting them.

The basic pipeline is:

Raw Browser Event  
       ↓  
Validation  
       ↓  
Filtering  
       ↓  
Sampling  
       ↓  
Normalization  
       ↓  
Aggregation  
       ↓  
Structured Event

This is particularly important for high-frequency events such as pointer movement and scrolling.

---

# **14\. Mouse Movement Sampling**

The system should **not capture every pointer movement event**.

A browser can generate hundreds of movement events per second.

Instead, GrowthOS should sample pointer movement.

Example:

Raw pointer events  
        ↓  
Sampling  
        ↓  
10–20 movement samples/sec  
        ↓  
Local buffer

This provides sufficient information for:

* Heatmaps  
* Movement patterns  
* Interaction density  
* Engagement analysis

without unnecessarily consuming browser resources.

---

# **15\. Click Events**

Clicks should be captured immediately because they are relatively low-volume and highly valuable.

A click event should capture information such as:

event\_type  
timestamp  
x  
y  
page  
element  
element\_type  
element\_id  
element\_role

Example:

event\_type: click

page: /pizza/farmhouse

element:  
button  
Add to Cart

position:  
421,382

The system should avoid relying exclusively on arbitrary DOM IDs because many websites generate dynamic IDs.

Where possible, the extension should generate a stable element representation.

---

# **16\. Hover and Pointer Events**

The POC should capture:

* Pointer movement  
* Pointer entry  
* Pointer exit  
* Hover  
* Pointer down  
* Pointer up  
* Click  
* Double click  
* Context menu

Pointer movement should be sampled.

Lower-frequency interaction events should be captured directly.

---

# **17\. Scroll Tracking**

The extension should not capture every scroll pixel.

Instead, meaningful scroll thresholds should be generated.

Example:

scroll\_25  
scroll\_50  
scroll\_75  
scroll\_90  
scroll\_100

Additional metrics should include:

* Maximum scroll depth  
* Scroll direction  
* Scroll velocity  
* Scroll pauses

Example insight:

> 72% of visitors never reach the pricing section.

---

# **18\. Page Usage Tracking**

Page usage is a core behavioral metric.

The system should distinguish between:

**Time on Page**

and

**Active Time**

Example:

User enters page       10:00  
Browses                10:00–10:03  
Switches tab           10:03–10:08  
Returns                10:08–10:10  
Leaves                 10:10

Results:

Time on page \= 10 minutes

Active time \= 5 minutes

This distinction is important because a browser tab remaining open does not necessarily mean that the user is actively engaging with the page.

---

# **19\. Page Usage Detection**

The system should use:

* `visibilitychange`  
* `pagehide`  
* `focus`  
* `blur`  
* User interaction  
* Pointer activity  
* Scroll activity  
* Keyboard activity

The system should maintain:

session\_id  
page\_id  
page\_enter\_time  
last\_activity  
active\_time  
idle\_time  
page\_exit\_time  
interaction\_count  
---

# **20\. Hero Section Tracking**

Hero sections should receive specialized behavioral analysis because they are often the first major interaction point.

The system should detect:

hero\_visible  
hero\_entered  
hero\_exited  
hero\_dwell\_time  
hero\_cta\_viewed  
hero\_cta\_clicked  
hero\_interaction

`IntersectionObserver` should be used to determine when the hero enters and exits the viewport.

This allows GrowthOS to identify situations such as:

> 83% of visitors see the hero, but only 4% interact with the primary CTA.

---

# **21\. Element Visibility**

The system should use `IntersectionObserver` to detect important elements entering and leaving the viewport.

Potential elements:

* Hero  
* CTA  
* Product cards  
* Pricing  
* Reviews  
* Promotions  
* Checkout components  
* Navigation elements

Events may include:

element\_entered\_viewport  
element\_exited\_viewport  
element\_visible  
element\_hidden

This enables visibility-based behavioral analysis.

---

# **22\. Form Tracking**

Forms should be tracked without capturing sensitive input values.

Events:

form\_viewed  
form\_started  
field\_focused  
field\_blurred  
validation\_error  
form\_abandoned  
form\_submitted

The system must never capture:

* Password values  
* Payment details  
* Authentication tokens  
* Sensitive personal input

Sensitive fields should be automatically excluded from tracking.

---

# **23\. Product Behavior**

For supported e-commerce websites, the POC should attempt to identify:

product\_viewed  
product\_image\_viewed  
product\_image\_interacted  
product\_variant\_selected  
product\_quantity\_changed  
product\_added\_to\_cart  
product\_removed\_from\_cart  
product\_wishlisted

These events can be used to derive:

* Product interest  
* Purchase intent  
* Product comparison  
* Price sensitivity  
* Product abandonment

The POC may initially rely on configurable DOM selectors because a universal product schema cannot be guaranteed across arbitrary websites.

---

# **24\. Cart Behavior**

Track:

cart\_viewed  
cart\_item\_added  
cart\_item\_removed  
cart\_quantity\_changed  
cart\_updated  
cart\_abandoned

These events help identify behaviors such as:

> Users frequently remove products after viewing shipping costs.

---

# **25\. Checkout Behavior**

Checkout is one of the highest-value behavioral areas.

Track:

checkout\_started  
checkout\_step\_viewed  
checkout\_step\_completed  
checkout\_step\_failed  
payment\_started  
payment\_failed  
checkout\_abandoned  
purchase\_completed

This allows GrowthOS to construct:

Checkout Started  
       ↓  
Address  
       ↓  
Delivery  
       ↓  
Payment  
       ↓  
Purchase

and identify where customers abandon the process.

---

# **26\. Browser and Device Context**

The POC should capture non-sensitive technical context.

Potential fields:

device\_type  
browser  
browser\_version  
operating\_system  
screen\_width  
screen\_height  
viewport\_width  
viewport\_height  
connection\_type

This enables comparisons such as:

* Mobile vs desktop  
* Chrome vs Safari  
* Different viewport sizes  
* Different connection conditions

---

# **27\. Page Performance Tracking**

The POC should also identify poor loading and rendering experiences.

Potential performance signals include:

page\_load\_started  
dom\_loaded  
page\_load\_completed  
resource\_loaded  
resource\_failed  
long\_task\_detected  
layout\_shift\_detected  
first\_contentful\_paint  
largest\_contentful\_paint  
interaction\_latency

This allows GrowthOS to identify relationships such as:

> Slow page loading is associated with higher bounce and abandonment.

---

# **28\. Session Management**

The extension should maintain a session context.

A session should contain:

session\_id  
anonymous\_id  
start\_time  
last\_activity  
pages\_visited  
events  
active\_time  
idle\_time  
conversion\_status

The session manager should combine:

* Page visibility  
* User activity  
* Navigation  
* Browser focus  
* Interaction events

The POC should support anonymous session tracking.

Authenticated identity resolution will be addressed later in the production architecture.

---

# **29\. IndexedDB Storage**

For the POC, IndexedDB should be used for local event storage.

Suggested logical structure:

IndexedDB  
│  
├── raw\_events  
│  
├── behavioral\_signals  
│  
├── sessions  
│  
└── extension\_config

IndexedDB is preferred over localStorage because the POC may temporarily hold a large number of structured events.

---

# **30\. Behavioral Signal Engine**

The Signal Engine converts raw events and metrics into meaningful behavioral signals.

Example:

click  
click  
click  
click  
click  
       ↓  
RAGE\_CLICK

Another example:

product\_viewed  
product\_viewed  
long\_dwell  
variant\_selected  
       ↓  
HIGH\_PRODUCT\_INTENT

The signal engine should retain evidence behind every generated signal.

---

# **31\. Signal Structure**

A behavioral signal should conceptually contain:

signal\_id  
signal\_type  
timestamp  
session\_id  
page\_id  
element\_id  
confidence  
evidence

Example:

Signal:  
HIGH\_PRODUCT\_INTENT

Confidence:  
91%

Evidence:  
4 product views  
90-second dwell  
Variant selection  
Add-to-cart interaction

This evidence will later be consumed by the AI Growth Brain.

---

# **32\. Initial Behavioral Signal Taxonomy**

## **Engagement Signals**

* High Engagement  
* Low Engagement  
* Content Engagement  
* Product Engagement  
* Session Depth  
* Repeat Visit  
* Returning Visitor  
* Deep Scroll  
* Long Dwell  
* Short Dwell

## **Intent Signals**

* High Purchase Intent  
* Product Interest  
* Pricing Intent  
* Search Intent  
* Comparison Intent  
* Checkout Intent  
* Repeat Purchase Intent  
* Low Purchase Intent

## **Friction Signals**

* Rage Click  
* Dead Click  
* Repeated Click  
* Navigation Friction  
* Form Friction  
* Checkout Friction  
* Payment Friction  
* Search Friction  
* Interaction Failure  
* Backtracking

## **UX Signals**

* Hero Engagement  
* CTA Engagement  
* CTA Ignored  
* Content Visibility  
* Content Skipped  
* Navigation Confusion  
* Layout Confusion  
* Element Misinterpretation  
* Unexpected Interaction  
* UI Responsiveness Issue

## **Conversion Signals**

* Conversion Ready  
* Conversion Hesitation  
* Checkout Started  
* Checkout Abandoned  
* Cart Abandoned  
* Purchase Completed  
* Conversion Friction  
* High Conversion Probability  
* Low Conversion Probability

## **Customer Signals**

* New Visitor  
* Returning Visitor  
* High-Value Customer  
* At-Risk Customer  
* Churn Risk  
* Loyal Customer  
* Dormant Customer  
* Reactivated Customer  
* High-LTV Visitor  
* Low-LTV Visitor

## **Product Signals**

* Product Interest  
* Product Comparison  
* Product Abandonment  
* Product Affinity  
* Category Affinity  
* Price Sensitivity  
* Discount Sensitivity  
* Repeat Product Interest  
* Cross-Sell Opportunity  
* Upsell Opportunity

## **Marketing Signals**

* Campaign Engagement  
* Ad-to-Page Engagement  
* Ad-to-Product Intent  
* Ad-to-Cart Intent  
* Campaign Conversion Quality  
* Low-Quality Traffic  
* High-Quality Traffic  
* Landing Page Mismatch

## **Anomaly Signals**

* Conversion Drop  
* Traffic Spike  
* Traffic Drop  
* Abnormal Bounce Rate  
* Abnormal Checkout Abandonment  
* Unusual Interaction Pattern  
* Sudden Device-Specific Drop  
* Campaign Behavior Anomaly

---

# **33\. Behavioral Sequence Analysis**

The system should eventually analyze sequences rather than individual events.

Example:

Advertisement  
      ↓  
Landing Page  
      ↓  
Product View  
      ↓  
Price Check  
      ↓  
Reviews  
      ↓  
Back  
      ↓  
Product View  
      ↓  
Cart

The system may derive:

HIGH\_INTENT  
\+  
PRICE\_SENSITIVE  
\+  
COMPARISON\_BEHAVIOR

This is more valuable than simply reporting individual clicks.

---

# **34\. POC Behavioral Processing Model**

The complete local processing model is:

            BROWSER  
                │  
                ▼  
        Raw Browser Events  
                │  
     ┌──────────┼──────────┐  
     ▼          ▼          ▼  
   Mouse       Page      Commerce  
   Events      Events     Events  
     │          │          │  
     └──────────┼──────────┘  
                ▼  
         Event Collector  
                │  
         Sampling / Filter  
                │  
          Normalization  
                │  
          Local Aggregation  
                │  
       ┌────────┴────────┐  
       ▼                 ▼  
 Event Storage       Signal Engine  
 IndexedDB                │  
                          ▼  
                Behavioral Signals  
---

# **35\. Performance Requirements**

The extension must not negatively affect the merchant website.

The POC should establish a performance budget.

Target:

**\<1% measurable page-performance overhead**

The extension must:

* Load asynchronously  
* Avoid blocking page rendering  
* Use passive event listeners where appropriate  
* Avoid expensive DOM traversal  
* Avoid synchronous network requests  
* Sample high-frequency events  
* Perform lightweight local processing  
* Store data asynchronously

The merchant website must remain functional even if the extension experiences an internal error.

---

# **36\. Privacy and Data Protection**

The POC should follow a privacy-first design.

The system must not capture:

* Passwords  
* Payment information  
* Authentication tokens  
* Sensitive form values  
* Unnecessary personal information

Sensitive elements should be automatically excluded.

The event model should favor:

**Behavioral metadata**

over:

**Raw user content.**

For example:

Capture:

field\_focused

Do not capture:

field\_value \= "user@email.com"  
---

# **37\. POC Architecture Boundary**

The following architecture is **intentionally not part of the current POC**:

Kafka  
Snowflake  
dbt  
PostgreSQL  
Neo4j  
AI Growth Brain  
Cloud APIs  
Production SDK

The POC ends at:

Browser  
 ↓  
Extension  
 ↓  
Event Collection  
 ↓  
Event Normalization  
 ↓  
Local Storage  
 ↓  
Behavioral Signal Generation  
---

# **38\. Future Production Architecture**

After the POC is validated, the architecture can evolve into:

Merchant Website  
        │  
        ▼  
GrowthOS SDK  
        │  
        ▼  
FastAPI Ingestion  
        │  
        ▼  
Kafka  
        │  
        ▼  
Snowflake  
        │  
        ▼  
dbt  
        │  
        ├──────────────┐  
        ▼              ▼  
 PostgreSQL          Neo4j  
        │              │  
        └──────┬───────┘  
               ▼  
        AI Growth Brain

The POC should therefore be designed so that its event schema and behavioral signal definitions can transition into this architecture without requiring a redesign.

---

# **39\. Core Architectural Principle**

The Behavior Intelligence module should follow:

**Collect → Normalize → Reduce → Understand**

rather than:

**Collect → Store Everything → Analyze Everything**

The system should capture sufficient raw information to derive meaningful insights while reducing unnecessary high-frequency browser data.

---

# **40\. POC Definition of Done**

The Browser Extension Behavior Intelligence POC is complete when:

* Chrome Manifest V3 extension is functional.  
* TypeScript architecture is established.  
* Content script successfully runs on supported websites.  
* Mouse/pointer events are collected.  
* Pointer movement is sampled.  
* Click events are captured.  
* Hover events are captured.  
* Scroll behavior is captured.  
* Page usage is measured.  
* Active and idle time are distinguishable.  
* Hero section visibility is tracked.  
* Important elements can be tracked.  
* Forms can be analyzed without capturing sensitive values.  
* Product interactions can be detected on supported test websites.  
* Cart behavior can be detected.  
* Checkout behavior can be detected.  
* Page performance signals can be collected.  
* Sessions can be created.  
* Events are normalized into the canonical GrowthOS schema.  
* Events are stored in IndexedDB.  
* Behavioral signals can be generated.  
* Rage clicks can be detected.  
* Dead clicks can be detected.  
* High product intent can be detected.  
* Hero engagement can be measured.  
* Checkout friction can be detected.  
* Basic behavioral sequences can be generated.  
* Extension overhead remains within the defined performance budget.  
* The system does not capture sensitive input values.  
* The architecture is ready to replace the extension collector with the future GrowthOS SDK.

---

# **41\. Final POC Architecture**

                        USER  
                          │  
                          ▼  
                  MERCHANT WEBSITE  
                          │  
                          ▼  
                ┌─────────────────┐  
                │ GrowthOS        │  
                │ Browser         │  
                │ Extension       │  
                └────────┬────────┘  
                         │  
                         ▼  
                 ┌───────────────┐  
                 │ Content       │  
                 │ Script        │  
                 └───────┬───────┘  
                         │  
          ┌──────────────┼──────────────┐  
          ▼              ▼              ▼  
       Mouse           Page          Commerce  
       Events          Events         Events  
          │              │              │  
          └──────────────┼──────────────┘  
                         ▼  
                ┌────────────────┐  
                │ Event          │  
                │ Normalizer     │  
                └───────┬────────┘  
                        │  
                        ▼  
                ┌────────────────┐  
                │ Local Event    │  
                │ Processor      │  
                └───────┬────────┘  
                        │  
              ┌─────────┴─────────┐  
              ▼                   ▼  
       ┌──────────────┐    ┌──────────────┐  
       │ IndexedDB    │    │ Behavioral   │  
       │ Event Store  │    │ Signal Engine│  
       └──────────────┘    └───────┬──────┘  
                                   │  
                                   ▼  
                         ┌──────────────────┐  
                         │ Behavioral       │  
                         │ Signals          │  
                         └──────────────────┘

**POC Boundary:**

> **Browser activity → structured events → behavioral signals**

**Future Boundary:**

> **Merchant activity → GrowthOS SDK → event infrastructure → behavioral intelligence → AI Growth Brain**

# **GrowthOS — Module 3: Ads Layer Manager**

---

# **1\. Module Definition**

The **Ads Layer Manager** is the customer-acquisition layer of GrowthOS.

It provides a unified interface for planning, creating, deploying, monitoring, and optimizing advertising campaigns across multiple advertising platforms.

**Instead of requiring users to manually configure campaigns inside Google Ads, Meta Ads, and future advertising platforms, businesses describe their objective in natural language.**

Example:

> "Increase Domino's weekend orders from college students in Mumbai while keeping customer acquisition cost below ₹250."

GrowthOS converts this objective into:

\#what my ai is going to do automat

* Campaign strategy  
* Audience definition  
* Keyword research  
* Creative requirements  
* Budget allocation  
* Bidding strategy  
* Campaign structure  
* Platform-specific configurations  
* Optimization rules

The module initially supports **Google Ads and Meta Ads**, while its architecture must allow additional advertising platforms to be added through standardized connectors.

---

# **2\. Problem Statement**

Advertising platforms expose powerful but complex configuration systems.

Marketing teams must manually manage:

* Campaign creation  
* Keywords  
* Audiences  
* Budgets  
* Bidding  
* Creatives  
* Placements  
* Performance analysis  
* Optimization

This creates several problems:

* High operational overhead  
* Fragmented campaign data  
* Slow optimization  
* Poor cross-platform visibility  
* Difficulty translating business goals into campaign configuration  
* Manual budget allocation  
* Limited connection between advertising performance and downstream customer behavior

The Ads Layer Manager abstracts platform complexity while preserving the ability for advanced users to inspect and modify detailed configurations.

---

# **3\. Scope**

## **3.1 Included in MVP**

### **Campaign Management**

* Natural-language campaign creation  
* Campaign planning  
* Campaign drafts  
* Campaign deployment  
* Campaign editing  
* Campaign pausing  
* Campaign activation  
* Campaign duplication

### **Google Ads**

* Search campaigns  
* Keyword management  
* Search terms  
* Budget management  
* Bidding configuration  
* Ad groups  
* Text ads  
* Conversion tracking  
* Performance metrics

### **Meta Ads**

* Campaigns  
* Ad sets  
* Audiences  
* Creatives  
* Placements  
* Budgets  
* Conversion objectives  
* Performance metrics

### **AI Capabilities**

* Keyword research  
* Audience discovery  
* Campaign recommendations  
* Budget allocation  
* Bid recommendations  
* Creative recommendations  
* Performance analysis  
* Campaign optimization

### **Cross-Platform**

* Unified campaign view  
* Cross-platform comparison  
* Unified attribution  
* Budget recommendations  
* Performance reporting

---

# **4\. Out of Scope for MVP**

* TikTok Ads  
* LinkedIn Ads  
* Pinterest Ads  
* X Ads  
* Programmatic advertising  
* Television advertising  
* Offline advertising  
* Full creative-generation platform  
* Autonomous ad account creation  
* Guaranteed lowest bid  
* Guaranteed auction win  
* Competitor account manipulation

Future platforms should be added through the connector architecture without changing the core Ads Layer.

---

# **5\. Core Responsibilities**

The Ads Layer Manager owns:

* Advertising account connections  
* Campaign planning  
* Campaign configuration  
* Campaign deployment  
* Keyword management  
* Audience management  
* Budget management  
* Bid strategy  
* Campaign monitoring  
* Performance analysis  
* Optimization recommendations

It does not own:

* Website behavioral tracking  
* Customer identity  
* Loyalty balances  
* Final customer LTV models

These capabilities are provided by the other GrowthOS modules.

---

# **6\. Technology Stack**

| Layer | Technology |
| ----- | ----- |
| Backend Language | Python |
| Backend Framework | FastAPI |
| Frontend | Next.js \+ TypeScript |
| AI/ML | Python |
| Primary Database | PostgreSQL |
| Analytics Store | ClickHouse |
| Cache | Redis |
| Event Streaming | Kafka |
| Object Storage | S3-compatible storage |
| API Architecture | REST \+ Webhooks |
| Google Integration | Google Ads API |
| Meta Integration | Meta Marketing API |
| Authentication | OAuth 2.0 |
| Infrastructure | Docker \+ Kubernetes |
| Monitoring | Prometheus \+ Grafana |
| Observability | OpenTelemetry |

The module uses connector abstractions so that Google Ads and Meta Ads do not become tightly coupled to the core campaign engine.

---

# **7\. High-Level Architecture**

                    Business User  
                          │  
                          ▼  
                  GrowthOS Interface  
                          │  
                          ▼  
                  AI Campaign Planner  
                          │  
             ┌────────────┼────────────┐  
             ▼            ▼            ▼  
        Audience      Keyword       Budget  
        Research      Research       Planner  
             │            │            │  
             └────────────┼────────────┘  
                          ▼  
                  Campaign Definition  
                          │  
                          ▼  
                  Validation Engine  
                          │  
                    Approval Layer  
                          │  
             ┌────────────┴────────────┐  
             ▼                         ▼  
       Google Connector          Meta Connector  
             │                         │  
             ▼                         ▼  
       Google Ads API             Meta API  
             │                         │  
             └────────────┬────────────┘  
                          ▼  
                   Performance Data  
                          │  
                          ▼  
                  Optimization Engine  
                          │  
                          ▼  
                    AI Growth Brain

---

# **8\. Advertising Connector Architecture**

Each advertising platform must implement a common connector interface.

Conceptually:

AdsConnector

├── authenticate()  
├── create\_campaign()  
├── update\_campaign()  
├── pause\_campaign()  
├── enable\_campaign()  
├── fetch\_metrics()  
├── manage\_budget()  
├── manage\_audience()  
└── manage\_creatives()

Google Ads and Meta Ads implement this interface independently.

This allows future integrations such as TikTok or LinkedIn to be added without rewriting the campaign orchestration layer.

---

# **9\. Natural Language Campaign Creation**

The primary user interaction is semantic.

Example:

> "Launch a ₹50,000 campaign for Domino's weekend orders targeting 18–25 year-olds in Mumbai."

The AI converts this into a structured campaign plan.

Example:

Objective:  
Conversions

Audience:  
18–25  
Mumbai  
Food/Pizza interests

Budget:  
₹50,000

Duration:  
Friday–Sunday

Platforms:  
Google \+ Meta

Optimization Goal:  
Purchase

Target CPA:  
₹250

The system must show the interpreted configuration before deployment.

Users can modify any generated parameter.

---

# **10\. Campaign Planning Engine**

The Campaign Planning Engine converts business goals into platform-specific campaigns.

The planner determines:

* Campaign objective  
* Target audience  
* Geography  
* Budget  
* Schedule  
* Keywords  
* Bid strategy  
* Conversion objective  
* Creative requirements

The AI must distinguish between:

**Business intent**

and

**Platform implementation.**

For example:

> "Get more pizza orders."

may become different configurations on Google and Meta while maintaining the same business objective.

---

# **11\. Keyword Research**

For Google Search campaigns, GrowthOS generates keyword recommendations based on:

* Business objective  
* Product catalog  
* Historical performance  
* Search-term data  
* Landing page content  
* Customer behavior  
* Conversion performance

Keywords are categorized into:

* High intent  
* Medium intent  
* Discovery  
* Branded  
* Competitor  
* Long-tail

The system should also recommend negative keywords.

Example:

High Intent:  
pizza delivery mumbai  
order pizza online

Negative:  
free pizza  
pizza recipe  
pizza job

Users must be able to review and modify keyword recommendations before deployment.

---

# **12\. Audience Discovery**

The system should identify audiences using:

* Demographics  
* Geography  
* Interests  
* Behaviors  
* Website behavior  
* Purchase history  
* Loyalty status  
* Customer segments  
* Predicted LTV  
* Churn probability

Example:

Audience:

High-value customers  
18–30  
Mumbai  
Mobile users  
High purchase intent

Customer Intelligence can provide high-value segments to the Ads Layer Manager.

---

# **13\. Budget Optimization**

The system continuously evaluates budget allocation.

Example:

Campaign A  
ROAS \= 2.1

Campaign B  
ROAS \= 5.8

Campaign C  
ROAS \= 1.4

AI recommendation:

Reduce Campaign C by 30%.

Increase Campaign B by 25%.

Expected incremental revenue:  
₹X

Budget changes must respect configured limits.

Example:

Maximum daily increase:  
20%

Maximum daily spend:  
₹50,000

---

# **14\. Bidding and Auction Optimization**

GrowthOS should optimize toward the business objective rather than simply maximizing bid price.

The system can recommend:

* Maximize conversions  
* Target CPA  
* Target ROAS  
* Manual bidding  
* Automated platform bidding

The system must not claim that it can guarantee winning every auction.

Instead, it should optimize expected business value using available platform signals.

The optimization objective should ultimately move toward:

> **Highest expected business value within the defined budget and constraints.**

---

# **15\. Campaign Deployment**

Before deployment, GrowthOS performs validation.

Required checks:

* Connected advertising account  
* Valid authentication  
* Valid campaign objective  
* Valid budget  
* Valid destination URL  
* Valid audience  
* Valid creatives  
* Platform compatibility

Deployment states:

DRAFT  
↓  
VALIDATING  
↓  
AWAITING\_APPROVAL  
↓  
APPROVED  
↓  
DEPLOYING  
↓  
ACTIVE

Failure states include:

VALIDATION\_FAILED  
DEPLOYMENT\_FAILED  
PLATFORM\_REJECTED  
AUTHENTICATION\_FAILED

---

# **16\. Approval Modes**

The Ads Layer supports three operating modes.

### **Manual**

AI only recommends changes.

### **Approval**

AI recommends changes and waits for user approval.

### **Autonomous**

AI executes changes within predefined constraints.

Example autonomous policy:

Maximum budget increase:  
15%

Minimum ROAS:  
3.0

Maximum daily spend:  
₹25,000

Allowed action:  
Budget adjustment

Actions outside policy boundaries require human approval.

---

# **17\. Campaign Optimization Loop**

The core optimization cycle is:

Collect Performance  
        ↓  
Analyze  
        ↓  
Identify Opportunity  
        ↓  
Generate Recommendation  
        ↓  
Calculate Confidence  
        ↓  
Check Policy  
        ↓  
Approval / Autonomous Execution  
        ↓  
Measure Result  
        ↓  
Repeat

The system should avoid reacting to insignificant fluctuations.

Optimization decisions should consider:

* Minimum sample size  
* Statistical significance  
* Historical baseline  
* Budget constraints  
* Campaign maturity  
* Seasonality

---

# **18\. Cross-Module Integration**

The Ads Layer receives behavioral signals from the SDK.

Example:

Meta Campaign  
     ↓  
Landing Page  
     ↓  
Product View  
     ↓  
Checkout  
     ↓  
Purchase

The Ads Layer can therefore optimize toward actual business outcomes rather than clicks alone.

Customer Intelligence can provide:

* High-LTV audiences  
* Churn segments  
* Repeat-purchase segments  
* Predicted purchase intent

Loyalty can provide:

* Loyalty membership  
* Reward usage  
* Customer retention status

---

# **19\. Attribution**

GrowthOS should maintain campaign attribution identifiers.

Supported attribution information includes:

* Source  
* Medium  
* Campaign  
* Ad  
* Keyword  
* Click ID  
* Platform  
* Landing page

The system associates advertising interactions with downstream behavior and purchases where technically and legally permitted.

Attribution models should initially support:

* Last-touch  
* First-touch  
* Campaign-level attribution

More advanced multi-touch attribution can be introduced later.

---

# **20\. Performance Analytics**

The Ads Layer collects:

* Impressions  
* Reach  
* Clicks  
* CTR  
* CPC  
* CPM  
* Spend  
* Conversions  
* CPA  
* Revenue  
* ROAS

Performance data should be normalized into a common GrowthOS schema.

Example:

platform  
campaign\_id  
campaign\_name  
spend  
impressions  
clicks  
conversions  
revenue  
roas  
timestamp

This allows Google and Meta campaigns to be compared consistently.

---

# **21\. AI Recommendations**

Examples:

> "Meta Campaign B generated 34% more purchases than the account average while maintaining a 4.8 ROAS. Increase budget by 15%."

> "Google keyword 'pizza delivery Mumbai' has a high conversion rate but is approaching its daily budget limit."

> "Campaign C has received sufficient traffic but has remained below the minimum ROAS threshold for seven days. Consider pausing it."

Every recommendation must include:

* Evidence  
* Confidence  
* Expected impact  
* Recommended action  
* Affected campaign

---

# **22\. Edge Cases**

The system must handle:

* Expired OAuth tokens  
* API rate limits  
* Platform outages  
* Campaign rejection  
* Invalid creatives  
* Invalid landing pages  
* Budget conflicts  
* Duplicate campaigns  
* Insufficient conversion data  
* Delayed platform metrics  
* Attribution mismatches  
* Conflicting optimization rules

Platform failures must not corrupt GrowthOS campaign state.

---

# **23\. APIs**

Initial API surface:

POST   /api/v1/ads/accounts/connect  
GET    /api/v1/ads/accounts

POST   /api/v1/ads/campaigns/plan  
POST   /api/v1/ads/campaigns

GET    /api/v1/ads/campaigns/{id}  
PATCH  /api/v1/ads/campaigns/{id}

POST   /api/v1/ads/campaigns/{id}/pause  
POST   /api/v1/ads/campaigns/{id}/activate

GET    /api/v1/ads/campaigns/{id}/metrics  
GET    /api/v1/ads/recommendations

POST   /api/v1/ads/recommendations/{id}/approve

All APIs must support workspace authorization and audit logging.

---

# **24\. Events**

The module publishes:

ads.account.connected  
ads.campaign.created  
ads.campaign.deployed  
ads.campaign.activated  
ads.campaign.paused  
ads.campaign.failed  
ads.metrics.updated  
ads.recommendation.generated  
ads.recommendation.approved  
ads.optimization.executed  
ads.budget.changed

These events are consumed by the AI Growth Brain, Analytics, Customer Intelligence, and Governance systems.

---

# **25\. Example Use Cases**

## **Use Case 1 — Semantic Campaign Creation**

Domino's enters:

> "Increase weekend pizza orders from college students in Mumbai."

GrowthOS generates campaigns for Google and Meta with recommended audiences, budgets, keywords, and optimization objectives.

---

## **Use Case 2 — Budget Optimization**

Meta Campaign A produces:

ROAS \= 5.2

Campaign B:

ROAS \= 1.8

GrowthOS recommends reallocating budget from B to A while respecting spending constraints.

---

## **Use Case 3 — Behavioral Optimization**

The SDK reports that users from a particular Meta campaign frequently view a product but abandon checkout.

GrowthOS recommends:

> "Do not increase this campaign's budget yet. The primary bottleneck appears to be checkout conversion rather than traffic acquisition."

This demonstrates cross-module reasoning.

---

## **Use Case 4 — LTV-Based Acquisition**

Customer Intelligence identifies a segment with unusually high lifetime value.

GrowthOS recommends creating a lookalike or equivalent high-value audience where supported by the advertising platform.

---

## **Use Case 5 — Autonomous Optimization**

Domino's configures:

Minimum ROAS: 3.0  
Maximum daily spend: ₹30,000  
Maximum budget increase: 15%  
Mode: Autonomous

GrowthOS can automatically make permitted budget adjustments while recording every action.

---

# **26\. Security**

The Ads Layer must protect advertising credentials and campaign access.

Requirements:

* OAuth 2.0  
* Encrypted credential storage  
* Workspace isolation  
* RBAC  
* API rate limiting  
* Audit logs  
* Token rotation  
* Secure secret management

OAuth tokens must never be exposed to frontend clients.

---

# **27\. Scalability**

The Ads Layer should use asynchronous workers for:

* Metric synchronization  
* Campaign deployment  
* Optimization calculations  
* Platform API calls  
* Recommendation generation

Platform connectors must be horizontally scalable.

Rate limits must be enforced per advertising platform and account.

The system should maintain internal queues to prevent platform API limits from affecting user-facing API latency.

---

# **28\. Dependencies**

### **Internal**

* AI Growth Brain  
* Customer Intelligence  
* Behavior Intelligence SDK  
* Loyalty Platform  
* Event Pipeline  
* Authentication  
* Analytics

### **External**

* Google Ads API  
* Meta Marketing API  
* Merchant websites  
* Conversion tracking systems

---

# **29\. Module Success Metrics**

| Metric | MVP Target |
| ----- | ----- |
| Campaign Deployment Success | \>98% |
| API Synchronization Success | \>99% |
| Recommendation Acceptance | \>60% |
| Optimization Execution Success | \>98% |
| Metric Freshness | \<15 minutes |
| Duplicate Campaign Rate | \<0.1% |
| OAuth Integration Success | \>99% |
| Average Campaign Creation Time | \<5 minutes |

---

# **30\. MVP Definition of Done**

The Ads Layer Manager is considered MVP-complete when:

* Google Ads integration is operational.  
* Meta Ads integration is operational.  
* Users can connect advertising accounts through OAuth.  
* Users can create campaigns using natural language.  
* AI generates campaign configurations.  
* Keyword research works for supported Google campaigns.  
* Audience recommendations work for supported platforms.  
* Campaigns can be reviewed and approved.  
* Campaigns can be deployed through platform APIs.  
* Campaign performance is synchronized.  
* Google and Meta metrics are normalized.  
* AI generates optimization recommendations.  
* Budget optimization respects configured limits.  
* Manual, Approval, and Autonomous modes are supported.  
* SDK behavioral signals can influence optimization.  
* Customer Intelligence segments can be used for targeting where platform capabilities permit.  
* All campaign changes are audited.  
* API failures and platform rate limits are handled.  
* Monitoring and alerting are operational.  
* Integration and API documentation is complete.

---

# **31\. Module Summary**

The Ads Layer Manager is the **acquisition engine of GrowthOS**.

It abstracts the complexity of individual advertising platforms while preserving detailed control for advanced users. Businesses describe growth objectives in natural language, and GrowthOS converts those objectives into platform-specific campaign configurations, deploys them, monitors performance, and continuously recommends or executes optimizations.

Its most important architectural characteristic is that it does not optimize advertising in isolation.

It receives signals from:

**Behavior Intelligence → Customer Intelligence → Loyalty**

and uses those signals to optimize advertising toward actual business outcomes.

**Core principle:**

> **Do not optimize for clicks. Optimize advertising for measurable business growth.**

# **GrowthOS — Module 4: AI Growth Brain & Customer Intelligence**

---

# **1\. Module Definition**

The **AI Growth Brain & Customer Intelligence module** is the reasoning and intelligence layer of GrowthOS.

It sits above the other three modules and continuously reasons across:

* Advertising data  
* Website behavior  
* Customer interactions  
* Purchases  
* Loyalty activity  
* Campaign performance  
* Customer profiles  
* Business objectives

The module transforms fragmented operational data into **semantic business intelligence**.

Users should be able to ask:

> "Why did sales decrease this week?"

> "Which customers should we target?"

> "Why is Meta performing better than Google?"

> "Which customers are likely to churn?"

> "What should we do to increase weekend orders?"

GrowthOS should retrieve relevant business context, reason over the available data, explain the answer, provide a confidence score, and recommend actions.

The module therefore serves as the **decision-making and orchestration layer** for the entire GrowthOS platform.

---

# **2\. Problem Statement**

Businesses have large amounts of data but limited ability to convert that data into decisions.

Data exists across:

* Advertising platforms  
* Websites  
* Applications  
* Commerce systems  
* Loyalty programs  
* Customer databases  
* Analytics platforms

Traditional analytics systems primarily answer:

> "What happened?"

GrowthOS must additionally answer:

> "Why did it happen?"

> "What will probably happen next?"

> "What should the business do?"

> "Can GrowthOS execute that action?"

The AI Growth Brain closes this gap.

---

# **3\. Scope**

## **3.1 Included in MVP**

### **AI Intelligence**

* Natural-language business queries  
* Semantic business reasoning  
* Recommendation generation  
* Explainable insights  
* Confidence scoring  
* Business summaries  
* Anomaly detection  
* Forecasting  
* Cross-module reasoning

### **Customer Intelligence**

* Unified customer profiles  
* Customer segmentation  
* Customer journey  
* LTV estimation  
* Churn prediction  
* Purchase propensity  
* Engagement scoring  
* Next-best-action recommendations

### **AI Planning**

* Goal decomposition  
* Action planning  
* Workflow generation  
* Campaign recommendations  
* Loyalty recommendations  
* Conversion recommendations

### **Automation**

* Manual mode  
* Approval mode  
* Autonomous mode  
* Policy enforcement  
* Action execution  
* Outcome measurement

---

# **4\. Out of Scope for MVP**

* Fully autonomous business operation  
* Financial trading decisions  
* Legal decision-making  
* Medical decision-making  
* General-purpose AI assistant unrelated to business growth  
* Training foundation models from scratch  
* Fully autonomous creative production  
* Automatic modification of merchant source code  
* Unrestricted advertising account control

The AI must operate within explicit business policies and platform permissions.

---

# **5\. Core Responsibilities**

The module owns:

* Business reasoning  
* Customer intelligence  
* Customer profiles  
* Segmentation  
* Predictions  
* Recommendations  
* AI planning  
* Cross-module orchestration  
* Confidence scoring  
* Explanation generation  
* Automation policies  
* Decision history

It does not directly own:

* Raw website event collection  
* Advertising platform API integration  
* Loyalty point ledgers

Those remain owned by Modules 1–3.

---

# **6\. Technology Stack**

| Layer | Technology |
| ----- | ----- |
| Primary Language | Python |
| API Framework | FastAPI |
| AI/ML Framework | Python ecosystem |
| LLM | Configurable enterprise LLM |
| Embeddings | Enterprise embedding model |
| Operational Database | PostgreSQL |
| Customer Graph | Neo4j |
| Analytics Store | ClickHouse |
| Event Streaming | Kafka |
| Cache | Redis |
| Object Storage | S3-compatible storage |
| Vector Search | pgvector / dedicated vector index |
| APIs | REST \+ Webhooks |
| Infrastructure | Docker \+ Kubernetes |
| Monitoring | Prometheus \+ Grafana |
| Observability | OpenTelemetry |

The AI model must remain replaceable. GrowthOS should not hard-code business logic into a specific model provider.

---

# **7\. High-Level Architecture**

                   User / Business Goal  
                            │  
                            ▼  
                    Semantic Interface  
                            │  
                            ▼  
                     AI Growth Brain  
                            │  
             ┌──────────────┼──────────────┐  
             ▼              ▼              ▼  
          Planner        Retriever       Policy  
             │              │              │  
             └──────────────┼──────────────┘  
                            ▼  
                       Reasoning  
                            │  
                  ┌─────────┴─────────┐  
                  ▼                   ▼  
             Customer Graph       Analytics  
                  │                   │  
                  └─────────┬─────────┘  
                            ▼  
                     Recommendation  
                            │  
                   Confidence \+ Evidence  
                            │  
                    Approval / Policy  
                            │  
                            ▼  
                     Action Executor  
                            │  
              ┌─────────────┼─────────────┐  
              ▼             ▼             ▼  
             Ads           SDK         Loyalty

---

# **8\. Unified Customer Graph**

The Customer Graph provides a relationship-oriented representation of customer activity.

A customer can be connected to:

Customer  
 ├── Sessions  
 ├── Campaigns  
 ├── Advertisements  
 ├── Products  
 ├── Orders  
 ├── Loyalty Programs  
 ├── Rewards  
 ├── Referrals  
 ├── Devices  
 └── Events

Neo4j is used for relationship-heavy queries and customer journey analysis.

PostgreSQL remains the source of truth for operational customer records.

---

# **9\. Customer Profile**

Each customer should have a dynamic profile.

Example:

Customer: CUST-48291

Acquisition:  
Meta

Customer Status:  
Returning

Orders:  
12

Average Order Value:  
₹820

Estimated LTV:  
₹8,400

Churn Probability:  
78%

Purchase Probability:  
84%

Preferred Device:  
Mobile

Preferred Category:  
Pizza

Loyalty Tier:  
Gold

Last Purchase:  
9 days ago

The profile must update as new events arrive.

---

# **10\. Identity Resolution**

The system must connect anonymous activity to known customers where permitted.

Potential identifiers include:

* Customer ID  
* Authenticated account  
* Session ID  
* Device ID  
* First-party cookies  
* Transaction identifiers  
* Loyalty membership

Identity resolution must use configurable confidence rules.

Example:

Anonymous Session  
       ↓  
User Logs In  
       ↓  
Identity Match  
       ↓  
Historical Session Linked

Low-confidence identity matches must not be silently merged.

---

# **11\. Customer Segmentation**

GrowthOS supports both rule-based and AI-generated segments.

Example:

> "Show me customers who spent more than ₹5,000, purchased at least three times, and have not purchased in the last 30 days."

The system creates:

Segment:  
High-value inactive customers

Rules:  
LTV \> ₹5,000  
Orders \>= 3  
Days since purchase \> 30

AI-generated segments must always expose their underlying criteria.

---

# **12\. Lifetime Value Prediction**

GrowthOS estimates customer lifetime value using:

* Historical purchases  
* Purchase frequency  
* Average order value  
* Recency  
* Customer tenure  
* Product affinity  
* Loyalty activity  
* Engagement  
* Acquisition source

The system should expose both:

**Predicted LTV**

and

**Confidence**

Example:

Predicted LTV: ₹8,400

Confidence: 87%

Primary factors:  
• 12 previous purchases  
• High repeat frequency  
• Gold loyalty status

Predictions should be recalculated as meaningful customer behavior changes.

---

# **13\. Churn Prediction**

The system identifies customers whose engagement or purchase behavior indicates potential churn.

Signals include:

* Increasing purchase intervals  
* Reduced sessions  
* Reduced product engagement  
* Loyalty inactivity  
* Failed transactions  
* Reduced campaign engagement

Example:

> "Customer churn probability increased from 42% to 78% after 35 days without a purchase."

The model must identify the major contributing factors.

---

# **14\. Purchase Propensity**

GrowthOS estimates the likelihood that a customer will perform a target action.

Examples:

* Purchase  
* Repeat purchase  
* Loyalty redemption  
* Product interaction  
* Subscription renewal

Example:

Purchase Probability:  
91%

Target:  
Pizza Combo A

Primary signals:  
Repeated product views  
Recent cart activity  
Previous purchases

These predictions can be consumed by the Ads and Loyalty modules.

---

# **15\. Semantic Business Interface**

The primary interface to the Growth Brain is natural language.

Examples:

> "Why did revenue fall yesterday?"

> "Which campaigns are wasting money?"

> "Show me our highest-value customers."

> "Why are mobile users abandoning checkout?"

> "What should we do to improve retention?"

The system converts the request into structured intent before querying data.

---

# **16\. AI Reasoning Pipeline**

Every business query follows a controlled pipeline:

User Query  
    ↓  
Intent Detection  
    ↓  
Entity Resolution  
    ↓  
Permission Check  
    ↓  
Context Retrieval  
    ↓  
Data Analysis  
    ↓  
Reasoning  
    ↓  
Confidence Calculation  
    ↓  
Recommendation  
    ↓  
Explanation

The AI must not answer using unsupported assumptions when required data is unavailable.

---

# **17\. Retrieval and Context**

The AI should retrieve only relevant context.

Potential sources:

* Campaign metrics  
* Customer Graph  
* Behavioral signals  
* Loyalty activity  
* Business rules  
* Historical performance  
* Previous recommendations  
* Organization configuration

The system should avoid passing unnecessary raw data to the model.

Large datasets should first be aggregated or queried deterministically.

---

# **18\. Business Rules and Policy Engine**

AI reasoning must operate within deterministic business constraints.

Example:

Rule:

Maximum daily ad budget:  
₹50,000

Maximum automatic increase:  
15%

Minimum ROAS:  
3.0

If AI recommends a 30% increase, the Policy Engine rejects autonomous execution.

The AI can still present the recommendation for manual approval.

This prevents model output from bypassing business controls.

---

# **19\. Recommendation Model**

Every recommendation follows a standardized structure.

Recommendation

Problem:  
Meta campaign performance decreased.

Evidence:  
ROAS dropped from 4.2 to 2.8.

Likely Cause:  
Creative fatigue.

Confidence:  
91%

Recommended Action:  
Replace Creative A.

Expected Impact:  
Potential 8–12% conversion improvement.

Execution:  
Approval Required

This structure must remain consistent across the platform.

---

# **20\. Confidence Scoring**

Confidence should be calculated using factors such as:

* Data quality  
* Sample size  
* Model certainty  
* Historical consistency  
* Evidence strength  
* Prediction stability

Example:

| Recommendation | Confidence |
| ----- | ----- |
| Increase Campaign B Budget | 96% |
| Checkout Friction Detected | 91% |
| Churn Risk | 84% |
| New Audience Opportunity | 72% |

Low-confidence recommendations must be clearly labeled.

Autonomous execution should require configurable minimum confidence.

---

# **21\. Progressive Abstraction**

The Growth Brain supports four levels of information.

### **Executive**

> "Revenue increased 12% because repeat customers increased."

### **Manager**

> "Repeat customer revenue increased 18%, primarily from Gold loyalty members."

### **Analyst**

Detailed campaign, customer, funnel, and cohort metrics.

### **Engineer**

Raw event payloads, API requests, logs, model inputs, and system diagnostics.

Users can drill down from summary to evidence.

---

# **22\. Operating Modes**

## **Manual**

AI recommends.

User executes.

## **Approval**

AI recommends.

User approves.

GrowthOS executes.

## **Autonomous**

AI recommends.

Policy Engine validates.

GrowthOS executes automatically.

Every autonomous action must be logged.

---

# **23\. Cross-Module Orchestration**

The Growth Brain is the only module that reasons across all four GrowthOS capabilities.

Example:

Ads:  
Meta traffic increased

        ↓

SDK:  
Checkout abandonment increased

        ↓

Customer Intelligence:  
High-value mobile customers affected

        ↓

Loyalty:  
Offer available to affected segment

        ↓

AI Growth Brain:  
Do not increase Meta budget.  
Fix checkout friction first.  
Offer loyalty incentive to high-value customers.

This is the central value of the architecture.

---

# **24\. Automation Execution**

AI-generated actions are converted into structured commands.

Example:

Action:  
Increase Meta Campaign B budget

Parameters:  
Campaign \= B  
Increase \= 10%  
Maximum \= ₹30,000/day

The execution layer validates the action against policy before sending it to the appropriate module.

The AI must never directly execute arbitrary API calls.

---

# **25\. Learning and Outcome Measurement**

After an action is executed, GrowthOS records:

* Action  
* Timestamp  
* Target  
* Expected outcome  
* Actual outcome  
* Result  
* Confidence  
* Approval status

Example:

Recommendation:  
Increase Campaign B budget 10%

Expected:  
\+8% conversions

Actual:  
\+11% conversions

Result:  
Successful

This creates an optimization history for future recommendations.

---

# **26\. Example Use Cases**

## **Use Case 1 — Revenue Diagnosis**

Domino's asks:

> "Why is revenue down this week?"

GrowthOS determines:

* Google CPC increased.  
* Mobile checkout abandonment increased.  
* Repeat purchases decreased.

The AI identifies the combined impact and recommends actions across multiple modules.

---

## **Use Case 2 — Churn Prevention**

GrowthOS identifies:

High LTV  
High churn probability  
Low recent engagement

It recommends a loyalty reward and personalized campaign.

---

## **Use Case 3 — Campaign Optimization**

The AI determines that one customer segment generates significantly higher LTV.

It recommends reallocating advertising budget toward that segment.

---

## **Use Case 4 — Executive Question**

CEO asks:

> "What should we focus on this week?"

GrowthOS responds with prioritized business opportunities ranked by:

* Expected impact  
* Confidence  
* Urgency  
* Implementation effort

---

# **27\. APIs**

Initial API surface:

POST /api/v1/ai/query  
GET  /api/v1/ai/recommendations

GET  /api/v1/customers/{id}  
GET  /api/v1/customers/{id}/timeline

POST /api/v1/segments  
GET  /api/v1/segments

GET  /api/v1/customer-insights  
GET  /api/v1/predictions

POST /api/v1/automations  
GET  /api/v1/automations

POST /api/v1/recommendations/{id}/approve  
POST /api/v1/recommendations/{id}/reject

All AI actions must pass through authorization and policy validation.

---

# **28\. Events**

The module publishes:

ai.query.completed  
ai.recommendation.generated  
ai.recommendation.approved  
ai.recommendation.rejected  
ai.action.executed  
ai.action.failed  
ai.prediction.generated  
customer.segment.created  
customer.churn.detected  
customer.ltv.updated  
customer.intent.detected

These events are available to Analytics and Governance systems.

---

# **29\. Security & AI Governance**

Requirements:

* Tenant isolation  
* RBAC  
* Encryption  
* Audit logging  
* Model version tracking  
* Prompt logging where permitted  
* Recommendation versioning  
* Policy enforcement  
* Human approval controls  
* Sensitive-data filtering

The system must never expose one organization's customer data to another organization.

AI responses must be grounded in authorized workspace data.

---

# **30\. AI Failure Handling**

If the AI cannot confidently answer a question, it must state the limitation.

Example:

> "I cannot reliably determine why conversions decreased because only 18 purchases were recorded during the comparison period."

The system must not fabricate metrics or explanations.

If data sources disagree, the response should explicitly identify the discrepancy.

---

# **31\. Scalability**

The Growth Brain should separate:

* Real-time queries  
* Asynchronous analysis  
* Batch predictions  
* Recommendation generation

Customer predictions can be generated asynchronously.

High-frequency operational queries should use precomputed aggregates and cached results.

AI inference should be horizontally scalable.

Long-running reasoning tasks should use asynchronous jobs rather than blocking API requests.

---

# **32\. Dependencies**

### **Internal**

* Loyalty & Rewards  
* Behavior Intelligence SDK  
* Ads Layer Manager  
* Event Pipeline  
* Customer Graph  
* Analytics  
* Authentication  
* Governance

### **External**

* LLM provider  
* Embedding model  
* Cloud infrastructure  
* Connected business systems

The Growth Brain should communicate with other modules through stable APIs and events.

---

# **33\. Module Success Metrics**

| Metric | MVP Target |
| ----- | ----- |
| AI Response Accuracy | \>90% |
| Recommendation Acceptance | \>60% |
| Recommendation Explainability | 100% |
| Confidence Score Availability | 100% |
| Hallucination Rate | \<2% |
| AI Query Response Time | \<5 seconds for standard queries |
| Customer Profile Freshness | \<5 minutes |
| Prediction Pipeline Success | \>99% |
| Autonomous Action Policy Violations | 0 |

---

# **34\. MVP Definition of Done**

The AI Growth Brain & Customer Intelligence module is considered MVP-complete when:

* Natural-language business queries are supported.  
* AI can retrieve authorized business context.  
* Customer profiles are generated.  
* Customer Graph integration is operational.  
* Dynamic segmentation is operational.  
* LTV prediction is available.  
* Churn prediction is available.  
* Purchase propensity is available.  
* AI recommendations contain evidence and confidence scores.  
* Progressive Abstraction is supported.  
* Manual, Approval, and Autonomous modes are operational.  
* Business policies restrict autonomous execution.  
* AI actions can invoke Ads, SDK-derived insights, and Loyalty workflows.  
* All AI recommendations and actions are auditable.  
* Model and recommendation versions are tracked.  
* AI failures produce transparent responses.  
* Monitoring and governance systems are operational.

---

# **35\. Module Summary**

The AI Growth Brain & Customer Intelligence module is the **central intelligence layer of GrowthOS**.

Modules 1–3 collect and execute growth-related activity:

**Loyalty → Retention**

**Behavior SDK → Conversion**

**Ads → Acquisition**

Module 4 connects them.

It understands the business objective, retrieves relevant data, reasons across the customer and business graph, identifies opportunities, recommends actions, enforces organizational policies, and optionally executes those actions through the appropriate GrowthOS module.

The key architectural principle is:

> **AI should reason across the system, but never bypass deterministic policies, permissions, or execution boundaries.**

[image1]: <data:image/png;base64,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RoxIzQM6CwGuTvpgUr3yyitl7UuXLg3tRx99dGoZoL1uvfXW+P/YLtUnn3yS6luPyy+/PJk9e3aqvS1OOeWUZM6cOcl7770XHoufL1OnTg19vvnmm4p9Yqrbb7891Y6uLau0bcV9DjrooLCtLViwIMz362irBx98MLnyyitT7d727duTbdu2JR9//HHy1FNPpeYDnYUAVycLcPGO4pprrim1EeDQLKr77rsv1d4Wjz32WPLDDz+k2tvj6quvLnsfZGnUhyq6JpVGZ236nHPOCW133XVXqu8RRxzRkG1t5cqVdQWyRtwX0AgEuDpZgNObXMPnalMtX748/BsHuL322iu54IILwoemvjX26dMntb4zzjgj/HvkkUcm//rXv5JRo0al+siUKVPCTuWBBx5IjjnmmNR80aGEWbNmJeeee26YPv7441N9ZMKECckTTzyRnHzyyUmPHj1S8/UcR/3vfRx11FHJk08+GUZufD90LlWlAGfbkf522t4GDhxYNl/bpfq88cYbydq1a8Nt49clkydPDqMa1b6QNCLAHXvssWE7FY2k+PnSs2fPMBJ56aWXhmn10/P0/QYMGJDccccdyfXXX5+5Xdd6jWLnnXdeWNfMmTOTPfbYIzVf6nmN0DGqOMDJa6+9lrlN1Qpw2rfef//9Ifwdfvjhqfn2fli9enWyZMmS0vR+++1X6qPtytpVdnvMmDGp9dl+9sYbb8zc9+vzQ8v27ds36d27d/Lwww+Hbc7mjx49Ojn00EOTm2++ubTtav+vbdKvC10bAa5OFuAUuN55553QpjrkkEPCv7Yz1xtW9cUXXyQzZsxIHn/88TCtnX68PpXmvfrqq8n8+fPDtP9wUv33v/8NH2J33313GLb/ec2asj6///576Ldw4cJk3rx5yaoffgjTcZ/u3buHthUrVoR1bdq0KUwPGjSorN/7778fdpI6n2Tr1q3hQ1jr104m7ofOpaoU4FQfffRR8txzzyVvvvlmmN59991L86dPnx6+AHz99dfJxo0bw20Tr0dfTFTvvvtucs8994Tb+nLi708aEeDmzp2bvPTSS6FP1iHU3XbbLczTKQqPPPJI2B51W4evrI9t16p//OMfybPPPhtu++1aVe01EoVDld4j+vAVVdynLa8ROkblA5ztJ33fagFOwW3Dhg0hcOtLrpW2L+tj7wft62wUTuIv1epv7Sq7rf1pfH+qX375JbntttuSF154IUyffvrpZX3Gjx8f2k888cTwr7ZJ3a8+LzT/7bffDu0KbaotW7aEkKf3wOLFi1PPEV0XAa5OFuB0Wx8i+ib3wQcfhGmVBTi90TW6EC+rcyV+/PHHsjbVb7/9VprWOl988cWyPtrhxNNDhgwpPYZ4PQpkNq1RFt9H53WobHRC6/n+++9DeIz7KcB99dVXYYdno4wKpL169Srrh86lqhbgPv/887Lpae5cIal1CFUVb0caRVD5ftKIAGdUWQHu2muvLVte26aVtdl2fe+995basrZrVa3X6OWXXw5fkLp161ZqO+uss1Lrqfc1QseofIDTPjTr9a4W4HQEJB5J/ctf/hL6/vWvf0317eghVPvyHo/wan+sLwVxPwtw+ly48MILS+32JV8BTueQ2n3ZgIH66kuYv190XQS4OsUBTvXll1+WDv2oqh1O2X///UvLGlU8UqAhdIW4nXfeObW8X07D67qtIXqVApnN1xV9WfflQ6W1x9P2IVnpECx2DFW1ABdPa2evDwDfr1qA04eWPhh0yNKv248KS2cEOJX/kNUHYbxOVT3btZ/Oeo1U++yzT2pdpq2vETpG9dBDD4XD4rfcckspvP3pT39K9a0W4LLovaDDpb69owFOI8Q6AhK36fQW398CnN8Gjdo14qbb+sKgUXTd1qk5fl3o2ghwdYoD3E033VT2RlLFAU6HPbMqXp+f1rlmKoU93+bLzlPT4U4/spe17moV91OAi0cq0BpU9QY4HUbXB5HvVy3ArVu3Lt4kykqHoHz/zgpw/lCoPtTidVYrv654Ous18n28tr5G6BjVZ599lixbtiwEI51CEo+OxqoFOB09sNNM4tJhSd+3owFOX8B1Woxv9/0twNk5y54CnF2s8dNPP4VRQ93Wlwe/LnRtBLg6xQHOU1mA0/kxGjaPP3w0pO6X9dM+wO26665hepdddkktZwHumWeeCYc74/lZ61bVGtkTOwfOt2PHUjUzwGnUQNutb6+kswLc8OHDy9p0UU28TlU927V/HFmvke/jtfU1Qseo/CHUSqoFOJVG8uI2bUfNCHBa59NPP51q9/0twNl+3FOAu/POO8NtAhyqIcDVqd4Ap7rooovK5uvD1y/rp32Au/jii1N9bDl740+aNClMX3LJJaX5tnPwy/iLKLIQ4FqTqqMBTstrJMK3iz7gdIK0Lsjx87JkbWOezkur1UdUWQFOoxm60MGmdShq8+bNZetU1bNd+8eR9RqpRo4cmVrWtPU1Qseo6g1w9mXXt9t64un+/fuHQ+FZAU77P10M5ts9v06jK739F2qd7uL7E+DQKAS4OtUb4PQjp/qgsRCnN6l2GH5ZP+0DnJ07oZ/80PROO+1Uuno0fuNb6XJ2XSGrDz5VvG6d06aynyHR1Xsa3fA7GwJc69COXyfRi0pXbOr2uHHjyvr5v3VWOBH9vVU6/0sfeP5wlJV+kkPTuvK42hVvKv28h85Jig/7G/1Egg476qKYAw88MLOPrScrwA0dOjTM03PW8ipdga2yPrZdx1eCZm3X8TKS9RrZVaVxQNMPu/r1qOp9jdB+qnoDnPXXz2xoO9O5YnH7okWLwm0dTlVVCnA610x18MEHp94f/r58m9hV0fa/Qti0//F3AhwahQBXp3oDnH4/zcr+lwb9lyt+WT/tA5z1UWk969evTz799NMwHb/x7bwgK534rfKP0cKfzs/Tzssq7kOAax31/k8Mqng6K5zEfeOK59nPZqjs5zp8n5g/J8zPl8suu6xiH40G2rlJ2h5t+oYbbij1sRE3lX4CROcFxT8jIrZd6/2h8zet4j5+Ous10qkKVmv+CIo6yd0v19bXCO2nakuA0/lyVvE+7Pnnnw9t+hkdbWf62+vnObICnAU8Kx3h8H1E5duM/QqAzt3TFwmV/gu6uA8BDo1CgGsCffMaPHhwCG5+XltpREHh0F/95sXnAlV6k2sdOnFWITPrByYBbRf64NL26+ftaDo/SR+Mvl10JbZ+9LSj27WW1+9/VbsSu5VfI6Ttueee4QeadRTDz2sGjXDr/toSQIH2IMDlnL/IQYej4t+qAorADpeeffbZqXkA0BUR4HIuq/QN0PcD8saXDvH7PgDQVRHgAAAAcoYABwAAkDMEOAAAgJwhwAEAAOQMAQ4AACBnCHAAAAA5Q4ADAADIGQIcAABAzhDgCkL/rY/KtwM7wvz589ke0TLYP6KICHAFwQ4KrYQAh1bC/hFFRIArCHZQaCUEOLQS9o8oIgJcQbCDQishwKGVsH9EERHgCoIdFFoJAQ6thP0jiogAVxDsoNBKCHBoJewfUUQEuIJgB4VWQoBDK2H/iCIiwBUEOyi0EgIcWgn7RxQRAa4g2EGhlRDg0ErYP6KICHAFwQ4KrYQAh1bC/hFFRIArCHZQaCUEOLQS9o8oIgJcQbCDQishwKGVsH9EERHgCoIdFFoJAQ6thP0jiogAVxDsoNBKCHBoJewfUUQEuIJgB4VWQoBDK2H/iCIiwBUEOyi0EgIcWgn7RxQRAa4g2EGhlRDg0ErYP6KICHAFwQ4KrYQAh1bC/hFFRIArCHZQaCUEOLQS9o8oIgJcQfTr1y+ZNm1aqh3YEcaPH8/2iJbB/hFFRIADAADIGQIcAABAzhDgAAAAcoYABwAAkDMEOAAAgJwhwAEAAOQMAQ4AACBnCHAAAAA5Q4ADAADIGQIcAABAzhDgAAAAcoYABwAAkDMEuJw69NBDk0cffbSqOXPmpJYDmsVvf95FF12UWgZoFr/9eewfkXcEuByrVSNHjkwtAzTLihUr/CZYVr4/0EyTJk3ym2BZsX9E3hHgcqzaDoqdEzpb9+7d/WZYqsWLF6f6A81WrXxfIG8IcDlW7QPT9wU6Q6XiCwV2hEqjwosWLUr1BfKGAJdzWTsodk7YUSqNCvt+QGeo9CXX9wPyiACXc9pB+RDn+wCdydeIESNSfYDO4vePfMFFURDgCiD+lrlw4cLUfKAz+VE4Px/oTOwfUVQEuIKwb5m+HdgRrIYPH56aB3Q29o8oIgJcQehbJt8u0SpsFM63AzsC+0cUEQEOAAAgZwhwAAAAOUOAAwAAyBkCHAAAQM4Q4AAAAHKGAAcAAJAzBDgAAICcIcABAADkDAEOAAAgZwhwAAAAOUOAAwAAyBkCHAAAQM4Q4AAAAHKGAAcAAJAzBLgWMGzYsFRbe2g9u+22W6q9rfbdd9+GPSagM2i7Z5tFqxg0aBDbI5quSwW4zZs3J6pvv/02NW9H2WmnncJj8u3toTr++ONT7eaZZ55JtWW57bbbGvaY0Hx33313+HtZ/fjjj8n++++f6ldkY8eOZZvNgVNPPbVsW1VNnTo16dmzZ6pvverdrzXCgw8+mFx55ZWpdm/JkiXhufl2oJG6VIBTvf/++132jdVVn3eRzZs3L/xde/fuXWpbunRpMnjw4FRfYEezAGfT48ePD9Md2Td1ZNm2WrlyZfLUU0+l2oEdocsEOPuGPuqYY8K/++23X6qPOe+888Kb9JJLLknNk1NOOSW54447kl122SVMx6Nee++9d5gfH8pUP7X59Wg54+eZgw8+OLn//vvDB/WNN96YdO/evWy+1h2vZ4899kit44wzzghUdluOPPLIio+n2mM6+eSTkyeeeCK8Tn6eDr9q3bo9efLk5J577kkmTJiQ6ofGUGnb9u3eqFGjkn/+859hBMH/3Xv06BH+ZgcddFDSt2/fsL35bT/+u3q+feeddw6jFLo/bQO+v+h9Ysvpvp588slkxIgRqX7Tpk4tbftZz7Pebdaev39eYs9ft/Vv1vNHY/gAJ2+88UZoO/TQQ8va+/Tpk1x33bVhX+P3IUcffXTF/Zq/T9HyWo/2Xfp7x/Ns27fbDz30ULjvuI+CpuatXr06jK7ZffnPkcMPP7yu7VHPddasWWH00e/T7XHoX71X//Wvf4Xt1/cBukyA++qrr5Lnnnsu3P7kk0+SV155JdVHb2LVihUrkptvvjn5+OOPw5s17rNhw4ZwKFY7+W3btiVffPFF2Q7p7LPPDtNDhgwptel8iLiPeemll4KseXLfffeFeQpBf/vb35IFCxak+h544IFl68naaSiMispuZwVUW4+ev78fs3HjxmTr1q0hwOpQne9nz1+lHeFPP/0Ubt96662pdaFjhg4dmnr9s3zzzTeh38yZM8PfRPXee++V5u+1116h7dFHHw0jDNbHb/tZ96W/6/bt20vT+qKieuGFF8I2snz58szlbORF77Gf16xJFi1aFKZnzJhRdn9a3rb93377LXWOp22zGnXMuh+Jn/+nn34abnfr1q00357/unXrwodlpeePjssKcK+99lpoO+KII0pt2v+qFOxvueWWZNWqVWXb2fTp0yvu1+J1KxyptE/Ttrpp06YwrX2y9VFp27e/v20j8Xo0X+v+/fffS6Nw4oPV9ddfH7bHtWvXptYR35/qkUceKR1qPeCAA1J9Hn/88eTVV19N5s+fX1rGrwtdW5cJcKoBAwaE2+PGjct8M6g0QhG3xd+ONELgl9O3+ritLQFOqp0Dp/LfPKtRZQW4eL5vy1LpHLis84xUeg1s2p5/3EcfwL4NHadv77VeV40k+D4agVBZiLEAow8n66MTsP1y+vBTCLJpC5AXX3xxqU3lR9KWLVuWvPPOO2VtFuA0IhK3m6z7ryZr25Ss57/mj8CoD3T//Pv161fq09b7R318gDvppJPCtH+tVX4UTAFeXwr8Ov2yMQWpF198sazttNNOK1tGpW0//vurLrvsstT66j2EWukcOLXrfbTnnnuW2vT4tmzZUtZPpS/uNv3yyy9nrg9dW5cIcDpc4zd+lR+69n28uXPnhhG4uK1Xr15lyzUywGnnoze71hWPGFSiamaAe/rpp8PjidvmzJkTRiLttcwKcDqs4NvQcfowq/W6XnrppZl9VHZI0gKMLobwfeLpM888s6xNFwPF0zqcr9KoiY1Q6D3z+uuvp9ZlAS5ui9n76q677qpr268U4LKe/6RJk0Kbf/5+2aw2dEzWRQzx+Zvy5z//ObTbdqRtSDQau379+tQ6Vb4tnqeLHOL1aD8WL6Py2/7PP/9c9sXUdDTAqXRYOG7TYVjfV6X3gE3rlASVTmXw60TX1SUCnA4VZr1BjjvuuFSbXzamUQS9gX17vFwjA5zOMbP69ddfw/C87xNTNTPA/fvf/049fwsRdg5JVoCr9vzRflnbtXfnnXdm9lFddNFF4bYFGI3o+T7xtK4UjNusbFrn61SreF21ApzoUL3Ktn2dD+r7mEoBLuv5n3DCCaHNP3+/bFYbOsYC3IUXXpjcdNNN4cufRkPjc8lsZLlS+XVmtcXzKlXcx2/7OvXjscceS62vEQFOzz1u0zmjvq+fvvzyy0NbV7u6HNV1iQCn87aySufFxf1UftmY3pTff/99qj1eLivA6XaldVcLcGb48OHhnA8rP9+omhngNJKic1HiNp2zpNIop6YJcJ2nntdVH5JZfVR2EYoFmL/+9a+pPlnL6bCXnVukEVibd8ghh2Quk6WeACf6cIu3/UqHXCsFuKznbyM8/vn7ZbPa0DH+EKpY2XQ9X0z88r4tnqdtyLf7Pn7bb2aA06hw3KYRSN/XTxPgkKVLBDiVnf9m7NwL32/kyJGp5U1WsLEPA5s+6qijwnR8NdQ111yTWs7UE+Bi1fqqmhngsj4MV/3wQ/gGbdMEuM6lyjpXx4wePTrztVdZ6G5LgFNg18ne+nDTlxl/eFPlT03IUm+Ai/3nP/8JfLtUCnBZz1+H1FT++ftls9rQMVkBTlcYq2xkqtLfo5JqfVWVroSO+/htv1KA089QLVy4MNXuVQpwugDu3XffLWu74oorUn39NAEOWQof4OxnQ3y7qPr371+a1kmjKo0kaFrz3nrrrdQyesPptl0p5dev0qifbutkVZ035/uYagFOV+jFPwsye/bsin1FVSvA6TDwrrvuGj54dd++j1QKcLYOXYGr2xoNUWl9Np8A17muvvrq8Nqef/75YVpX8umwVPw7cKq33367NO2vMm5LgLN2lf85EtEHlw592k/siAKmruKL+9UKcOecc04yZcqU0rRt+/7KaVMpwInKnv/AgQPD9DF/7BdsfqXAkNWGjskKcGIj+Tb9yy+/hPPQ4i8D2i9dcMEFqWVV8X4tnqf9ocr+3lqfjmjE5zKr/LZfKcDZaLAO5/v7ilUKcPZLB/riq2ldVa267rrryvr5ZQlwyFL4APfZZ5+lTrw3Kl3yHbedddZZod3K/37bPvvsU5qny9/txO24jz6w7H99+PzzzzMDjC6Jr1TWx0YKrLRDiz8YpVr5c/y089IHmZ1bFB/+isOor3gdGu7XFVNW/gdjCXCdT6O+uorOSh+G/uc2dPK3lX7+JZ7X1gBn265vNzpJOy6N1Okxxn1qBTj9TpZ+XsRK274/B3TMmDGl+b78th8/f12MEc8jwHWeSgFOVBMnTixN6yc94vroo48yT+L3+zU/X9uSvtRYqV/85UDlt/1KAU503q/9PJIuiInnVap4IEDbpg7FWmX9xJIqnibAIUvhA1xn8G82AACAZiLANQABDgAAdCYCXAMQ4AAAQGciwAEAAOQMAQ4AACBnCHAAAAA5Q4ADAADIGQIcAABAzhDgAAAAcoYABwAAkDMEOAAAgJwhwAEAAOQMAQ4AACBnCHAAAAA5Q4ADAADIGQIcAABAzhDgAAAAcoYABwAAkDMEOAAAgJwhwAEAAOQMAQ4AACBnCHAAAAA58/8BchilsWzx/LEAAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,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9p4S14YNG3rkc/YVt1fT1f7tQoADmo8Ah0JRFTXA/fjjj9nq1auzNWvWlCbXzZs3J/3RNUUMcDt37szWrVtX+pw3btyY9Gu1rVu3OnF7NUXajiECHNB8BDgUiqqoAW7x4sVl7atWrXLtkyZNSp6D+jUzwA0dOjTr169f0t4VqnVfflnWpgD36aefZnvuuWfSv0iatR2bjQAHNB8BDoWishLgZsyY4drvu+++svYpU6ZkX3/9tVvmq9K5SWr//PPPy/quXLnSnRcW9nv55ZfL+vzxj3/M+vbtW1rep08f175jxw737/bt27Pjjjuu1P+LL75w/X72s5+5x3rPvg4++ODS13//+9/dusLXfuKJJ0rLVU8++WTWv3//sj6+Zs+eHfTMsgEDBiTf81tvvVVavmvXrqYGONX555+ftHeFKg5wCoaqDz/8sKx9n332yd0+8TpFn2lcX331VdLvm2++KesTL/fi7XjppZfm9t9tt92ybdu2lfqqVqxYkfRrJQIc0HwEOBSKykqAu+mmm1z7NddcU9auyVSlifx3v/udOxSntgsvvDBZt6/XXnstu+eee7JXX33VPT7ppJNKfQYOHOja3n777ezee+91IUK1bNmyUh8f4ObOnZs9++yz7uvvv/8+u//++93XKvXzAU57lDSJ+36333579sEHH7jH48ePL63XhzuFBYU+BTyVQmbe96HSe3jsscfc17feemtZPwUe1RtvvJHdeeedLsC89957ri3s1yhVKwKcb48Paa5du9a1a/vcfffdpe2Tt6duy5YtbtmSJUvc9n7uuefc47jfwoULs5deeskty1sufjuq/Hb04y7sp5+lv/3tb65de4z1eeh7UI0cOTJZb6sQ4IDmI8ChUFQWAtzo0aNdmyrsq2Dy2WefudAVtiskxX0VyDSZau9O/Jp+G2g9Os8u3mOiE+tVfm+ZD3B+efjeLr/88tLXPsAdeeSR7rFCoyb+8Hnz5893XytEqmbNmlX22g888IBrV4jIez3vuuuuc20+KOy1115uz2T8veQ9t1GqVga48H1W2z4//PBD2fbRdg6fW4/49UJ529G/n7DN782Lnz9t2rTc9lYhwAHNR4BDoaiKGuAUtjSx+5PbdVhKk3XYV3XLLbck63jmmWeSCVP14IMPJn1DOsSq+vWvf13W7g+BDh8+3D2uFuDOO++80tc+wA0Z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g1XhBqu2WRhn3MjXPm7kixABrgYCnG0WJlZhYrXNwjgjwNlHgEOIAFcDAc42CxOrMLHaZmGcEeDsI8AhRICroegBbs8998yuuOKKbNSoUcky0TK56KKLsn333TdZHjviiCOyefPmZS+88EI2d+7cbOjQoUkfSyxMrFLkiXXw4MHZH/7wh+y1115zYyM+12vAgAGlcXbeeee5c63idYjO31GfI488Mlk2aNAgt+zyyy9PlllgYZw1K8Cde+652aWXXpq0VzJt2rTszjvvzB555JFsxIgRZcv8mIif402dOjV3+cSJE3PbvUMOOaTqcvnFL35RGreVnHHGGdn06dPd13379k3WIVqm9xm3twIBDiECXA1FD3APP/ywe48bN27Mdt9992S5aufOndm6devc177vhRdeWNZvt912Ky1//PHHXXj7xz/+4R7H67TEwsQqRd3ON9ww2703TRx33XVX9vLLL5fGie+jyVL1/fffZ99++21p+cqVK8vWdfHFF7v2ePJ/4403XPusa69NXt8KC+OsWQHuvffey3788cekPab/VH799dfZrl27sqVLl2YvPP+8e309Dvupbr311uT5GnOqn/70p2Xt+++/v1uH6toKY+bMM8+s+b0uW7YsW79+fYlq8+bNZW1PPfWU+0/y6tWrs02bNiXr0H9mar1OMxHgECLA1aAqcoD7/PPPs8WLF7v3eeKJJybLVeu+/NJ9PWbMmOz22293bfEvnauuusq1aQ9L2G55UhULE6vEn0cRHHPMMdn27duz5cuXl7WfffbZ2YoVK0qPfYBbuHChezxhwoTsueeec23hHpe8AKfJ0Vf8+pZYGGftDnB//etf3euFe1U3bNjg2hTCfJvG0g8//OCu5A2fX2lcXHLJJa5dwf/1119Plks9AS6mOuecc5J20V7EvPVpr/SOHTuS9lYhwCFEgKtBVdQAp/+1qvwkqP8lxn1UPsB5d9xxh2tXaPNt2nvy6KOPJs+3zsLEKqq4rae98sordb2vOMB5S5YscXtK/CHXOMD5vb7aixyv0xoL46zdAc5X2LbXXntlW7duzT788MOkr44U+Mf6T4LqlltuSdar11YNHz7c/RsfTZBmBzhRUFu0aFHp8fvvv++eU8+pKc1CgEOIAFeDqqgBzpe+9ocU8vrEAU4++ugj94vUP1Yflc5JiftaZmFilbzPrqcpkKkuu+yyZFmoUoAbMmSIa3/11Vfd4zDA3Xvvve5rTUjx+iyyMM56IsDlHXbU+ZTx+1BQU+l3rT8aUClMqbQnz3/93XffJX1aEeAU1FRvvvmmO89TpRAX92slAhxCBLgaVBYCnA5D+K/jPnkBTocewv7+XDqd93HQQQcl/a2yMLFK3mfX03RBgmrbtm3JhQuhSgGuT58+rv3jjz92j8MA52uPPfZI1meRhXHWEwFu7dq1SbsCSPw+tGdOfd99993SYdb4eeLH1IIFC0qvkde3FQHO91HdeOON7t+801ZaiQCHEAGuBlURA9w+++zj3ps//HTCCSe4xzo/JOynygtwv//9792ysO2xxx4r7cnzNWPGjOS5lliYWCX+LIpCE6bOTwrrnnvuKQtelQKc+NLXPsCptmzZ4v6Nx6tVFsZZOwOc/lqASuepxct8gI/bxVelw+q6kEa/o/w5dP/85z9z19WqAHfSSSeV3mNP/EUEAhxCBLgaVEUMcH7viH5R6bEmVB1K+Mtf/lLWT5UX4P785z+7ZXG7fjH6k499xX0ssTCxSpG3sw4XKZx9+X+H2VXhhQ2NBLhDDz00++abb3IPf1lkYZy1M8D5w+e6+jRepm1V6X0onOlKZt1WJl4mOvVDr+8f+6ukdcFN2K9VAU6e/7+raeP2diDAIUSAq0FVtACn24Xo3JKNGzZkd999d4nOzYh/sajyAtzbb7+d9M2j8ucwWWRhYpV6Poui8HtptXdOjysFOH+e0DvvvOMexxcxiEqfUfwa1lgYZ+0McKLK+92jPbiV3ofOyw2vcI6pdI9K/ztP69LFDzr0GvZrZYC74YYburzuZiHAIUSAq0FVtAD34IMPuvf10ksvuXsrhVR+YhVV/Ev0lFNOce3a0xavO6YrEcOLHayxMLGKKm4rqt/85jfu/Y4fP949rhTg/NXOs2fPdo/zApzfG2PhM6rGwjjriQCX93q6ArXSrTeqBTjdUFoV/86Lz+cVAhx6AwJcDaqiBbg1a9ZU/AWi0n24wsdxgPM3Y/UTcDX6ZRrfkNUSCxOrVPo8i+j+++9379cf5qoU4LSHWCek9+/f3z3OC3DhDaTj17HEwjgrQoDTBVKqF198Mekv1QKczseN1yf6SyBxOwEOvQEBrgZV0QKcr7hddE5ReI8llf7yws9//nP3p2w+/fRT16bzmcLn6dwSXcSgk3T1WJOuv5z/uOOOS17HCgsTq1T6PHuSvzJZY0dBS236k0G+fD8f4HRC+QUXXJA9+eSTpQsfwj8/lBfgxJ/HpMP6eX9NxAIL46yZAU5XJutebbGTTz651M8fKdDNbnV7IgV+X5U+50oBTuNI96qMD5V6Kv2JL//YB7j4/Xnx8/06CHCwhABXg6pIAe6AAw5w7ynv6i7xV3jNmjXLPfalq/50E8rbbrsteY4ouIV/bsuX/uZg3NcSCxOrqOK2nqZJN/zLHb70tyHDw/Q+wKn0n4X58+e7UBavr1KAk6OPPtotUzCIl1lgYZw1M8BVqnhvvcaJxoQvHe6s9veVKwU4/58J/x/MmI4y6LxgHwx9gKtU8fNFRYCDJQS4GlRFCnCtpL0suru59qKMHTvWnXMS97HGwsQqPTUh1EP/adBeC/3x72qTb29mYZw1K8A14rDDDqvrlA1UR4BDiABXQ28KcJ3IwsQqPTWxojksjLOeDHBoDgIcQgS4GghwtlmYWIWJ1TYL44wAZx8BDiECXA0EONssTKzCxGqbhXFGgLOPAIcQAa4GApxtFiZWYWK1zcI4I8DZR4BDiAAHAABgDAEOAADAGAIcAACAMQQ4AAAAYwhwAAAAxhDgAAAAjCHAAQAAGEOAq2HSpEnZwIEDk3bYcOCBB2ajR49O2otG4yxugx0Wxlm/fv0YZ8aNHDkyGzZsWNKO3okAVwM38rXNwg1WhRus2mZhnHEjX/u4kS9CBLgaCHC2WZhYhYnVNgvjjABnHwEOIQJcDQQ42yxMrMLEapuFcUaAs48AhxABrgYCnG0WJlZhYrXNwjgjwNlHgEOIAFcDAc42CxOrMLHaZmGcEeDsI8AhRICrgQBnm4WJVZhYbbMwzghw9hHgECLA1UCAs83CxCpMrLZZGGcEOPsIcAgR4GogwNlmYWIVJlbbLIwzApx9BDiECHA1EOBsszCxChOrbRbGGQHOPgIcQgS4GghwtlmYWIWJ1TYL44wAZx8BDiECXA0EONssTKzCxGqbhXFGgLOPAIcQAa4GApxtFiZWYWK1zcI4I8DZR4BDiABXAwHONgsTqzCx2mZhnBHg7CPAIUSAq4EAZ5uFiVWYWG2zMM4IcPYR4BAiwNVAgLPNwsQqTKy2WRhnBDj7CHAIEeBqIMDZZmFiFSZW2yyMMwKcfQQ4hAhwNRDgbLMwsQoTq20WxhkBzj4CHEIEuBoIcLZZmFiFidU2C+OMAGcfAQ4hAlwNBDjbLEyswsRqm4VxRoCzjwCHEAGuBgKcbRYmVmFitc3COCPA2UeAQ4gAVwMBzjYLE6swsdpmYZwR4OwjwCFEgKth1qxZ2bBhw5J22DBmzJjs/PPPT9qLRuMsboMdFsbZ4MGDGWfGTZ06NZs4cWLSjt6JAAcAAGAMAQ4AAMAYAhwAAIAxBDgAAABjCHAAAADGEOAAAACMIcDVMGnSpGzgwIFJO2w48MADs9GjRyftRaNxFrfBDgvjrF+/fowz40aOHMltrVBCgKuBG/naZuEGq8INVm2zMM64ka993MgXIQJcDQQ42yxMrMLEapuFcUaAs48AhxABrgYCnG0WJlZhYrXNwjgjwNlHgEOIAFdDbw1wY8eOdedbxO3WWJhYpacn1t122y079dRTs+HDhyfLUHv7WBhnvTnA6fdZ3GYRAQ4hAlwNzQxwAwYMcOuz8EtU9eabbybt1liYWKXSmLjlllvcsilTppS1z5w507Wfe+65yXMasfvuu7v16fXiZT3phBNOyJ5++unsgAMOSJa1U63tY2GcNSvA5dXLL7+c9Ouq/fbbz33WcXt3KXyr4naLCHAIEeBqUDUrwD355JPZihUrsk2bNmW/+93vkuVoPgsTq1SaYHp7gLvooovc+zrssMOSZe1Ua/tYGGfNDHDh47lz57q2b7/9NunbFbq6Ml43yhHgECLA1aBqVoD75ptvsttvvz175plnXJCLl6P5LEysUmniIsAR4JqlVQFOnnjiidz2riDA1UaAQ4gAV4OqWQFOpYlg6NChVX9R9enTJ/vxxx9dH1+vvvpq0m/dunWl5WvXrs1+8pOfuK/j14zb5Ouvv87mz59f1vb888+X+quqHUL1pYk1rOuvv76sn4JHWOvXr3fnEsXraxULE6uo4jbpSoD78MMPsxf+9zPU4cawzjzzzGS9Phj5GjJkiPs3L6D4ydmX9iT3798/6ac2Vd++fbOlS5eWPSfs9+ijj5YtU2mvdNinWq1evbqs78YNG+Iu2bx585L357fPmjVryvp2d/uIhXHWygCX97tH9tlnn/9swKA0fuL1Vauwrz77uJYtW5a8rug/zGHFy6UrPzNFQIBDiABXg6oZAS7+5anSOXFxv+uuu84tU5gK29955x13Lod//Prrr2dbtmwpvbdzzjkn2759e9lr+NeJ2yQvwMXPqyfAff/992XtF198cenrXbt2uT77779/qe2f//yna2vXzZEtTKyiitukqwFO9fHHH5fabrjhBtc269prS2177723a9OkG76+Kj60/9xzz2Vbt24ta9u5c6frG7aJD3D63O+///5S+4gRI0pfK9zFz9UkH76/UD174PQzs++++5a1qa6++uqyNr99DjnkkFKb3z5hv40bN7q2eraPZ2Gcxb+DGpW3jocffjhp19hRXXDBBaU2/Z7S+LnxxhuTddSzB+6BBx4oe6ybJ+v3oEJY3Nerdg5cvT8zRUGAQ4gAV4OqGQFOv7DCXyIq/TKL+3333XduWRjWRHvu/NfHHXec63PHHXeU9fnzn/9c9hr+deI2aVaAi4NF3Oezzz4ra9PeR4W+dv0SsjCxSt5nJI0EuLCvD0yLFi0qtWliil/vjTfecG1hQDnppJNc26xZs8r6ahJVKXiF7T7A3X333WXtIV0NGL92NfUEuDw6RSHeM+O3T9iWFyh9hW152ydkYZy1KsDdc889LrTHe0bztqNo/Pzwww9Jez0BLs99993nXj9u9+oJcLV+ZoqCAIcQAa4GVXcDnHbP6xfMgw8+WGrTIVHt4g+DmfiK1xFauHBhbp+99toraa+0vmYFuLjdO/30091yTXwLFixw71meeuqpbOXKlS6oxs9pBQsTq1Tall0NcDp0Ga9D9e9//7v0WF/rcwn7HHPMMa5fGFCWL1/u2nTIS5+h/xw1sWk8x8HOB7j49UN+jN555511/empegPcoEGDsptvvtmdXyqrVq1KQkK17RM/rmf7hCyMs2YGuLD0s3zKKafk9tOh8XDs6Odf40cV9683wJ111lnuVA2tR5/1W2+9VfV5tQJcpTER/swUBQEOIQJcDaruBrhLL73UrSc89+uaa65xbSeeeGJZX5WCXbyOkCYKVdzunx8/jtuk1QHu2v/by1Ot4ue0goWJVSptj64GuBdffDFZh0rnSOprTWY6JBrfrkF/y1MVBpTNmze7tkoV/odE6glwsmPHjtI6Fi9eXDWc1RPg/B6duHRKQdiv2vbxX/vJvp7tE7IwzpoZ4PS5yOOPP+4e6zPN61et4v71BLhf//rX0Vr+W3Ffr1aAqzQm/M9MkRDgECLA1aDqboCLL0gI65NPPinrq9I5HfE6Qv5wTtzunx8/jttE/zNuZYDzofXkk09OlrWThYlVKm1LH4RPO+20snad3xW3+xOy43WowslI/0F44YUXyvrovDBVGFDWffllxfeVp94AJ3vssUc2bty4bMmSJe45lZ5XK8BpfKl0K4uwXXsN8wJcpe0TP65n+4QsjLNmBrjwsS7w0F447VmP+2nvWPz8SmoFOD++dA5n2H7JJZdUfV6tAFdpTBDgUHQEuBpU3Q1wvuppz2uL3Xbbba6PzoUL2/1hy7DNn1MXtmniVLUywPmr9vQ/9HhZO1mYWKXSttReW9WvfvWrsnYdglSFJ+TXOxnlXZigw4+qMKD4+3uFFyFU05UAF3r77bcrPm/q1KluWaU76esK2fg8S9F/mroT4OrZPiEL46xVAU78TcrDU0JUeXvmKvHriNs9/QzkLdf5jnntHgEOnYoAV4OqOwFOtwRR6RdFvMzvmQvbdO6OSgEobA+viNOfuNI5SI888khZH/0iitenq6tU4UUROh9F1coA5/tUOrl48ODBSVsrWJhYpdK21PmTmgRfe+21snZ/8nX4udY7GWmvXfx6/tYaYUDRn41SkKn3ZO56ApxOEI/bFMAqPU/nyam0RzdeJprMNMbi8aTqToCL2/K2T8jCOGtlgPPtM2bMKD3W2KnUt9Jf1qjUX/R7OF6uC8F8xf09Ahw6FQGuBlV3ApyuyFPl3fvMHwaLJyd/GbvO69GJ5P52HOFkffjhh7s21T/+8Q/3r84nUoXrUvDbtm2ba1eY06Smw1J558Dp9TyVXtc/ju9D5ytsi+nwlj8Mp8Mr7777bul54S/6VrIwsUq1bemDkUqHvn3FJ9p3ZTLy98jSffkUEP1tIOKA0q9fv9LrffXVV6WwpYpfp54Ad95557k+uoeh/oPgq9qfYoor77QDlUKWv5XOQw891HCAmzBhQmn7aMxW2z6ehXHW6gCnba6aPn26e6yxE95DUBcL+N9l+qzi54v/XRVW/Noq/Rzo6II+U3+6Rryu+PdZ+Nj3qTYm4p+ZIiDAIUSAq0HVnQDXHWPGjHH3UKr2R+UV0DQp+sd5v8jk2GOPrbqeVtJeyGnTpmXnn3++Oxk8Xt5KFiZWqfS5hbQ3SnscmvU5ai+IPpe8vWIx3bdPwUYXU+y5557J8q7Qf0R01aJC/KhRo5LljdDf0dTPSnz7ne7Q9tFFRvVsHwvjrFkBrhEaPwp2eg/dHT86BUSfdT2fS6chwCFEgKuhJwNcI3rqF3RRWZhYhc/NNgvjrCcDHJqDAIcQAa4GApxtFiZW4XOzzcI4I8DZR4BDiABXg7UA9+mnnyZtvZmFiVWYWG2zMM4IcPYR4BAiwNVgLcChnIWJVZhYbbMwzghw9hHgECLA1aA/F6QbTMbtsEEXgujiibi9aOI/SwVbLIwz3WqFcWab7os4ceLEpB29EwEOAADAGAIcAACAMQQ4AAAAYwhwAAAAxhDgAAAAjCHAAQAAGEOAAwAAMIYAVwM38rXNwg1WhRus2mZhnHEjX/u4kS9CBLgaCHC2WZhYhYnVNgvjjABnHwEOIQJcDQQ42yxMrMLEapuFcUaAs48AhxABrgYCnG0WJlZhYrXNwjgjwNlHgEOIAFcDAc42CxOrMLHaZmGcEeDsI8AhRICrgQBnm4WJVZhYbbMwzghw9hHgECLA1UCAs83CxCpMrLZZGGcEOPsIcAgR4GogwNlmYWIVJlbbLIwzApx9BDiECHA1EOBsszCxChOrbRbGGQHOPgIcQgS4GghwtlmYWIWJ1TYL44wAZx8BDiECXA0EONssTKzCxGqbhXFGgLOPAIcQAa6GvNq8eXPc1O1av3593GS26t0+27ZujZtaUkWfWCWv6t0+nTR2WlHt2j5FH2c+wMXVru3Tjira755WFAEOHgGuhvHjxydOO+20pK27pkyZkrTlOfvss5O2PMcff3zSlkd7F+t97Z/+9KdJW556t88555yTtHWHvue87XPkkUcmn2vRxO9Z6t0+9X5+9Y4JqXed9fabNm1a0tYu9b7HereP+uWts+jjrF+/fsl7lrzvJU/ez1aeerdjb/jdk6fe71nbJ26ToUOHJp8teicCHAAAgDEEOAAAAGMIcAAAAMYQ4AAAAIwhwAEAABhDgAMAADCGAAcAAGAMAQ4AAMAYAhwAAIAxBDgAAABjCHAAAADGEOAAAACMIcABAAAYQ4ADAAAwhgAHAABgDAEOAADAGAIcEs8++2w2Z86cpB1opo0bNmSTJ09O2oFmYpyhUxHgkCDAoR2YWNEOjDN0KgIcEgQ4tAMTK9qBcYZORYBDggCHdmBiRTswztCpCHBIEODQDkysaAfGGToVAQ4JAhzagYkV7cA4Q6ciwCFBgEM7MLGiHRhn6FQEOCQIcGgHJla0A+MMnYoAhwQBDu3AxIp2YJyhUxHgkCDAoR2YWNEOjDN0KgIcEgQ4tAMTK9qBcYZORYBDggCHdmBiRTswztCpCHBIEODQDkysaAfGGToVAQ4JAhzagYkV7cA4Q6ciwCFBgEM7MLGiHRhn6FQEOCQIcGgHJla0A+MMnYoAhwQBDu3AxIp2YJyhUxHgkCDAoR2YWNEOjDN0KgIcEgQ4tAMTK9qBcYZORYBDggCHdmBiRTswztCpCHBIEODQDkysaAfGGToVAQ4JAhzagYkV7cA4Q6ciwAEAABhDgAMAADCGAAcAAGAMAQ4AAMAYAhwAAIAxBDgAAABjCHAAAADGEOCQGDlyZDZs2LCkHWim8ePHZwMHDkzagWZinKFTEeCQ4Ea+aAdusIp2YJyhUxHgkCDAoR2YWNEOjDN0KgIcEgQ4tAMTK9qBcYZORYBDggCHdmBiRTswztCpCHBIEODQDkysaAfGGToVAQ4JAhzagYkV7cA4Q6ciwCFBgEM7MLGiHRhn6FQEOCQIcGgHJla0A+MMnYoAhwQBDu3AxIp2YJyhUxHgkCDAoR2YWNEOjDN0KgIcEgpwc+fOzYYPH15mxIgRSVueUaNGJW15xo4dm7R117hx45K2PPW+xyOPPDJpyzNmzJi6t0+96t0+o0ePTtq6q97tU28/bZ+4bdOmTdn06dOT9mazun3y1Lu+rqh3+9T7s1Uv/WzV+/3U+7OVtz6NMwIcOhEBDgkFuO7U5s2b46bc2rZ1a9xEBVXv9lm/fn3cRAXVSdun3p+trlRv2D4EOHQiAhyAHsGhLQBoHAEOQI8gwAFA4whwAHoEAQ4AGkeAA9AjCHAA0DgCHIAeQYADgMYR4AD0CAIcADSOAAegRxDgAKBxBDgAPYIABwCNI8AB6BEEOABoHAEOAADAGAIcAACAMQQ4AAAAYwhwAAAAxhDgAAAAjCHAAQAAGEOAAwAAMIYABwAAYAwBDgAAwBgCHAAAgDEEOAAAAGMIcAAAAMYQ4AAAAIwhwAEAABhDgAPQcn379s0effTRusTPBQCkCHAA2qKe2rhhQ/I8AECKAAegLebNmxfntbJSeOvfv3/yPABAigAHoG2qhbi999476Q8AyEeAA9A2w4cPj3NbqeK+AIDKCHAA2mrHjh1xdstmz56d9AMAVEaAA9BW8WHUDRs2cPgUALqIAAeg7cIivAFA1xHgALSd3wunvW/xMgBAbQQ4AG2nixl0Ltz111+fLAMA1EaAA9AjFOLiNgBAfQhwAAAAxhDgAAAAjCHAAQAAGEOAAwAAMIYABwAAYAwBDgAAwBgCHAAAgDEEOAAAAGMIcAAAAMYQ4AAAAIwhwAEAABhDgAMAADCGAAcAAGAMAQ4AAMAYAhwAAIAxBDgAaIKxY8c6cTsAtAIBDr3ewIEDs1dffTWLK+7XCieccEL29NNPZwcccECyDLVNnDAh/thczZ8/P+nbar7idgBoBQIcerU99tgjd+I977zzkr6tcNFFF7nXPuyww5JlqM0HuHvvvbfUNmjQINe2YsWKpD8AdAoCHHq1Sy+91E32t9xyS7KsHXpzgFPQ0t7PuL0r8gKcvPbaa659yJAhyXMAoBMQ4NCrqeo53Hbuuee6vmHbyJEjXZtCWNj+6KOPZjt37nTLfG3atCnr169fqc/1119ftjys1atXJ6//8ssvl/X54x//mPXt27e0vE+fPq59x44d7t/t27dnxx13XKn/F198Uba+ffbZp7TM15NPPpm8rmhP1uLFi93XYel7ivt2hb4nfR9xe1dUCnD6DFThOWkffvhh9sLzzyfrUMVtJ510Uun79HXTTTcl/WbOnBl3S/r4sTN69OioZ5YNGDAg6T9lypSyPuvXr0/6SKVxFvcbOnRoWR9fcT8AthDg0KupTjzxxKQ9Vm+AU6hS6by2sO+sa68tC3BePXvgbr311rLX3n333d3jsM0HOP84XK6AGi7zyy+44ILS43POOceFgRtvvDF5fQW4Tz75JNuyZUvZuXpxaOqqZga45cuXZ/fcc4/7XpctW+bajjjiiLK+9Qa4OXPmuLajjz66rP3MM89MnhuvJ16X+LETLtN2XLt2bbZhw4ayvrt27XL99t9//1LbP//5Txfiwr2V1cZZ+Hjy5Mmu35VXXlnWfsghh5Q9BmAPAQ69mkpBLG6P1RvgtMdHpUAUryNPrQCnSXvz5s3J+Vya+FUKbnpcLcBdfvnlZcv83qX4tR544IHshx9+cHvnwna9tmrp0qXJc7qjmQEurrvuuivpW2+A83s74361+Irb/dhRsAzbr7vuuqS/6rPPPitr83vQFCx9W73jzL/GfvvtlywDYBsBDr2a6sADD0zaY/UGuL322su1bd261R0y8wGrkloB7rLLLnPLx48fX9Y+ffp0164wpsfVAtzUqVPLlmlvlQ61LViwwFm4cGH21FNPZYsWLXL9Zs2aVfZaCnA//vhj8t66asmSJaX3VamezwlY1VQ6hPr555+773Hw4MGltnoD3OzZs13b22+/ne27775J/0p8xe1+7Jx66qll7aNGjSrrf/rpp7vHb7zxRulz8Z+N6rvvviv1jcdZ/JqeP4z+5ZdfJnvhANhGgEOvphozZkzSHqs3wIk/D0317bff5h6W9GoFuDvuuMMtP/jgg8va/aGxX/7yl+5xtQCn4KDSoVc91h69avXggw+WvZYC3Mcff5y8t65qZ4DzYSjca1VvgNPhSb/XUYc0P/jgg+znP/958ryYr7jdj514nPnx4x9fe+21pXVUqvD54TjTOYqVxtncuXNL/RRsdeFOGGwB2ESAQ6+muuKKK5L2WF6A8yelxwHOGzduXPab3/ymNHnq5PS4T60Ad/PNN7vlhx9+eFm7Dyj+PLauBLh1X36ZvfXWW8lrVRJexNBMzTyEGgc4USms+sf1BrjQ2Wef7d6jSoeQd9ttt6RPuJ68dYUXMYTtcYDzV0SffPLJyTqq0TgLw3G83NMFE/4/BKrwPDsA9hDg0Kv5G/jWOg/u2GOPTSZHfyVppQAXUumQXNzuD29WuoP/pEmT3PJwT5Lo5HWVv6igKwFOe2S09yZ+rUosBjh/ocdHH31UanvppZey999/v6zfnnvuWdpO1Zx22mmun/6Nl3m+4vZ6A5xueaJ6/PHHk3XUK+/1Y7qYRnsWddFHvAyAHQQ49Go+AGgPRrwspL0V8eSoqwhV8VWo8XO110al85niZX4vnva+xMtEQWTVqlXZunXrytq3bdtW9n66EuCGDx9e1jeU9xchLAY43ddPpXPJfJteS7dXCfv5vV5hW95neMkll7h+I0aMSJZ5vuL2egOcX4fCVbwO3XA6POyZ9x79OAvb8vodeuihrl+lMQfABgIcej2d8+VLhxf9rRzifr50Baj66K81qMIA59tUb775pjt5XKWwUunwm79K1Jdu2REu93uT/PlYvsI9KF0JcPLEE0+U+ujQoP+e16xZk7y/VgW4Cf8bvuLzwrqq0lWoqviiAR9wFOJ0Tp9q3rx57t+wn/baqXSBgK4cVX/VxIkTk9fXVbuer7BNfboS4HT4VGNQtXLlyuzdd98trXfGjBmlfvE486VxFq7v4Ycfdu26RYw+W10I4Sv+XgDYQoAD/o+u7LvwwgurnoOkv12q86Li9pCCgu5BpglXh0i13rhPI7Tn7KyzznK3lYiXNUq3KdEVrUcddZQ7nBgv7zQKurr1hsJjvCx2/PHHu/Ggw9jxslbT+5w2bVp2/vnnV7xKOhxnuqK12jjTKQBnnHGGG9u1rowGYAMBDgAAwBgCHAAAgDEEOAAAAGMIcAAAAMYQ4AAAAIwhwAEAABhDgAMAADCGAAcAAGAMAQ4AAMAYAhwAAIAxBDgAAABjCHAAAADGEOAAAACMIcABAAAYQ4ADAAAwhgAHAABgDAEO6BBxff/999mxxx6b9GvE008/nV111VVJe6uceeaZ7nuYPXt2sgwAQIADOobq008/dXzt2LEj69u3b9K3q1QLFixI2luFAAcA1RHggA6hGjFiRFnb0qVLs507d2ZHHHFE0r8rCHAAUCwEOKBD5AU4375r166ytq1bt7p2X9u2bcuuvPLKsj5btmwp6xNX2HfZsmXuNcL66quvkvdSr64EuI0bNpS9rmrevHllfd58803X3qdPn+T5r7zyilvHnnvuWWrbZ599ojVmWf/+/ZPnyooVK7LFixdnDzzwQFn/TZs2JX0BoFkIcECHUFUKcKq47a9//Wv2+9//Pnv44Ydz+zz66KNur5uo1q5dW3oc743z9fzzz2e33npr9thjj7nHF198cfJ+6tGVAKdS2FRoU4h66623XNuAAQNKfWbMmOHaTj311OT52kP54IMPlh4ffPDB7ntV3Xfffdndd9/tvl65cmVZyPN8gFPpkPULL7yQ/fDDD+5x3BcAmoUAB3QIVb0BLjZw4EC3B01hJV7m1xGHtlqmTp3qnjdlypRkWS1dCXB5FKq0VzBsmzt3rtvzGPeNt42vvH4KZnG7Xku12267JcsAoFUIcECHUHUlwF122WXZnDlzsmeeecbRIT8dToz7+XXUE+CuvvrqbOHChW59Lzz/vHveb37zm6RfLV0NcIMGDcpuvvnm0veyatWq3LAVbwftgYz7qbQt/J5GfT9PPfVU6RBxvE4FuB9//DFpB4BWIsABHUJVb4DToc680qHA+Pl+HdUC3EknnZQtX748Wtt/6qabbkr619KVAKfDpv6QZVjbt29P+qqOOuoo97UOh27cuDGbP39+0qdaxetUgPv444+TdgBoJQIc0CFU9QQ47XWLL2qQL774ouEAp/rmm2/K2g499FDX3soAd/LJJ7t+Ojwatj/55JO5AU7n9X399dfZ7rvvnv3lL39xz437qHQeXdxeiT8HLm4HgFYiwAEdQhUHOJ3bpgrDlcJGHFB0rziFukpBRFUpwCkMqRQMw/ZTTjnFtbcywP32t791Fw7069evrH3JkiW5AW7ChAluvdOmTXPLVXEf1erVq5P2SghwAHoCAQ7oEKowwOmkel2duW7durKA869//St77733yp77/vvvu+dXCiIq3SA4bheFP1V4Jaf4W5W0MsD5vYmDBw8ua1flBbhwmUrn6cXL/fuO2+WAAw5I2ghwAHoCAQ7oEHmlsBb30+01fCl8KADNnDmzahDxt9UIK1yuvWAq3U9OhyhVumWHqjsBrlKdffbZpb6+1qxZUwpmDz30UMUApwsSVP5QarxcYfeJJ55wfXQvO90M2V/AoNeI+1fbbgDQKgQ4oEP4Uph66aWXsnvvvbfirS10tamvL7/80rVVCyK6sa32dvlwpgqX6yKGjz76yLUr7Ohr3fhW1eoAd//995cC5ObNm7NHHnnE3b+tUoDTbU1U6hMvC+kwaliLFi1y7yvuV227AUCrEOAA9Crai6aK2wHAEgIcgF5Bh3T94dOuXKQAAEVEgAPQK/jDrJ9//nk2fPjwZDkAWEKAAwAAMIYABwAAYAwBDgAAwBgCHAAAgDEEOAAAAGMIcAAAAMYQ4AAAAIwhwAEAABhDgAMAADCGAAcAAGAMAQ4AAMAYAhwAAIAxBDgAAABj/j/3WouCfGQ6MAAAAABJRU5ErkJggg==>