"""
NLP Domain Schemas
Defines structured query classification, evidence citations, 3-tier answers,
and grounded digest explanations for GrowthOS Module 4.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from domain.metrics import TimeWindow


class QueryIntent(str, Enum):
    FUNNEL_DROP_OFF = "funnel_drop_off"
    METRIC_LOOKUP = "metric_lookup"
    PERIOD_COMPARISON = "period_comparison"
    COHORT_RETENTION = "cohort_retention"
    FRICTION_INVESTIGATION = "friction_investigation"
    ANOMALY_DIAGNOSIS = "anomaly_diagnosis"
    UNSUPPORTED = "unsupported"


class QueryClassification(BaseModel):
    """
    Structured interpretation of a merchant's natural language question.
    Strictly classified into the known metric catalog; never generates free-form SQL.
    """
    model_config = ConfigDict(extra="forbid")

    query_text: str
    intent: QueryIntent
    target_metric: Optional[str] = None
    time_window: TimeWindow
    prior_window: Optional[TimeWindow] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    vertical: str = "ecommerce_d2c"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    clarification_needed: Optional[str] = None


class EvidenceCitation(BaseModel):
    """
    Atomic grounding evidence link tying an NLP claim to computed facts.
    """
    model_config = ConfigDict(extra="forbid")

    citation_id: str
    claim_text: str
    metric_name: str
    computed_value: float
    sample_size: int
    prior_value: Optional[float] = None
    time_window: Optional[str] = None
    is_verified: bool = True
    discrepancy: Optional[str] = None


class StructuredAnswer(BaseModel):
    """
    Three-tier structured answer to a merchant query:
    1. Executive One-Liner (High-level takeaway)
    2. Analytical Breakdown (Detailed statistical comparison with sample sizes)
    3. Technical Trace (Source event lineage, session IDs, formulas)
    """
    model_config = ConfigDict(extra="forbid")

    query_text: str
    intent: QueryIntent
    executive_summary: str
    analytical_breakdown: List[str]
    technical_trace: Dict[str, Any]
    citations: List[EvidenceCitation] = Field(default_factory=list)
    unsupported_claims_dropped: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DigestExplanation(BaseModel):
    """
    Fact-grounded narrative explanation of a DigestReport.
    """
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    headline: str
    executive_summary: str
    detailed_narrative: str
    citations: List[EvidenceCitation] = Field(default_factory=list)
    unsupported_claims_dropped: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
