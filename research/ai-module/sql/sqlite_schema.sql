-- SQLite DDL for GrowthOS local test harnesses and development
-- Identical table structure, constraints, and index semantics as PostgreSQL.

CREATE TABLE IF NOT EXISTS events (
    tenant_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    schema_version TEXT NOT NULL DEFAULT '1.0.0',
    project_id TEXT NOT NULL,
    source_module TEXT NOT NULL,
    event_name TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    session_id TEXT NOT NULL,
    anonymous_id TEXT NOT NULL,
    customer_id TEXT,
    idempotency_key TEXT,
    page TEXT NOT NULL DEFAULT '{}',
    utm TEXT NOT NULL DEFAULT '{}',
    device TEXT NOT NULL DEFAULT '{}',
    network TEXT NOT NULL DEFAULT '{}',
    consent TEXT NOT NULL DEFAULT '{}',
    properties TEXT NOT NULL DEFAULT '{}',
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (tenant_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_events_tenant_occurred 
    ON events (tenant_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_events_tenant_name_occurred 
    ON events (tenant_id, event_name, occurred_at);

CREATE INDEX IF NOT EXISTS idx_events_tenant_customer 
    ON events (tenant_id, customer_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_events_tenant_anonymous 
    ON events (tenant_id, anonymous_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_events_tenant_session 
    ON events (tenant_id, session_id, occurred_at);


CREATE TABLE IF NOT EXISTS identity_links (
    link_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    link_reason TEXT NOT NULL,
    confidence_score REAL NOT NULL DEFAULT 1.0,
    evidence_event_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    reversed_at TEXT,
    reversed_by TEXT,
    reversal_reason TEXT,
    PRIMARY KEY (tenant_id, link_id)
);

CREATE INDEX IF NOT EXISTS idx_links_tenant_source 
    ON identity_links (tenant_id, source_type, source_id, status);

CREATE INDEX IF NOT EXISTS idx_links_tenant_target 
    ON identity_links (tenant_id, target_type, target_id, status);

CREATE INDEX IF NOT EXISTS idx_links_tenant_evidence 
    ON identity_links (tenant_id, evidence_event_id);


CREATE TABLE IF NOT EXISTS identity_nodes (
    tenant_id TEXT NOT NULL,
    identifier_type TEXT NOT NULL,
    identifier_value TEXT NOT NULL,
    canonical_customer_id TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    last_resolved_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (tenant_id, identifier_type, identifier_value)
);

CREATE INDEX IF NOT EXISTS idx_nodes_tenant_canonical 
    ON identity_nodes (tenant_id, canonical_customer_id);


-- 4. Merchant Policy Rules & Guardrails
CREATE TABLE IF NOT EXISTS policy_rules (
    tenant_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    name TEXT NOT NULL DEFAULT 'Standard Merchant Guardrails',
    max_discount_value_paise INTEGER NOT NULL DEFAULT 15000, -- INR 150.00
    max_discount_pct REAL NOT NULL DEFAULT 25.0,
    max_daily_budget_shift_pct REAL NOT NULL DEFAULT 15.0,
    max_daily_discount_budget_paise INTEGER NOT NULL DEFAULT 5000000, -- INR 50,000.00
    contact_cooldown_hours INTEGER NOT NULL DEFAULT 48,
    max_incentives_per_customer_30d INTEGER NOT NULL DEFAULT 1,
    autonomous_confidence_threshold REAL NOT NULL DEFAULT 0.85,
    autonomous_action_allowlist TEXT NOT NULL DEFAULT '["flag_ui_friction_bug","request_dense_telemetry"]',
    emergency_kill_switch_active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, rule_id)
);

-- 5. Action Plans Table with Versioned State Machine
CREATE TABLE IF NOT EXISTS action_plans (
    tenant_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    signal_dedupe_key TEXT NOT NULL,
    customer_id TEXT,
    anonymous_id TEXT,
    action_type TEXT NOT NULL,
    target_module TEXT NOT NULL,
    parameters TEXT NOT NULL DEFAULT '{}',
    reasoning_summary TEXT NOT NULL,
    evidence_citations TEXT NOT NULL DEFAULT '[]',
    priority_score REAL NOT NULL DEFAULT 0.0,
    calibrated_probability REAL,
    policy_check_passed INTEGER NOT NULL DEFAULT 0,
    policy_violations TEXT NOT NULL DEFAULT '[]',
    rule_version INTEGER NOT NULL DEFAULT 1,
    execution_mode TEXT NOT NULL DEFAULT 'approval',
    status TEXT NOT NULL DEFAULT 'drafted', -- drafted, pending_approval, approved, dispatching, dispatched, rejected, failed, expired, reconciliation_needed
    version INTEGER NOT NULL DEFAULT 1,
    is_holdout INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    approved_at TEXT,
    approved_by TEXT,
    dispatched_at TEXT,
    execution_receipt TEXT,
    PRIMARY KEY (tenant_id, plan_id)
);

CREATE INDEX IF NOT EXISTS idx_plans_tenant_status ON action_plans (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_plans_tenant_customer ON action_plans (tenant_id, customer_id);
CREATE INDEX IF NOT EXISTS idx_plans_tenant_signal ON action_plans (tenant_id, signal_dedupe_key);

-- 6. Dedicated Local Outbound Claim Table (Idempotency Barrier)
CREATE TABLE IF NOT EXISTS outbound_claims (
    tenant_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'reserved', -- reserved, succeeded, failed, reconciliation_needed
    receipt TEXT,
    reserved_at TEXT NOT NULL,
    completed_at TEXT,
    PRIMARY KEY (tenant_id, idempotency_key)
);

-- 7. Dedicated Outreach Log (Cooldown & Quiet Hours)
CREATE TABLE IF NOT EXISTS outreach_log (
    log_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    recipient_type TEXT NOT NULL, -- customer_id, anonymous_id
    recipient_id TEXT NOT NULL,
    channel TEXT NOT NULL, -- whatsapp, email, sms
    template_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'reserved', -- reserved, sent, failed
    sent_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, log_id)
);

CREATE INDEX IF NOT EXISTS idx_outreach_cooldown 
    ON outreach_log (tenant_id, recipient_type, recipient_id, channel, sent_at);

-- 8. Cumulative Daily Spend & Budget Ledger
CREATE TABLE IF NOT EXISTS daily_budget_ledger (
    tenant_id TEXT NOT NULL,
    date_key TEXT NOT NULL, -- YYYY-MM-DD
    total_discount_paise INTEGER NOT NULL DEFAULT 0,
    total_budget_shifted_paise INTEGER NOT NULL DEFAULT 0,
    action_count INTEGER NOT NULL DEFAULT 0,
    last_updated_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, date_key)
);

-- 9. Cryptographically Chained Append-Only Audit Ledger
CREATE TABLE IF NOT EXISTS audit_ledger (
    audit_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    prev_record_hash TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    PRIMARY KEY (tenant_id, audit_id)
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant_plan ON audit_ledger (tenant_id, plan_id);
CREATE INDEX IF NOT EXISTS idx_audit_tenant_timestamp ON audit_ledger (tenant_id, timestamp);

-- 10. Database Triggers Blocking UPDATE and DELETE on audit_ledger
CREATE TRIGGER IF NOT EXISTS trg_audit_ledger_no_update
BEFORE UPDATE ON audit_ledger
BEGIN
    SELECT RAISE(FAIL, 'SECURITY ERROR: audit_ledger is strictly append-only; UPDATE is prohibited');
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_ledger_no_delete
BEFORE DELETE ON audit_ledger
BEGIN
    SELECT RAISE(FAIL, 'SECURITY ERROR: audit_ledger is strictly append-only; DELETE is prohibited');
END;
