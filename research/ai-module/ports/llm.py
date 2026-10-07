"""
LLM Port Interface (Hexagonal Architecture)
Defines abstract contracts for natural language reasoning, query classification,
digest explanations, and answer synthesis.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from domain.metrics import DigestReport, MetricResult
from domain.nlp import QueryClassification, StructuredAnswer, DigestExplanation


class LLMPort(ABC):
    """
    Port for Large Language Model integrations.
    Supports query classification, digest narration, and structured 3-tier Q&A.
    """

    @abstractmethod
    def classify_query(
        self,
        query: str,
        metric_catalog: List[Dict[str, Any]],
        vertical: str = "ecommerce_d2c",
        as_of: Optional[Any] = None
    ) -> QueryClassification:
        """
        Classifies a merchant's natural language question into a structured QueryClassification.
        Maps strictly to known metrics and time windows; never writes raw SQL.
        """
        pass

    @abstractmethod
    def explain_digest(
        self,
        report: DigestReport,
        vertical: str = "ecommerce_d2c"
    ) -> str:
        """
        Generates a draft narrative explanation from a computed DigestReport.
        Output must contain embedded fact citations for verification by EvidenceLinker.
        """
        pass

    @abstractmethod
    def synthesize_answer(
        self,
        query: str,
        classification: QueryClassification,
        metrics: List[MetricResult]
    ) -> StructuredAnswer:
        """
        Synthesizes a 3-tier structured answer (Executive, Analytical, Technical)
        grounded entirely in the provided computed MetricResult data.
        """
        pass
