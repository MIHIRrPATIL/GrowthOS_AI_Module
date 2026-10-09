"""
Storage Adapter for GrowthOS Ads Module
Implements SQLite storage for account connections and daily campaign performance.
Strictly NO emojis in code, docstrings, or logs.
"""

from typing import List, Optional, Dict, Any
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

from domain.models import AccountConnection, AccountStatus, AdsCampaignDaily
from domain.plans import CampaignPlan, PlanStatus
from domain.attribution import ClickRecord, ConversionRecord
from domain.optimization import OptimizationProposal, ProposalStatus


class SqlAdsStorageAdapter:
    """
    Thread-safe SQLite storage for Ads Module with WAL mode and parameterized queries.
    """

    def __init__(self, db_path: str = "ads_module.db"):
        self.db_path = db_path
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._mem_conn is not None:
            return self._mem_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
        else:
            schema_sql = """
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
            """

        with self._get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()

    # =========================================================================
    # Account Connections
    # =========================================================================

    def save_account_connection(self, connection: AccountConnection) -> None:
        sql = """
        INSERT INTO ads_account_connections (
            workspace_id, account_id, platform, account_name, status,
            currency, timezone, login_customer_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(workspace_id, account_id) DO UPDATE SET
            account_name = excluded.account_name,
            status = excluded.status,
            currency = excluded.currency,
            timezone = excluded.timezone,
            login_customer_id = excluded.login_customer_id,
            updated_at = excluded.updated_at
        """
        with self._get_connection() as conn:
            conn.execute(
                sql,
                (
                    connection.workspace_id,
                    connection.account_id,
                    connection.platform,
                    connection.account_name,
                    connection.status.value,
                    connection.currency,
                    connection.timezone,
                    connection.login_customer_id,
                    connection.created_at,
                    connection.updated_at
                )
            )
            conn.commit()

    def get_account_connection(self, workspace_id: str, account_id: str) -> Optional[AccountConnection]:
        sql = "SELECT * FROM ads_account_connections WHERE workspace_id = ? AND account_id = ?"
        with self._get_connection() as conn:
            row = conn.execute(sql, (workspace_id, account_id)).fetchone()
            if not row:
                return None
            return AccountConnection(
                workspace_id=row["workspace_id"],
                account_id=row["account_id"],
                platform=row["platform"],
                account_name=row["account_name"],
                status=AccountStatus(row["status"]),
                currency=row["currency"],
                timezone=row["timezone"],
                login_customer_id=row["login_customer_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )

    def list_account_connections(self, workspace_id: str) -> List[AccountConnection]:
        sql = "SELECT * FROM ads_account_connections WHERE workspace_id = ? ORDER BY created_at DESC"
        with self._get_connection() as conn:
            rows = conn.execute(sql, (workspace_id,)).fetchall()
            return [
                AccountConnection(
                    workspace_id=r["workspace_id"],
                    account_id=r["account_id"],
                    platform=r["platform"],
                    account_name=r["account_name"],
                    status=AccountStatus(r["status"]),
                    currency=r["currency"],
                    timezone=r["timezone"],
                    login_customer_id=r["login_customer_id"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                )
                for r in rows
            ]

    # =========================================================================
    # Daily Performance Metrics
    # =========================================================================

    def upsert_daily_metrics(self, records: List[AdsCampaignDaily]) -> int:
        if not records:
            return 0

        sql = """
        INSERT INTO ads_campaigns_daily (
            workspace_id, platform, account_id, campaign_id, campaign_name,
            date, spend_paise, spend_inr, impressions, clicks, conversions,
            conversion_value_paise, ctr, cpc_paise, cpa_paise, roas,
            currency, timezone, status, synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(workspace_id, platform, account_id, campaign_id, date) DO UPDATE SET
            campaign_name = excluded.campaign_name,
            spend_paise = excluded.spend_paise,
            spend_inr = excluded.spend_inr,
            impressions = excluded.impressions,
            clicks = excluded.clicks,
            conversions = excluded.conversions,
            conversion_value_paise = excluded.conversion_value_paise,
            ctr = excluded.ctr,
            cpc_paise = excluded.cpc_paise,
            cpa_paise = excluded.cpa_paise,
            roas = excluded.roas,
            currency = excluded.currency,
            timezone = excluded.timezone,
            status = excluded.status,
            synced_at = excluded.synced_at
        """
        rows = [
            (
                r.workspace_id,
                r.platform,
                r.account_id,
                r.campaign_id,
                r.campaign_name,
                r.date,
                r.spend_paise,
                r.spend_inr,
                r.impressions,
                r.clicks,
                r.conversions,
                r.conversion_value_paise,
                r.ctr,
                r.cpc_paise,
                r.cpa_paise,
                r.roas,
                r.currency,
                r.timezone,
                r.status,
                r.synced_at
            )
            for r in records
        ]

        with self._get_connection() as conn:
            conn.executemany(sql, rows)
            conn.commit()

        return len(records)

    def get_campaign_daily_metrics(
        self,
        campaign_id: str,
        start_date: str,
        end_date: str
    ) -> List[AdsCampaignDaily]:
        sql = """
        SELECT * FROM ads_campaigns_daily
        WHERE campaign_id = ? AND date >= ? AND date <= ?
        ORDER BY date ASC
        """
        with self._get_connection() as conn:
            rows = conn.execute(sql, (campaign_id, start_date, end_date)).fetchall()
            return [self._row_to_model(r) for r in rows]

    def get_bulk_metrics(
        self,
        workspace_id: str,
        start_date: str,
        end_date: str
    ) -> List[AdsCampaignDaily]:
        sql = """
        SELECT * FROM ads_campaigns_daily
        WHERE workspace_id = ? AND date >= ? AND date <= ?
        ORDER BY date ASC, campaign_id ASC
        """
        with self._get_connection() as conn:
            rows = conn.execute(sql, (workspace_id, start_date, end_date)).fetchall()
            return [self._row_to_model(r) for r in rows]

    def _row_to_model(self, r: sqlite3.Row) -> AdsCampaignDaily:
        return AdsCampaignDaily(
            workspace_id=r["workspace_id"],
            platform=r["platform"],
            account_id=r["account_id"],
            campaign_id=r["campaign_id"],
            campaign_name=r["campaign_name"],
            date=r["date"],
            spend_paise=r["spend_paise"],
            spend_inr=r["spend_inr"],
            impressions=r["impressions"],
            clicks=r["clicks"],
            conversions=r["conversions"],
            conversion_value_paise=r["conversion_value_paise"],
            ctr=r["ctr"],
            cpc_paise=r["cpc_paise"],
            cpa_paise=r["cpa_paise"],
            roas=r["roas"],
            currency=r["currency"],
            timezone=r["timezone"],
            status=r["status"],
            synced_at=r["synced_at"]
        )

    # =========================================================================
    # Campaign Plans (Phase 3)
    # =========================================================================

    def save_campaign_plan(self, plan: CampaignPlan) -> None:
        sql = """
        INSERT INTO ads_campaign_plans (
            plan_id, workspace_id, account_id, name, status, plan_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(plan_id) DO UPDATE SET
            name = excluded.name,
            status = excluded.status,
            plan_json = excluded.plan_json,
            updated_at = excluded.updated_at
        """
        plan_dict = plan.model_dump()
        plan_json = json.dumps(plan_dict)
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(sql, (
                plan.plan_id,
                plan.workspace_id,
                plan.account_id,
                plan.name,
                plan.status.value,
                plan_json,
                plan.created_at or now_str,
                now_str
            ))
            conn.commit()

    def get_campaign_plan(self, plan_id: str) -> Optional[CampaignPlan]:
        sql = "SELECT plan_json FROM ads_campaign_plans WHERE plan_id = ?"
        with self._get_connection() as conn:
            row = conn.execute(sql, (plan_id,)).fetchone()
            if not row:
                return None
            data = json.loads(row["plan_json"])
            return CampaignPlan.model_validate(data)

    def list_campaign_plans(
        self,
        workspace_id: str,
        status: Optional[PlanStatus] = None
    ) -> List[CampaignPlan]:
        if status:
            sql = "SELECT plan_json FROM ads_campaign_plans WHERE workspace_id = ? AND status = ? ORDER BY created_at DESC"
            params = (workspace_id, status.value)
        else:
            sql = "SELECT plan_json FROM ads_campaign_plans WHERE workspace_id = ? ORDER BY created_at DESC"
            params = (workspace_id,)

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [CampaignPlan.model_validate(json.loads(r["plan_json"])) for r in rows]

    def update_plan_status(
        self,
        plan_id: str,
        status: PlanStatus,
        validation_errors: Optional[List[str]] = None,
        validation_warnings: Optional[List[str]] = None,
        deployed_campaign_id: Optional[str] = None,
        approved_by: Optional[str] = None,
        approval_notes: Optional[str] = None
    ) -> Optional[CampaignPlan]:
        plan = self.get_campaign_plan(plan_id)
        if not plan:
            return None

        plan.status = status
        plan.updated_at = datetime.now(timezone.utc).isoformat()
        if validation_errors is not None:
            plan.validation_errors = validation_errors
        if validation_warnings is not None:
            plan.validation_warnings = validation_warnings
        if deployed_campaign_id is not None:
            plan.deployed_campaign_id = deployed_campaign_id
        if approved_by is not None:
            plan.approved_by = approved_by
        if approval_notes is not None:
            plan.approval_notes = approval_notes

        self.save_campaign_plan(plan)
        return plan

    # =========================================================================
    # Closed-Loop Attribution (Phase 4)
    # =========================================================================

    def save_click(self, click: ClickRecord) -> None:
        sql = """
        INSERT INTO ads_clicks (
            click_id, workspace_id, gclid, utm_source, utm_campaign,
            utm_medium, utm_term, utm_content, anonymous_id, user_id,
            landing_page, clicked_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(click_id) DO UPDATE SET
            user_id = COALESCE(excluded.user_id, ads_clicks.user_id)
        """
        with self._get_connection() as conn:
            conn.execute(sql, (
                click.click_id,
                click.workspace_id,
                click.gclid,
                click.utm_source,
                click.utm_campaign,
                click.utm_medium,
                click.utm_term,
                click.utm_content,
                click.anonymous_id,
                click.user_id,
                click.landing_page,
                click.clicked_at
            ))
            conn.commit()

    def get_clicks_for_visitor(
        self,
        workspace_id: str,
        anonymous_id: str,
        user_id: Optional[str] = None,
        lookback_days: int = 30
    ) -> List[ClickRecord]:
        if user_id:
            sql = """
            SELECT * FROM ads_clicks
            WHERE workspace_id = ? AND (anonymous_id = ? OR user_id = ?)
            ORDER BY clicked_at DESC
            """
            params = (workspace_id, anonymous_id, user_id)
        else:
            sql = """
            SELECT * FROM ads_clicks
            WHERE workspace_id = ? AND anonymous_id = ?
            ORDER BY clicked_at DESC
            """
            params = (workspace_id, anonymous_id)

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [
                ClickRecord(
                    click_id=r["click_id"],
                    workspace_id=r["workspace_id"],
                    gclid=r["gclid"],
                    utm_source=r["utm_source"],
                    utm_campaign=r["utm_campaign"],
                    utm_medium=r["utm_medium"],
                    utm_term=r["utm_term"],
                    utm_content=r["utm_content"],
                    anonymous_id=r["anonymous_id"],
                    user_id=r["user_id"],
                    landing_page=r["landing_page"],
                    clicked_at=r["clicked_at"]
                )
                for r in rows
            ]

    def save_conversion(self, conversion: ConversionRecord) -> None:
        sql = """
        INSERT INTO ads_conversions (
            conversion_id, workspace_id, account_id, order_id, anonymous_id,
            user_id, amount_paise, amount_inr, currency, converted_at,
            matched_gclid, matched_click_id, attribution_type,
            conversion_action_name, uploaded_to_google, uploaded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(conversion_id) DO UPDATE SET
            uploaded_to_google = excluded.uploaded_to_google,
            uploaded_at = excluded.uploaded_at
        """
        with self._get_connection() as conn:
            conn.execute(sql, (
                conversion.conversion_id,
                conversion.workspace_id,
                conversion.account_id,
                conversion.order_id,
                conversion.anonymous_id,
                conversion.user_id,
                conversion.amount_paise,
                conversion.amount_inr,
                conversion.currency,
                conversion.converted_at,
                conversion.matched_gclid,
                conversion.matched_click_id,
                conversion.attribution_type,
                conversion.conversion_action_name,
                1 if conversion.uploaded_to_google else 0,
                conversion.uploaded_at
            ))
            conn.commit()

    def get_conversion(self, conversion_id: str) -> Optional[ConversionRecord]:
        sql = "SELECT * FROM ads_conversions WHERE conversion_id = ?"
        with self._get_connection() as conn:
            r = conn.execute(sql, (conversion_id,)).fetchone()
            if not r:
                return None
            return self._conv_row_to_model(r)

    def list_conversions(self, workspace_id: str, limit: int = 100) -> List[ConversionRecord]:
        sql = "SELECT * FROM ads_conversions WHERE workspace_id = ? ORDER BY converted_at DESC LIMIT ?"
        with self._get_connection() as conn:
            rows = conn.execute(sql, (workspace_id, limit)).fetchall()
            return [self._conv_row_to_model(r) for r in rows]

    def get_pending_conversions(self, workspace_id: str) -> List[ConversionRecord]:
        sql = """
        SELECT * FROM ads_conversions
        WHERE workspace_id = ? AND uploaded_to_google = 0 AND matched_gclid IS NOT NULL
        ORDER BY converted_at ASC
        """
        with self._get_connection() as conn:
            rows = conn.execute(sql, (workspace_id,)).fetchall()
            return [self._conv_row_to_model(r) for r in rows]

    def mark_conversion_uploaded(self, conversion_id: str, uploaded_at: str) -> None:
        sql = "UPDATE ads_conversions SET uploaded_to_google = 1, uploaded_at = ? WHERE conversion_id = ?"
        with self._get_connection() as conn:
            conn.execute(sql, (uploaded_at, conversion_id))
            conn.commit()

    def get_attribution_summary(self, workspace_id: str) -> Dict[str, Any]:
        sql = """
        SELECT
            COUNT(*) as total_conversions,
            SUM(CASE WHEN attribution_type = 'DIRECT_GCLID' THEN 1 ELSE 0 END) as direct_gclid_count,
            SUM(CASE WHEN attribution_type = 'LAST_TOUCH_UTM' THEN 1 ELSE 0 END) as utm_count,
            SUM(CASE WHEN attribution_type = 'ORGANIC' THEN 1 ELSE 0 END) as organic_count,
            SUM(CASE WHEN attribution_type IN ('DIRECT_GCLID', 'LAST_TOUCH_UTM') THEN amount_paise ELSE 0 END) as attributed_paise,
            SUM(amount_paise) as total_paise,
            SUM(CASE WHEN uploaded_to_google = 1 THEN 1 ELSE 0 END) as uploaded_count,
            SUM(CASE WHEN uploaded_to_google = 0 AND matched_gclid IS NOT NULL THEN 1 ELSE 0 END) as pending_upload_count
        FROM ads_conversions
        WHERE workspace_id = ?
        """
        with self._get_connection() as conn:
            r = conn.execute(sql, (workspace_id,)).fetchone()
            tot = r["total_conversions"] or 0
            attr_paise = r["attributed_paise"] or 0
            tot_paise = r["total_paise"] or 0
            return {
                "workspace_id": workspace_id,
                "total_conversions": tot,
                "direct_gclid_conversions": r["direct_gclid_count"] or 0,
                "utm_conversions": r["utm_count"] or 0,
                "organic_conversions": r["organic_count"] or 0,
                "total_attributed_revenue_paise": attr_paise,
                "total_attributed_revenue_inr": round(attr_paise / 100.0, 2),
                "total_revenue_inr": round(tot_paise / 100.0, 2),
                "uploaded_conversions_count": r["uploaded_count"] or 0,
                "pending_upload_count": r["pending_upload_count"] or 0
            }

    def _conv_row_to_model(self, r: sqlite3.Row) -> ConversionRecord:
        return ConversionRecord(
            conversion_id=r["conversion_id"],
            workspace_id=r["workspace_id"],
            account_id=r["account_id"],
            order_id=r["order_id"],
            anonymous_id=r["anonymous_id"],
            user_id=r["user_id"],
            amount_paise=r["amount_paise"],
            amount_inr=r["amount_inr"],
            currency=r["currency"],
            converted_at=r["converted_at"],
            matched_gclid=r["matched_gclid"],
            matched_click_id=r["matched_click_id"],
            attribution_type=r["attribution_type"],
            conversion_action_name=r["conversion_action_name"],
            uploaded_to_google=bool(r["uploaded_to_google"]),
            uploaded_at=r["uploaded_at"]
        )

    # =========================================================================
    # Autonomous Optimization Proposals (Phase 5)
    # =========================================================================

    def save_proposal(self, proposal: OptimizationProposal) -> None:
        sql = """
        INSERT INTO ads_optimization_proposals (
            proposal_id, workspace_id, account_id, proposal_type, status, proposal_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(proposal_id) DO UPDATE SET
            status = excluded.status,
            proposal_json = excluded.proposal_json,
            updated_at = excluded.updated_at
        """
        prop_json = json.dumps(proposal.model_dump())
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(sql, (
                proposal.proposal_id,
                proposal.workspace_id,
                proposal.account_id,
                proposal.proposal_type.value,
                proposal.status.value,
                prop_json,
                proposal.created_at or now_str,
                now_str
            ))
            conn.commit()

    def get_proposal(self, proposal_id: str) -> Optional[OptimizationProposal]:
        sql = "SELECT proposal_json FROM ads_optimization_proposals WHERE proposal_id = ?"
        with self._get_connection() as conn:
            r = conn.execute(sql, (proposal_id,)).fetchone()
            if not r:
                return None
            return OptimizationProposal.model_validate(json.loads(r["proposal_json"]))

    def list_proposals(
        self,
        workspace_id: str,
        status: Optional[ProposalStatus] = None
    ) -> List[OptimizationProposal]:
        if status:
            sql = "SELECT proposal_json FROM ads_optimization_proposals WHERE workspace_id = ? AND status = ? ORDER BY created_at DESC"
            params = (workspace_id, status.value)
        else:
            sql = "SELECT proposal_json FROM ads_optimization_proposals WHERE workspace_id = ? ORDER BY created_at DESC"
            params = (workspace_id,)

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [OptimizationProposal.model_validate(json.loads(r["proposal_json"])) for r in rows]

    def update_proposal_status(
        self,
        proposal_id: str,
        status: ProposalStatus,
        applied_at: Optional[str] = None,
        rolled_back_at: Optional[str] = None,
        rollback_snapshot: Optional[Dict[str, Any]] = None
    ) -> Optional[OptimizationProposal]:
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            return None

        proposal.status = status
        proposal.updated_at = datetime.now(timezone.utc).isoformat()
        if applied_at is not None:
            proposal.applied_at = applied_at
        if rolled_back_at is not None:
            proposal.rolled_back_at = rolled_back_at
        if rollback_snapshot is not None:
            proposal.rollback_snapshot = rollback_snapshot

        self.save_proposal(proposal)
        return proposal
