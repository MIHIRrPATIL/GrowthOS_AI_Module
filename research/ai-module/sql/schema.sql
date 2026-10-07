-- PostgreSQL DDL for GrowthOS Ingestion, Storage, and Identity Resolution
-- Enforces strict multi-tenant isolation, immutable telemetry, and reversible identity links.

-- 1. Raw Telemetry Events Table
CREATE TABLE IF NOT EXISTS events (
    tenant_id VARCHAR(64) NOT NULL,
    event_id VARCHAR(64) NOT NULL,
    schema_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
    project_id VARCHAR(64) NOT NULL,
    source_module VARCHAR(64) NOT NULL,
    event_name VARCHAR(128) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    anonymous_id VARCHAR(64) NOT NULL,
    customer_id VARCHAR(64) NULL,
    idempotency_key VARCHAR(128) NULL,
    page JSONB NOT NULL DEFAULT '{}'::jsonb,
    utm JSONB NOT NULL DEFAULT '{}'::jsonb,
    device JSONB NOT NULL DEFAULT '{}'::jsonb,
    network JSONB NOT NULL DEFAULT '{}'::jsonb,
    consent JSONB NOT NULL DEFAULT '{}'::jsonb,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_events PRIMARY KEY (tenant_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_events_tenant_occurred 
    ON events (tenant_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_events_tenant_name_occurred 
    ON events (tenant_id, event_name, occurred_at);

CREATE INDEX IF NOT EXISTS idx_events_tenant_customer 
    ON events (tenant_id, customer_id, occurred_at) 
    WHERE customer_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_events_tenant_anonymous 
    ON events (tenant_id, anonymous_id, occurred_at);

CREATE INDEX IF NOT EXISTS idx_events_tenant_session 
    ON events (tenant_id, session_id, occurred_at);


-- 2. Reversible Identity Links Table
CREATE TABLE IF NOT EXISTS identity_links (
    link_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    source_type VARCHAR(32) NOT NULL,       -- 'anonymous_id', 'device_id', 'cookie_id'
    source_id VARCHAR(128) NOT NULL,        -- e.g. 'anon_99bf21a0'
    target_type VARCHAR(32) NOT NULL,       -- 'customer_id', 'phone', 'email'
    target_id VARCHAR(128) NOT NULL,        -- e.g. 'CUST-48291'
    link_reason VARCHAR(64) NOT NULL,       -- 'login', 'checkout_phone_match', 'magic_link'
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    evidence_event_id VARCHAR(64) NULL,     -- references event_id that created the link
    status VARCHAR(32) NOT NULL DEFAULT 'active', -- 'active', 'reversed', 'superseded'
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reversed_at TIMESTAMPTZ NULL,
    reversed_by VARCHAR(64) NULL,
    reversal_reason TEXT NULL,
    CONSTRAINT pk_identity_links PRIMARY KEY (tenant_id, link_id)
);

CREATE INDEX IF NOT EXISTS idx_links_tenant_source 
    ON identity_links (tenant_id, source_type, source_id, status);

CREATE INDEX IF NOT EXISTS idx_links_tenant_target 
    ON identity_links (tenant_id, target_type, target_id, status);

CREATE INDEX IF NOT EXISTS idx_links_tenant_evidence 
    ON identity_links (tenant_id, evidence_event_id);


-- 3. Identity Nodes (Canonical Lookup Cache)
CREATE TABLE IF NOT EXISTS identity_nodes (
    tenant_id VARCHAR(64) NOT NULL,
    identifier_type VARCHAR(32) NOT NULL,   -- 'anonymous_id', 'customer_id', 'phone', 'email'
    identifier_value VARCHAR(128) NOT NULL,
    canonical_customer_id VARCHAR(128) NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    last_resolved_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_identity_nodes PRIMARY KEY (tenant_id, identifier_type, identifier_value)
);

CREATE INDEX IF NOT EXISTS idx_nodes_tenant_canonical 
    ON identity_nodes (tenant_id, canonical_customer_id);


-- 4. Merchant Policy Rules & Guardrails
CREATE TABLE IF NOT EXISTS policy_rules (
    tenant_id VARCHAR(64) NOT NULL,
    rule_id VARCHAR(64) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(128) NOT NULL DEFAULT 'Standard Merchant Guardrails',
    max_discount_value_paise BIGINT NOT NULL DEFAULT 15000, -- INR 150.00
    max_discount_pct NUMERIC(5, 2) NOT NULL DEFAULT 25.00,
    max_daily_budget_shift_pct NUMERIC(5, 2) NOT NULL DEFAULT 15.00,
    max_daily_discount_budget_paise BIGINT NOT NULL DEFAULT 5000000, -- INR 50,000.00
    contact_cooldown_hours INTEGER NOT NULL DEFAULT 48,
    max_incentives_per_customer_30d INTEGER NOT NULL DEFAULT 1,
    autonomous_confidence_threshold NUMERIC(4, 3) NOT NULL DEFAULT 0.850,
    autonomous_action_allowlist JSONB NOT NULL DEFAULT '["flag_ui_friction_bug","request_dense_telemetry"]'::jsonb,
    emergency_kill_switch_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pk_policy_rules PRIMARY KEY (tenant_id, rule_id)
);

-- 5. Action Plans Table with Versioned State Machine
CREATE TABLE IF NOT EXISTS action_plans (
    tenant_id VARCHAR(64) NOT NULL,
    plan_id VARCHAR(64) NOT NULL,
    signal_dedupe_key VARCHAR(256) NOT NULL,
    customer_id VARCHAR(128),
    anonymous_id VARCHAR(128),
    action_type VARCHAR(64) NOT NULL,
    target_module VARCHAR(64) NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    reasoning_summary TEXT NOT NULL,
    evidence_citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    priority_score NUMERIC(4, 3) NOT NULL DEFAULT 0.000,
    calibrated_probability NUMERIC(4, 3),
    policy_check_passed BOOLEAN NOT NULL DEFAULT FALSE,
    policy_violations JSONB NOT NULL DEFAULT '[]'::jsonb,
    rule_version INTEGER NOT NULL DEFAULT 1,
    execution_mode VARCHAR(32) NOT NULL DEFAULT 'approval',
    status VARCHAR(32) NOT NULL DEFAULT 'drafted',
    version INTEGER NOT NULL DEFAULT 1,
    is_holdout BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    approved_at TIMESTAMPTZ,
    approved_by VARCHAR(128),
    dispatched_at TIMESTAMPTZ,
    execution_receipt JSONB,
    CONSTRAINT pk_action_plans PRIMARY KEY (tenant_id, plan_id)
);

CREATE INDEX IF NOT EXISTS idx_plans_tenant_status ON action_plans (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_plans_tenant_customer ON action_plans (tenant_id, customer_id);
CREATE INDEX IF NOT EXISTS idx_plans_tenant_signal ON action_plans (tenant_id, signal_dedupe_key);

-- 6. Dedicated Local Outbound Claim Table (Idempotency Barrier)
CREATE TABLE IF NOT EXISTS outbound_claims (
    tenant_id VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(256) NOT NULL,
    plan_id VARCHAR(64) NOT NULL,
    action_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'reserved',
    receipt JSONB,
    reserved_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    CONSTRAINT pk_outbound_claims PRIMARY KEY (tenant_id, idempotency_key)
);

-- 7. Dedicated Outreach Log (Cooldown & Quiet Hours)
CREATE TABLE IF NOT EXISTS outreach_log (
    log_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    recipient_type VARCHAR(32) NOT NULL,
    recipient_id VARCHAR(128) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    template_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'reserved',
    sent_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pk_outreach_log PRIMARY KEY (tenant_id, log_id)
);

CREATE INDEX IF NOT EXISTS idx_outreach_cooldown 
    ON outreach_log (tenant_id, recipient_type, recipient_id, channel, sent_at);

-- 8. Cumulative Daily Spend & Budget Ledger
CREATE TABLE IF NOT EXISTS daily_budget_ledger (
    tenant_id VARCHAR(64) NOT NULL,
    date_key VARCHAR(10) NOT NULL,
    total_discount_paise BIGINT NOT NULL DEFAULT 0,
    total_budget_shifted_paise BIGINT NOT NULL DEFAULT 0,
    action_count INTEGER NOT NULL DEFAULT 0,
    last_updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT pk_daily_budget_ledger PRIMARY KEY (tenant_id, date_key)
);

-- 9. Cryptographically Chained Append-Only Audit Ledger
CREATE TABLE IF NOT EXISTS audit_ledger (
    audit_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    plan_id VARCHAR(64) NOT NULL,
    actor VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    prev_record_hash VARCHAR(64) NOT NULL,
    record_hash VARCHAR(64) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    CONSTRAINT pk_audit_ledger PRIMARY KEY (tenant_id, audit_id)
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant_plan ON audit_ledger (tenant_id, plan_id);
CREATE INDEX IF NOT EXISTS idx_audit_tenant_timestamp ON audit_ledger (tenant_id, timestamp);

-- 10. PostgreSQL Trigger Functions Blocking UPDATE and DELETE on audit_ledger
CREATE OR REPLACE FUNCTION fn_audit_ledger_immutable()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'SECURITY ERROR: audit_ledger is strictly append-only; UPDATE and DELETE are prohibited';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_ledger_immutable ON audit_ledger;
CREATE TRIGGER trg_audit_ledger_immutable
BEFORE UPDATE OR DELETE ON audit_ledger
FOR EACH ROW
EXECUTE FUNCTION fn_audit_ledger_immutable();
