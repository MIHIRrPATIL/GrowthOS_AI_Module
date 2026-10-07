"""
Merchant Query Service
Public interface for answering merchant natural language questions with 3-tier answers
and recording auditable query trails in the append-only ledger.
"""

from typing import Optional
from datetime import datetime, timezone
import uuid

from domain.nlp import StructuredAnswer
from domain.actions import AuditRecord
from engines.nl_query_engine import NLQueryEngine
from ports.outbound import AuditLedgerPort


class MerchantQueryService:
    """
    Coordinates merchant Q&A interactions, ensuring full evidence grounding,
    auditability, and multi-tenant isolation.
    """

    def __init__(
        self,
        nl_query_engine: NLQueryEngine,
        audit_ledger: AuditLedgerPort
    ):
        self.nl_query_engine = nl_query_engine
        self.audit_ledger = audit_ledger

    def ask(
        self,
        tenant_id: str,
        merchant_id: str,
        question: str,
        vertical: str = "ecommerce_d2c",
        as_of: Optional[datetime] = None
    ) -> StructuredAnswer:
        """
        Processes question and records audit trace.
        """
        answer = self.nl_query_engine.process_query(
            tenant_id=tenant_id,
            query_text=question,
            vertical=vertical,
            as_of=as_of
        )

        # Record audit entry in append-only ledger
        self.audit_ledger.record_audit(
            AuditRecord(
                tenant_id=tenant_id,
                plan_id=f"query_{uuid.uuid4().hex[:10]}",
                actor=f"merchant:{merchant_id}",
                event_type="merchant_query_answered",
                details={
                    "query": question,
                    "intent": answer.intent.value,
                    "metric_name": answer.technical_trace.get("metric_name"),
                    "citations_count": len(answer.citations)
                }
            )
        )

        return answer
