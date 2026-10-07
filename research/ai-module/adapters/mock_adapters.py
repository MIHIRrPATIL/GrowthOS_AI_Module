"""
Mock Outbound Adapters for Zero-Dependency Testing and Execution
Records all dispatches in memory with idempotency tracking.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from ports.outbound import (
    LoyaltyPort,
    BehaviorPort,
    AdsPort,
    NotificationPort,
    AuditLedgerPort,
)
from domain.actions import AuditRecord


class MockLoyaltyAdapter(LoyaltyPort):
    """
    In-memory mock adapter for Module 1 (Loyalty & Rewards).
    """
    def __init__(self):
        self.dispatched_fee_waivers: List[Dict[str, Any]] = []
        self.dispatched_point_grants: List[Dict[str, Any]] = []
        self.dispatched_coupons: List[Dict[str, Any]] = []
        self.seen_idempotency_keys: set = set()

    def waive_delivery_fee(
        self,
        customer_id: str,
        fee_amount: float,
        points_deducted: int,
        idempotency_key: str
    ) -> Dict[str, Any]:
        if idempotency_key in self.seen_idempotency_keys:
            return {
                "status": "duplicate_skipped",
                "message": f"Action with key {idempotency_key} already processed",
                "idempotency_key": idempotency_key
            }

        self.seen_idempotency_keys.add(idempotency_key)
        receipt = {
            "action": "waive_delivery_fee",
            "customer_id": customer_id,
            "fee_amount": fee_amount,
            "points_deducted": points_deducted,
            "idempotency_key": idempotency_key,
            "status": "success",
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        self.dispatched_fee_waivers.append(receipt)
        return receipt

    def grant_bonus_points(
        self,
        customer_id: str,
        points: int,
        reason: str,
        idempotency_key: str
    ) -> Dict[str, Any]:
        if idempotency_key in self.seen_idempotency_keys:
            return {"status": "duplicate_skipped", "idempotency_key": idempotency_key}

        self.seen_idempotency_keys.add(idempotency_key)
        receipt = {
            "action": "grant_bonus_points",
            "customer_id": customer_id,
            "points": points,
            "reason": reason,
            "idempotency_key": idempotency_key,
            "status": "success",
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        self.dispatched_point_grants.append(receipt)
        return receipt

    def issue_discount_coupon(
        self,
        customer_id: str,
        coupon_code: str,
        discount_amount: float,
        idempotency_key: str
    ) -> Dict[str, Any]:
        if idempotency_key in self.seen_idempotency_keys:
            return {"status": "duplicate_skipped", "idempotency_key": idempotency_key}

        self.seen_idempotency_keys.add(idempotency_key)
        receipt = {
            "action": "issue_discount_coupon",
            "customer_id": customer_id,
            "coupon_code": coupon_code,
            "discount_amount": discount_amount,
            "idempotency_key": idempotency_key,
            "status": "success",
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        self.dispatched_coupons.append(receipt)
        return receipt


class MockBehaviorAdapter(BehaviorPort):
    """
    In-memory mock adapter for Module 2 (Behavior Intelligence).
    """
    def __init__(self):
        self.dense_telemetry_requests: List[Dict[str, Any]] = []
        self.reported_ui_friction_bugs: List[Dict[str, Any]] = []

    def request_dense_telemetry(
        self,
        component_selector: str,
        duration_minutes: int,
        sample_rate: float = 1.0
    ) -> Dict[str, Any]:
        req = {
            "component_selector": component_selector,
            "duration_minutes": duration_minutes,
            "sample_rate": sample_rate,
            "status": "active",
            "requested_at": datetime.now(timezone.utc).isoformat()
        }
        self.dense_telemetry_requests.append(req)
        return req

    def register_ui_friction_bug(
        self,
        component_selector: str,
        friction_type: str,
        session_count: int,
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        bug = {
            "bug_id": f"BUG-UX-{len(self.reported_ui_friction_bugs) + 1:04d}",
            "component_selector": component_selector,
            "friction_type": friction_type,
            "session_count": session_count,
            "evidence": evidence,
            "status": "triaged",
            "registered_at": datetime.now(timezone.utc).isoformat()
        }
        self.reported_ui_friction_bugs.append(bug)
        return bug


class MockAdsAdapter(AdsPort):
    """
    In-memory mock adapter for Module 3 (Ads Layer Manager).
    """
    def __init__(self):
        self.synced_audiences: List[Dict[str, Any]] = []
        self.budget_shifts: List[Dict[str, Any]] = []
        self.seen_idempotency_keys: set = set()

    def sync_audience_segment(
        self,
        segment_name: str,
        customer_identifiers: List[str],
        target_platform: str = "all"
    ) -> Dict[str, Any]:
        sync_result = {
            "segment_name": segment_name,
            "audience_size": len(customer_identifiers),
            "target_platform": target_platform,
            "customer_ids": customer_identifiers,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "status": "synced"
        }
        self.synced_audiences.append(sync_result)
        return sync_result

    def shift_campaign_budget(
        self,
        from_campaign_id: str,
        to_campaign_id: str,
        delta_amount_inr: float,
        idempotency_key: str
    ) -> Dict[str, Any]:
        if idempotency_key in self.seen_idempotency_keys:
            return {"status": "duplicate_skipped", "idempotency_key": idempotency_key}

        self.seen_idempotency_keys.add(idempotency_key)
        shift_record = {
            "from_campaign_id": from_campaign_id,
            "to_campaign_id": to_campaign_id,
            "delta_amount_inr": delta_amount_inr,
            "idempotency_key": idempotency_key,
            "status": "applied",
            "shifted_at": datetime.now(timezone.utc).isoformat()
        }
        self.budget_shifts.append(shift_record)
        return shift_record


class MockNotificationAdapter(NotificationPort):
    """
    In-memory mock adapter for Direct Customer Notifications (WhatsApp/Email).
    """
    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []
        self.seen_idempotency_keys: set = set()

    def send_recovery_message(
        self,
        recipient: str,
        channel: str,
        template_name: str,
        parameters: Dict[str, Any],
        idempotency_key: str
    ) -> Dict[str, Any]:
        if idempotency_key in self.seen_idempotency_keys:
            return {"status": "duplicate_skipped", "idempotency_key": idempotency_key}

        self.seen_idempotency_keys.add(idempotency_key)
        msg = {
            "message_id": f"msg_{len(self.sent_messages) + 1:05d}",
            "recipient": recipient,
            "channel": channel,
            "template_name": template_name,
            "parameters": parameters,
            "idempotency_key": idempotency_key,
            "delivered_at": datetime.now(timezone.utc).isoformat(),
            "status": "delivered"
        }
        self.sent_messages.append(msg)
        return msg


class MockAuditLedgerAdapter(AuditLedgerPort):
    """
    In-memory append-only audit ledger adapter with hash chaining.
    """
    def __init__(self):
        self.ledger: List[AuditRecord] = []

    def record_audit(self, entry: AuditRecord) -> None:
        last_hash = self.get_last_hash(entry.tenant_id)
        if entry.prev_record_hash == "GENESIS" and last_hash != "GENESIS":
            # Link to prior hash
            entry = entry.model_copy(update={"prev_record_hash": last_hash})
            entry.record_hash = entry.calculate_hash()
        elif not entry.record_hash:
            entry.record_hash = entry.calculate_hash()
        self.ledger.append(entry)

    def get_audit_trail(
        self,
        tenant_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        limit: int = 50
    ) -> List[AuditRecord]:
        results = self.ledger
        if tenant_id:
            results = [r for r in results if r.tenant_id == tenant_id]
        if plan_id:
            results = [r for r in results if r.plan_id == plan_id]
        return results[-limit:]

    def get_last_hash(self, tenant_id: str) -> str:
        tenant_entries = [r for r in self.ledger if r.tenant_id == tenant_id]
        if tenant_entries:
            return tenant_entries[-1].record_hash
        return "GENESIS"

    def verify_hash_chain(self, tenant_id: str) -> bool:
        tenant_entries = [r for r in self.ledger if r.tenant_id == tenant_id]
        if not tenant_entries:
            return True
        prev = "GENESIS"
        for r in tenant_entries:
            if r.prev_record_hash != prev:
                return False
            # Verify record_hash computation
            if r.record_hash != r.calculate_hash():
                return False
            prev = r.record_hash
        return True
