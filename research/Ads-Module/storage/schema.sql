-- SQLite / PostgreSQL DDL for GrowthOS Ads Module
-- Strictly NO emojis in code, docstrings, or logs.

CREATE TABLE IF NOT EXISTS ads_account_connections (
    workspace_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'google_ads',
    account_name TEXT NOT NULL DEFAULT 'Main Ad Account',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    currency TEXT NOT NULL DEFAULT 'INR',
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    login_customer_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (workspace_id, account_id)
);

CREATE TABLE IF NOT EXISTS ads_campaigns_daily (
    workspace_id TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'google_ads',
    account_id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    campaign_name TEXT NOT NULL,
    date TEXT NOT NULL,
    spend_paise INTEGER NOT NULL,
    spend_inr REAL NOT NULL,
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    conversions REAL NOT NULL DEFAULT 0.0,
    conversion_value_paise INTEGER NOT NULL DEFAULT 0,
    ctr REAL NOT NULL DEFAULT 0.0,
    cpc_paise INTEGER NOT NULL DEFAULT 0,
    cpa_paise INTEGER NOT NULL DEFAULT 0,
    roas REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL DEFAULT 'INR',
    timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    synced_at TEXT NOT NULL,
    PRIMARY KEY (workspace_id, platform, account_id, campaign_id, date)
);

CREATE INDEX IF NOT EXISTS idx_ads_campaigns_lookup 
ON ads_campaigns_daily (workspace_id, date);

CREATE INDEX IF NOT EXISTS idx_ads_campaign_id 
ON ads_campaigns_daily (campaign_id, date);

CREATE TABLE IF NOT EXISTS ads_campaign_plans (
    plan_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DRAFT',
    plan_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ads_plans_workspace
ON ads_campaign_plans (workspace_id, status);
