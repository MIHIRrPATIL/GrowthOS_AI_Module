"""
Unit Tests for SqlConsentAdapter (Persistent DPDP Consent Store)
GrowthOS Module 4: AI Growth Brain

Strictly NO emojis in code, docstrings, or logs.
"""

import pytest
from datetime import datetime, timezone, timedelta

from adapters.sql_consent_adapter import SqlConsentAdapter


@pytest.fixture
def consent_adapter():
    adapter = SqlConsentAdapter(db_path=":memory:")
    yield adapter
    adapter.close()


def test_initial_consent_defaults_to_false(consent_adapter):
    consent = consent_adapter.get_consent("tenant_test", "cust_unknown")
    assert consent == {}
    assert not consent_adapter.has_consent("tenant_test", "cust_unknown", "whatsapp_marketing")
    assert not consent_adapter.has_consent("tenant_test", "cust_unknown", "email_marketing")


def test_record_and_query_consent(consent_adapter):
    consent_adapter.record_consent(
        tenant_id="tenant_dominos",
        customer_id="cust_101",
        consent_flags={
            "whatsapp_marketing": True,
            "email_marketing": False,
            "ad_tracking": True
        },
        evidence_event_id="evt_optin_999",
        notice_version="2.1"
    )

    consent = consent_adapter.get_consent("tenant_dominos", "cust_101")
    assert consent["whatsapp_marketing"] is True
    assert consent["email_marketing"] is False
    assert consent["ad_tracking"] is True

    assert consent_adapter.has_consent("tenant_dominos", "cust_101", "whatsapp_marketing") is True
    assert consent_adapter.has_consent("tenant_dominos", "cust_101", "email_marketing") is False
    assert consent_adapter.has_consent("tenant_dominos", "cust_101", "unspecified_purpose") is False


def test_consent_revocation(consent_adapter):
    tenant = "tenant_dominos"
    cust = "cust_202"

    consent_adapter.record_consent(tenant, cust, {"whatsapp_marketing": True})
    assert consent_adapter.has_consent(tenant, cust, "whatsapp_marketing") is True

    # Customer revokes consent
    consent_adapter.record_consent(tenant, cust, {"whatsapp_marketing": False})
    assert consent_adapter.has_consent(tenant, cust, "whatsapp_marketing") is False


def test_consent_audit_trail_logging(consent_adapter):
    tenant = "tenant_dominos"
    cust = "cust_303"

    consent_adapter.record_consent(
        tenant, cust,
        {"whatsapp_marketing": True},
        evidence_event_id="evt_01",
        ip_address="203.0.113.1",
        user_agent="Mozilla/5.0 Chrome/120"
    )
    consent_adapter.record_consent(
        tenant, cust,
        {"whatsapp_marketing": False},
        evidence_event_id="evt_02",
        ip_address="203.0.113.1",
        user_agent="Mozilla/5.0 Chrome/120"
    )

    trail = consent_adapter.get_audit_trail(tenant, cust)
    assert len(trail) == 2
    actions = [t["action"] for t in trail]
    assert "OPT_IN" in actions
    assert "OPT_OUT" in actions
    assert trail[0]["evidence_event_id"] in ("evt_01", "evt_02")
