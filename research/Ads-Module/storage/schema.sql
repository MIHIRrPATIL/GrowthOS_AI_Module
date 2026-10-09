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

CREATE TABLE IF NOT EXISTS ads_clicks (
    click_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    gclid TEXT,
    utm_source TEXT,
    utm_campaign TEXT,
    utm_medium TEXT,
    utm_term TEXT,
    utm_content TEXT,
    anonymous_id TEXT NOT NULL,
    user_id TEXT,
    landing_page TEXT NOT NULL,
    clicked_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ads_clicks_anon
ON ads_clicks (workspace_id, anonymous_id, clicked_at);

CREATE INDEX IF NOT EXISTS idx_ads_clicks_user
ON ads_clicks (workspace_id, user_id, clicked_at);

CREATE INDEX IF NOT EXISTS idx_ads_clicks_gclid
ON ads_clicks (workspace_id, gclid);

CREATE TABLE IF NOT EXISTS ads_conversions (
    conversion_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    anonymous_id TEXT NOT NULL,
    user_id TEXT,
    amount_paise INTEGER NOT NULL,
    amount_inr REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    converted_at TEXT NOT NULL,
    matched_gclid TEXT,
    matched_click_id TEXT,
    attribution_type TEXT NOT NULL DEFAULT 'ORGANIC',
    conversion_action_name TEXT NOT NULL DEFAULT 'Purchases',
    uploaded_to_google INTEGER NOT NULL DEFAULT 0,
    uploaded_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_ads_conv_workspace
ON ads_conversions (workspace_id, converted_at);

CREATE INDEX IF NOT EXISTS idx_ads_conv_pending
ON ads_conversions (workspace_id, uploaded_to_google);

CREATE TABLE IF NOT EXISTS ads_optimization_proposals (
    proposal_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    proposal_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    proposal_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ads_opt_workspace
ON ads_optimization_proposals (workspace_id, status);
