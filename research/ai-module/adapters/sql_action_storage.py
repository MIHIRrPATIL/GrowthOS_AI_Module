"""
SQL Action Storage Adapter for GrowthOS Module 4
Implements ActionStoragePort with SQLite local persistence and PostgreSQL parity.
Guarantees optimistic concurrency, atomic claim reservations, and daily spend tracking.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from domain.actions import ActionPlan, PolicyRule, ActionType, ExecutionMode
from ports.action_storage import ActionStoragePort


class SqlActionStorageAdapter(ActionStoragePort):
    """
    SQLite adapter for action plans, policy rules, claims, outreach logs, and daily spend.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self._conn.execute("PRAGMA journal_mode = WAL;")
        return self._conn

    def _init_db(self) -> None:
        schema_path = Path(__file__).resolve().parent.parent / "sql" / "sqlite_schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found at: {schema_path}")

        schema_sql = schema_path.read_text(encoding="utf-8")
        conn = self._get_connection()
        conn.executescript(schema_sql)
        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # -------------------------------------------------------------------------
    # Policy Rules
    # -------------------------------------------------------------------------
    def get_policy_rule(self, tenant_id: str) -> Optional[PolicyRule]:
        conn = self._get_connection()
        cur = conn.execute(
            """
            SELECT tenant_id, rule_id, version, name, max_discount_value_paise,
                   max_discount_pct, max_daily_budget_shift_pct, max_daily_discount_budget_paise,
                   contact_cooldown_hours, max_incentives_per_customer_30d,
                   autonomous_confidence_threshold, autonomous_action_allowlist,
                   emergency_kill_switch_active, created_at, updated_at
            FROM policy_rules
            WHERE tenant_id = ?
            ORDER BY version DESC LIMIT 1
            """,
            (tenant_id,)
        )
        row = cur.fetchone()
        if not row:
            return None

        allowlist = json.loads(row["autonomous_action_allowlist"]) if row["autonomous_action_allowlist"] else []
        return PolicyRule(
            tenant_id=row["tenant_id"],
            rule_id=row["rule_id"],
            version=row["version"],
            name=row["name"],
            max_discount_value_paise=row["max_discount_value_paise"],
            max_discount_pct=row["max_discount_pct"],
            max_daily_budget_shift_pct=row["max_daily_budget_shift_pct"],
            max_daily_discount_budget_paise=row["max_daily_discount_budget_paise"],
            contact_cooldown_hours=row["contact_cooldown_hours"],
            max_incentives_per_customer_30d=row["max_incentives_per_customer_30d"],
            autonomous_confidence_threshold=row["autonomous_confidence_threshold"],
            autonomous_action_allowlist=allowlist,
            emergency_kill_switch_active=bool(row["emergency_kill_switch_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def save_policy_rule(self, rule: PolicyRule) -> None:
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO policy_rules (
                tenant_id, rule_id, version, name, max_discount_value_paise,
                max_discount_pct, max_daily_budget_shift_pct, max_daily_discount_budget_paise,
                contact_cooldown_hours, max_incentives_per_customer_30d,
                autonomous_confidence_threshold, autonomous_action_allowlist,
                emergency_kill_switch_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (tenant_id, rule_id) DO UPDATE SET
                version = excluded.version,
                name = excluded.name,
                max_discount_value_paise = excluded.max_discount_value_paise,
                max_discount_pct = excluded.max_discount_pct,
                max_daily_budget_shift_pct = excluded.max_daily_budget_shift_pct,
                max_daily_discount_budget_paise = excluded.max_daily_discount_budget_paise,
                contact_cooldown_hours = excluded.contact_cooldown_hours,
                max_incentives_per_customer_30d = excluded.max_incentives_per_customer_30d,
                autonomous_confidence_threshold = excluded.autonomous_confidence_threshold,
                autonomous_action_allowlist = excluded.autonomous_action_allowlist,
                emergency_kill_switch_active = excluded.emergency_kill_switch_active,
                updated_at = excluded.updated_at
            """,
            (
                rule.tenant_id,
                rule.rule_id,
                rule.version,
                rule.name,
                rule.max_discount_value_paise,
                rule.max_discount_pct,
                rule.max_daily_budget_shift_pct,
                rule.max_daily_discount_budget_paise,
                rule.contact_cooldown_hours,
                rule.max_incentives_per_customer_30d,
                rule.autonomous_confidence_threshold,
                json.dumps(rule.autonomous_action_allowlist),
                1 if rule.emergency_kill_switch_active else 0,
                rule.created_at,
                rule.updated_at
            )
        )
        conn.commit()

    # -------------------------------------------------------------------------
    # Action Plans
    # -------------------------------------------------------------------------
    def save_plan(self, plan: ActionPlan) -> None:
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO action_plans (
                tenant_id, plan_id, signal_dedupe_key, customer_id, anonymous_id,
                action_type, target_module, parameters, reasoning_summary, evidence_citations,
                priority_score, calibrated_probability, policy_check_passed, policy_violations,
                rule_version, execution_mode, status, version, is_holdout, created_at,
                expires_at, approved_at, approved_by, dispatched_at, execution_receipt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (tenant_id, plan_id) DO UPDATE SET
                parameters = excluded.parameters,
                reasoning_summary = excluded.reasoning_summary,
                evidence_citations = excluded.evidence_citations,
                priority_score = excluded.priority_score,
                calibrated_probability = excluded.calibrated_probability,
                policy_check_passed = excluded.policy_check_passed,
                policy_violations = excluded.policy_violations,
                rule_version = excluded.rule_version,
                execution_mode = excluded.execution_mode,
                status = excluded.status,
                version = excluded.version,
                is_holdout = excluded.is_holdout,
                expires_at = excluded.expires_at,
                approved_at = excluded.approved_at,
                approved_by = excluded.approved_by,
                dispatched_at = excluded.dispatched_at,
                execution_receipt = excluded.execution_receipt
            """,
            (
                plan.tenant_id,
                plan.plan_id,
                plan.signal_dedupe_key,
                plan.customer_id,
                plan.anonymous_id,
                plan.action_type.value,
                plan.target_module,
                json.dumps(plan.parameters),
                plan.reasoning_summary,
                json.dumps(plan.evidence_citations),
                plan.priority_score,
                plan.calibrated_probability,
                1 if plan.policy_check_passed else 0,
                json.dumps(plan.policy_violations),
                plan.rule_version,
                plan.execution_mode.value,
                plan.status,
                plan.version,
                1 if plan.is_holdout else 0,
                plan.created_at,
                plan.expires_at,
                plan.approved_at,
                plan.approved_by,
                plan.dispatched_at,
                json.dumps(plan.execution_receipt) if plan.execution_receipt else None
            )
        )
        conn.commit()

    def _row_to_plan(self, row: sqlite3.Row) -> ActionPlan:
        params = json.loads(row["parameters"]) if row["parameters"] else {}
        evidence = json.loads(row["evidence_citations"]) if row["evidence_citations"] else []
        violations = json.loads(row["policy_violations"]) if row["policy_violations"] else []
        receipt = json.loads(row["execution_receipt"]) if row["execution_receipt"] else None

        return ActionPlan(
            tenant_id=row["tenant_id"],
            plan_id=row["plan_id"],
            signal_dedupe_key=row["signal_dedupe_key"],
            customer_id=row["customer_id"],
            anonymous_id=row["anonymous_id"],
            action_type=ActionType(row["action_type"]),
            target_module=row["target_module"],
            parameters=params,
            reasoning_summary=row["reasoning_summary"],
            evidence_citations=evidence,
            priority_score=row["priority_score"],
            calibrated_probability=row["calibrated_probability"],
            confidence_score=row["priority_score"],
            policy_check_passed=bool(row["policy_check_passed"]),
            policy_violations=violations,
            rule_version=row["rule_version"],
            execution_mode=ExecutionMode(row["execution_mode"]),
            status=row["status"],
            version=row["version"],
            is_holdout=bool(row["is_holdout"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            approved_at=row["approved_at"],
            approved_by=row["approved_by"],
            dispatched_at=row["dispatched_at"],
            execution_receipt=receipt
        )

    def get_plan(self, tenant_id: str, plan_id: str) -> Optional[ActionPlan]:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM action_plans WHERE tenant_id = ? AND plan_id = ?",
            (tenant_id, plan_id)
        )
        row = cur.fetchone()
        return self._row_to_plan(row) if row else None

    def get_plan_by_signal(self, tenant_id: str, signal_dedupe_key: str, action_type: str) -> Optional[ActionPlan]:
        conn = self._get_connection()
        cur = conn.execute(
            """
            SELECT * FROM action_plans 
            WHERE tenant_id = ? AND signal_dedupe_key = ? AND action_type = ?
            AND status NOT IN ('rejected', 'failed', 'expired')
            ORDER BY created_at DESC LIMIT 1
            """,
            (tenant_id, signal_dedupe_key, action_type)
        )
        row = cur.fetchone()
        return self._row_to_plan(row) if row else None

    def list_plans(
        self,
        tenant_id: str,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        limit: int = 50
    ) -> List[ActionPlan]:
        conn = self._get_connection()
        query = "SELECT * FROM action_plans WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]

        if status:
            query += " AND status = ?"
            params.append(status)
        if customer_id:
            query += " AND customer_id = ?"
            params.append(customer_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cur = conn.execute(query, params)
        return [self._row_to_plan(r) for r in cur.fetchall()]

    def update_plan_status_atomic(
        self,
        tenant_id: str,
        plan_id: str,
        expected_status: str,
        new_status: str,
        expected_version: int,
        approved_by: Optional[str] = None,
        dispatched_at: Optional[str] = None,
        execution_receipt: Optional[Dict[str, Any]] = None
    ) -> bool:
        conn = self._get_connection()
        receipt_json = json.dumps(execution_receipt) if execution_receipt else None
        now_str = datetime.now(timezone.utc).isoformat()
        approved_at = now_str if new_status == "approved" else None

        cur = conn.execute(
            """
            UPDATE action_plans
            SET status = ?,
                version = version + 1,
                approved_by = COALESCE(?, approved_by),
                approved_at = COALESCE(?, approved_at),
                dispatched_at = COALESCE(?, dispatched_at),
                execution_receipt = COALESCE(?, execution_receipt)
            WHERE tenant_id = ? AND plan_id = ? AND status = ? AND version = ?
            """,
            (
                new_status,
                approved_by,
                approved_at,
                dispatched_at,
                receipt_json,
                tenant_id,
                plan_id,
                expected_status,
                expected_version
            )
        )
        conn.commit()
        return cur.rowcount > 0

    # -------------------------------------------------------------------------
    # Outbound Claims (Idempotency Barrier)
    # -------------------------------------------------------------------------
    def reserve_outbound_claim(
        self,
        tenant_id: str,
        idempotency_key: str,
        plan_id: str,
        action_type: str,
        reserved_at: datetime
    ) -> bool:
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO outbound_claims (
                    tenant_id, idempotency_key, plan_id, action_type, status, reserved_at
                ) VALUES (?, ?, ?, ?, 'reserved', ?)
                """,
                (tenant_id, idempotency_key, plan_id, action_type, reserved_at.isoformat())
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_outbound_claim(
        self,
        tenant_id: str,
        idempotency_key: str,
        status: str,
        receipt: Optional[Dict[str, Any]] = None,
        completed_at: Optional[datetime] = None
    ) -> None:
        conn = self._get_connection()
        receipt_json = json.dumps(receipt) if receipt else None
        comp_str = completed_at.isoformat() if completed_at else None
        conn.execute(
            """
            UPDATE outbound_claims
            SET status = ?, receipt = ?, completed_at = ?
            WHERE tenant_id = ? AND idempotency_key = ?
            """,
            (status, receipt_json, comp_str, tenant_id, idempotency_key)
        )
        conn.commit()

    def get_outbound_claim(self, tenant_id: str, idempotency_key: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM outbound_claims WHERE tenant_id = ? AND idempotency_key = ?",
            (tenant_id, idempotency_key)
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "tenant_id": row["tenant_id"],
            "idempotency_key": row["idempotency_key"],
            "plan_id": row["plan_id"],
            "action_type": row["action_type"],
            "status": row["status"],
            "receipt": json.loads(row["receipt"]) if row["receipt"] else None,
            "reserved_at": row["reserved_at"],
            "completed_at": row["completed_at"]
        }

    # -------------------------------------------------------------------------
    # Dedicated Outreach Log (Cooldown & Quiet Hours)
    # -------------------------------------------------------------------------
    def record_outreach(
        self,
        tenant_id: str,
        log_id: str,
        recipient_type: str,
        recipient_id: str,
        channel: str,
        template_name: str,
        sent_at: datetime,
        status: str = "sent"
    ) -> None:
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO outreach_log (
                log_id, tenant_id, recipient_type, recipient_id, channel, template_name, status, sent_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (log_id, tenant_id, recipient_type, recipient_id, channel, template_name, status, sent_at.isoformat())
        )
        conn.commit()

    def get_last_outreach(
        self,
        tenant_id: str,
        recipient_type: str,
        recipient_id: str,
        channel: Optional[str] = None
    ) -> Optional[datetime]:
        conn = self._get_connection()
        query = """
            SELECT sent_at FROM outreach_log
            WHERE tenant_id = ? AND recipient_type = ? AND recipient_id = ? AND status IN ('sent', 'reserved')
        """
        params = [tenant_id, recipient_type, recipient_id]
        if channel:
            query += " AND channel = ?"
            params.append(channel)

        query += " ORDER BY sent_at DESC LIMIT 1"
        cur = conn.execute(query, params)
        row = cur.fetchone()
        if row and row["sent_at"]:
            dt = datetime.fromisoformat(row["sent_at"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        return None

    # -------------------------------------------------------------------------
    # Cumulative Daily Budget & Spend Ledger
    # -------------------------------------------------------------------------
    def record_daily_spend(
        self,
        tenant_id: str,
        date_key: str,
        discount_paise: int,
        budget_shifted_paise: int,
        timestamp: datetime
    ) -> None:
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO daily_budget_ledger (
                tenant_id, date_key, total_discount_paise, total_budget_shifted_paise, action_count, last_updated_at
            ) VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT (tenant_id, date_key) DO UPDATE SET
                total_discount_paise = total_discount_paise + excluded.total_discount_paise,
                total_budget_shifted_paise = total_budget_shifted_paise + excluded.total_budget_shifted_paise,
                action_count = action_count + 1,
                last_updated_at = excluded.last_updated_at
            """,
            (tenant_id, date_key, discount_paise, budget_shifted_paise, timestamp.isoformat())
        )
        conn.commit()

    def get_daily_spend(self, tenant_id: str, date_key: str) -> Dict[str, Any]:
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM daily_budget_ledger WHERE tenant_id = ? AND date_key = ?",
            (tenant_id, date_key)
        )
        row = cur.fetchone()
        if not row:
            return {
                "tenant_id": tenant_id,
                "date_key": date_key,
                "total_discount_paise": 0,
                "total_budget_shifted_paise": 0,
                "action_count": 0
            }
        return {
            "tenant_id": row["tenant_id"],
            "date_key": row["date_key"],
            "total_discount_paise": row["total_discount_paise"],
            "total_budget_shifted_paise": row["total_budget_shifted_paise"],
            "action_count": row["action_count"]
        }

    def count_customer_incentives(self, tenant_id: str, customer_id: str, since: datetime) -> int:
        conn = self._get_connection()
        cur = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM action_plans
            WHERE tenant_id = ? AND customer_id = ?
            AND action_type IN ('waive_delivery_fee', 'issue_discount_coupon')
            AND status IN ('dispatched', 'dispatching', 'approved')
            AND created_at >= ?
            """,
            (tenant_id, customer_id, since.isoformat())
        )
        row = cur.fetchone()
        return int(row["cnt"]) if row else 0
