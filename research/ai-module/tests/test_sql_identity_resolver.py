"""
Unit tests for SqlIdentityResolver.
Validates:
1. Reversible identity links between anonymous visitors and customers.
2. Bidirectional alias queries and canonical resolution.
3. Link reversal rollback (uncoupling identities without mutating raw event logs).
4. Strict multi-tenant isolation.
"""

import pytest
from adapters.sql_identity_resolver import SqlIdentityResolver


@pytest.fixture
def resolver():
    res = SqlIdentityResolver(db_path=":memory:")
    yield res
    res.close()


def test_link_identities_and_canonical_resolution(resolver):
    link = resolver.link_identities(
        tenant_id="ws_dominos_in",
        source_type="anonymous_id",
        source_id="anon_mumbai_01",
        target_type="customer_id",
        target_id="CUST-48291",
        link_reason="login",
        evidence_event_id="evt_login_001",
        confidence_score=1.0
    )

    assert link.status == "active"
    assert link.source_id == "anon_mumbai_01"
    assert link.target_id == "CUST-48291"
    assert link.confidence_score == 1.0

    # Idempotent call returns same active link
    link_again = resolver.link_identities(
        tenant_id="ws_dominos_in",
        source_type="anonymous_id",
        source_id="anon_mumbai_01",
        target_type="customer_id",
        target_id="CUST-48291",
        link_reason="login"
    )
    assert link_again.link_id == link.link_id

    # Canonical customer resolution
    canonical = resolver.get_canonical_customer_id("ws_dominos_in", "anon_mumbai_01")
    assert canonical == "CUST-48291"

    # Querying customer_id directly resolves to itself
    assert resolver.get_canonical_customer_id("ws_dominos_in", "CUST-48291") == "CUST-48291"


def test_multi_device_linked_identifiers(resolver):
    # Link mobile and desktop sessions to same customer
    resolver.link_identities(
        tenant_id="ws_dominos_in",
        source_type="anonymous_id",
        source_id="anon_mobile",
        target_type="customer_id",
        target_id="CUST-48291",
        link_reason="login_mobile"
    )
    resolver.link_identities(
        tenant_id="ws_dominos_in",
        source_type="anonymous_id",
        source_id="anon_desktop",
        target_type="customer_id",
        target_id="CUST-48291",
        link_reason="login_desktop"
    )

    aliases = resolver.get_linked_identifiers("ws_dominos_in", "CUST-48291")
    assert aliases == {"anon_mobile", "anon_desktop", "CUST-48291"}


def test_reversible_link_rollback(resolver):
    # 1. Establish link
    link = resolver.link_identities(
        tenant_id="ws_dominos_in",
        source_type="anonymous_id",
        source_id="anon_shared_tablet",
        target_type="customer_id",
        target_id="CUST-48291",
        link_reason="checkout_form_autofill"
    )
    assert resolver.get_canonical_customer_id("ws_dominos_in", "anon_shared_tablet") == "CUST-48291"

    # 2. Reverse link (e.g. merchant admin discovers family shared device)
    reversed_link = resolver.reverse_link(
        tenant_id="ws_dominos_in",
        link_id=link.link_id,
        reversed_by="merchant_admin",
        reversal_reason="Misattributed shared family tablet"
    )

    assert reversed_link.status == "reversed"
    assert reversed_link.reversed_by == "merchant_admin"
    assert reversed_link.reversal_reason == "Misattributed shared family tablet"
    assert reversed_link.reversed_at is not None

    # 3. Canonical resolution now uncouples anon_shared_tablet
    canonical_after = resolver.get_canonical_customer_id("ws_dominos_in", "anon_shared_tablet")
    assert canonical_after != "CUST-48291"

    # 4. Audit trail retains the reversed link for forensic tracking
    audit = resolver.get_links_for_identifier("ws_dominos_in", "anon_shared_tablet", include_reversed=True)
    assert len(audit) == 1
    assert audit[0].status == "reversed"


def test_identity_multi_tenant_isolation(resolver):
    resolver.link_identities(
        tenant_id="ws_dominos_in",
        source_type="anonymous_id",
        source_id="anon_shared_id",
        target_type="customer_id",
        target_id="CUST-DOMINOS-01",
        link_reason="login"
    )

    # In Starbucks workspace, the same anonymous_id is completely unlinked
    canonical_starbucks = resolver.get_canonical_customer_id("ws_starbucks_in", "anon_shared_id")
    assert canonical_starbucks is None
