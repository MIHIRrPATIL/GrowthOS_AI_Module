"""
Evidence Linker Engine
Automated anti-hallucination gate that cross-references NLP claims against computed deterministic metrics.
Prunes unsupported claims, enforces polarity consistency, binds explicit citations,
and rejects ungrounded qualitative hyperbole.

Strictly NO emojis used in logs or output.
"""

from typing import List, Dict, Any, Optional, Tuple
import re

from domain.metrics import MetricResult, DigestFlag
from domain.nlp import EvidenceCitation


class EvidenceLinker:
    """
    Deterministic validator that verifies natural language statements against ground-truth computed facts.
    Guarantees that:
    1. Every retained sentence is grounded in at least one verified metric fact.
    2. Numbers are strictly bound to the specific metric mentioned in that sentence.
    3. Directional words ("increased", "decreased") strictly match the mathematical sign of the metric delta.
    4. Ungrounded qualitative hyperbole ("alarming", "sharply", "across the board") is rejected.
    """

    # Directional indicators
    POSITIVE_WORDS = {
        "increase", "increased", "increasing", "spike", "spiked", "surge",
        "surged", "up", "rose", "rising", "higher", "climbing", "jumped"
    }
    NEGATIVE_WORDS = {
        "decrease", "decreased", "decreasing", "drop", "dropped", "drop-off",
        "decline", "declined", "down", "fell", "falling", "lower", "reduced"
    }

    # Unsupported qualitative qualifiers that must not pass without factual grounding
    UNSUPPORTED_QUALIFIERS = {
        "alarming", "alarmingly", "sharply", "across the board",
        "massive", "massively", "huge", "catastrophic", "dramatic", "dramatically"
    }

    # Semantic keyword mappings to canonical metric keys
    METRIC_KEYWORD_MAP = {
        "cart abandonment": "cart_abandonment_rate",
        "abandonment": "cart_abandonment_rate",
        "checkout step 2": "checkout_step_2_drop_off_rate",
        "step 2": "checkout_step_2_drop_off_rate",
        "step 1": "checkout_step_1_drop_off_rate",
        "checkout step 1": "checkout_step_1_drop_off_rate",
        "step 3": "checkout_step_3_drop_off_rate",
        "checkout drop off": "checkout_drop_off_rate",
        "checkout drop-off": "checkout_drop_off_rate",
        "checkout friction": "checkout_step_2_drop_off_rate",
        "friction": "checkout_step_2_drop_off_rate",
        "checkout conversion": "checkout_conversion_rate",
        "overall conversion": "overall_conversion_rate",
        "conversion rate": "overall_conversion_rate",
        "conversion": "overall_conversion_rate"
    }

    def __init__(self, tolerance: float = 0.005):
        # 0.5% relative numeric tolerance
        self.tolerance = tolerance

    def verify_and_link(
        self,
        text: str,
        metrics: Optional[List[MetricResult]] = None,
        flags: Optional[List[DigestFlag]] = None,
        anomalies: Optional[List[Any]] = None
    ) -> Tuple[str, List[EvidenceCitation], List[str]]:
        """
        Parses text sentence by sentence, checks every claim against provided metrics and flags.
        Returns:
            - clean_text: Filtered text with unsupported sentences pruned
            - citations: List of verified EvidenceCitation links
            - dropped_claims: List of rejected sentences with failure rationale
        """
        metrics = metrics or []
        flags = flags or []
        anomalies = anomalies or []

        # Build fact dictionary for fast matching
        fact_index = self._build_fact_index(metrics, flags, anomalies)

        sentences = self._split_into_sentences(text)
        retained_sentences: List[str] = []
        citations: List[EvidenceCitation] = []
        dropped_claims: List[str] = []

        for sentence in sentences:
            sentence_clean = sentence.strip()
            if not sentence_clean:
                continue

            # Check sentence for validity
            is_valid, cit, reason = self._evaluate_sentence(sentence_clean, fact_index)
            if is_valid:
                # Remove inline citation markup from user-facing text
                display_sentence = re.sub(r"\[citation:[^\]]+\]", "", sentence_clean).strip()
                display_sentence = re.sub(r"\s+", " ", display_sentence)
                retained_sentences.append(display_sentence)
                if cit:
                    citations.extend(cit)
            else:
                dropped_claims.append(f"{sentence_clean} (Reason: {reason})")

        clean_text = " ".join(retained_sentences)
        return clean_text, citations, dropped_claims

    def _evaluate_sentence(
        self,
        sentence: str,
        fact_index: Dict[str, Any]
    ) -> Tuple[bool, List[EvidenceCitation], Optional[str]]:
        """
        Evaluates an individual sentence against the fact index.
        """
        sentence_lower = sentence.lower()

        # 1. Reject ungrounded qualitative hyperbole
        for qual in self.UNSUPPORTED_QUALIFIERS:
            # Check whole-word / phrase match
            pattern = rf"\b{re.escape(qual)}\b"
            if re.search(pattern, sentence_lower):
                return False, [], f"Contains ungrounded qualitative qualifier '{qual}'"

        # 2. Check for explicit citation tags first: [citation: metric=name value=0.4500 sample=100]
        explicit_match = re.search(
            r"\[citation:\s*metric=([a-zA-Z0-9_]+)\s+value=([\d\.]+)(?:\s+prior=([\d\.]+))?(?:\s+sample=(\d+))?\]",
            sentence,
            re.IGNORECASE
        )
        if explicit_match:
            metric_name = explicit_match.group(1).lower()
            claimed_val = float(explicit_match.group(2))
            claimed_prior = float(explicit_match.group(3)) if explicit_match.group(3) else None
            sample_size = int(explicit_match.group(4)) if explicit_match.group(4) else 0

            if metric_name not in fact_index:
                return False, [], f"Unknown metric '{metric_name}' in citation"

            fact = fact_index[metric_name]
            expected_val = fact["value"]
            if expected_val is None:
                return False, [], f"Metric '{metric_name}' has undefined value (zero denominator)"

            # Tolerance check
            if abs(claimed_val - expected_val) > max(self.tolerance, 0.001):
                return False, [], f"Metric '{metric_name}' value mismatch (claimed {claimed_val}, expected {expected_val})"

            # Polarity check if direction words are used
            if not self._check_polarity(sentence_lower, fact.get("pct_change"), fact.get("polarity")):
                return False, [], f"Direction mismatch in '{sentence}' (computed change is {fact.get('pct_change')}%)"

            prior_val = fact.get("prior_value", claimed_prior)
            cit = EvidenceCitation(
                citation_id=f"cit_{metric_name}",
                claim_text=sentence,
                metric_name=metric_name,
                computed_value=expected_val,
                prior_value=prior_val,
                sample_size=fact.get("sample_size", sample_size),
                is_verified=True
            )
            return True, [cit], None

        # 3. Identify which metric is referenced in the sentence
        referenced_metric = self._identify_referenced_metric(sentence_lower, fact_index)

        # 4. Check if sentence makes numeric percentage assertions
        pct_matches = re.findall(r"(\d+(?:\.\d+)?)%", sentence)
        if pct_matches:
            if not referenced_metric:
                return False, [], f"Percentage claim {pct_matches} without identifiable metric concept"

            fact = fact_index[referenced_metric]
            expected_val = fact.get("value")
            prior_val = fact.get("prior_value")
            pct_chg = fact.get("pct_change")

            # Verify that the claimed percentage belongs to the referenced metric
            matched_claim = False
            for p in pct_matches:
                p_float = float(p)
                p_ratio = p_float / 100.0

                if expected_val is not None and (abs(expected_val - p_ratio) <= self.tolerance or abs(expected_val * 100.0 - p_float) <= self.tolerance * 100.0):
                    matched_claim = True
                    break
                if prior_val is not None and (abs(prior_val - p_ratio) <= self.tolerance or abs(prior_val * 100.0 - p_float) <= self.tolerance * 100.0):
                    matched_claim = True
                    break
                if pct_chg is not None and abs(abs(pct_chg) - p_float) <= 1.0:
                    matched_claim = True
                    break

            if not matched_claim:
                return False, [], (
                    f"Number {pct_matches}% does not match referenced metric '{referenced_metric}' "
                    f"(computed value: {expected_val}, delta: {pct_chg}%)"
                )

            # Polarity check
            if not self._check_polarity(sentence_lower, fact.get("pct_change"), fact.get("polarity")):
                return False, [], f"Polarity contradiction for metric '{referenced_metric}'"

            cit = EvidenceCitation(
                citation_id=f"cit_{referenced_metric}",
                claim_text=sentence,
                metric_name=referenced_metric,
                computed_value=fact["value"] if fact["value"] is not None else 0.0,
                prior_value=fact.get("prior_value"),
                sample_size=fact.get("sample_size", 0),
                is_verified=True
            )
            return True, [cit], None

        # 5. Sentence with NO numbers and NO explicit citation
        if referenced_metric:
            fact = fact_index[referenced_metric]
            pct_change = fact.get("pct_change")

            # Check directional words
            has_pos = any(w in sentence_lower for w in self.POSITIVE_WORDS)
            has_neg = any(w in sentence_lower for w in self.NEGATIVE_WORDS)

            if has_pos or has_neg:
                if not self._check_polarity(sentence_lower, pct_change, fact.get("polarity")):
                    return False, [], (
                        f"Direction contradiction for '{referenced_metric}': claim asserts "
                        f"{'decrease' if has_neg else 'increase'}, but computed delta was {pct_change:+.1f}%"
                    )
                # Valid grounded directional claim
                return True, [], None

        # 6. Sentence has no numbers, no explicit citation, and no factual grounding -> Reject
        return False, [], "Ungrounded assertion without backing metric fact or citation tag"

    def _identify_referenced_metric(self, sentence_lower: str, fact_index: Dict[str, Any]) -> Optional[str]:
        """
        Determines the single most specific metric referenced in the sentence.
        """
        # Exact keyword map match
        for phrase, m_key in sorted(self.METRIC_KEYWORD_MAP.items(), key=lambda x: len(x[0]), reverse=True):
            if phrase in sentence_lower and m_key in fact_index:
                return m_key

        # Direct metric name match
        for m_key in sorted(fact_index.keys(), key=len, reverse=True):
            if m_key.replace("_", " ") in sentence_lower or m_key in sentence_lower:
                return m_key

        return None

    def _check_polarity(
        self,
        sentence_lower: str,
        pct_change: Optional[float],
        polarity: Optional[str] = None
    ) -> bool:
        """
        Validates that directional claims align mathematically with the sign of the delta.
        """
        if pct_change is None:
            return True

        has_pos = any(w in sentence_lower for w in self.POSITIVE_WORDS)
        has_neg = any(w in sentence_lower for w in self.NEGATIVE_WORDS)

        # If metric increased (pct_change > 0), but sentence claims decrease/drop/reduction without increase:
        if pct_change > 0.5 and has_neg and not has_pos:
            return False

        # If metric decreased (pct_change < -0.5), but sentence claims increase/spike/surge without decrease:
        if pct_change < -0.5 and has_pos and not has_neg:
            return False

        return True

    def _build_fact_index(
        self,
        metrics: List[MetricResult],
        flags: List[DigestFlag],
        anomalies: List[Any]
    ) -> Dict[str, Any]:
        facts: Dict[str, Any] = {}

        for m in metrics:
            name = m.metric_name.lower()
            if name not in facts:
                facts[name] = {
                    "value": m.value,
                    "sample_size": m.sample_size,
                    "min_sample_met": m.min_sample_met,
                    "prior_value": None,
                    "pct_change": None,
                    "polarity": None
                }
            else:
                # Prior window comparison
                facts[name]["prior_value"] = m.value
                cur_val = facts[name]["value"]
                if cur_val is not None and m.value is not None and m.value > 0:
                    facts[name]["pct_change"] = ((cur_val - m.value) / m.value) * 100.0

        for f in flags:
            name = f.metric_name.lower()
            chg = getattr(f, "delta_pct", getattr(f, "pct_change", None))
            sample = getattr(f, "current_sample_size", getattr(f, "sample_size", 0))
            is_sig = getattr(f, "is_statistically_significant", getattr(f, "is_significant", True))
            facts[name] = {
                "value": f.current_value,
                "prior_value": f.prior_value,
                "pct_change": chg,
                "sample_size": sample,
                "min_sample_met": getattr(f, "min_sample_met", True),
                "is_significant": is_sig,
                "polarity": getattr(f, "polarity", None)
            }

        for a in anomalies:
            cart_val = getattr(a, "cart_total_inr", getattr(a, "cart_value", None))
            if cart_val is not None:
                facts["idle_cart_value"] = {
                    "value": cart_val,
                    "sample_size": 1,
                    "min_sample_met": True,
                    "pct_change": None
                }

        return facts

    def _split_into_sentences(self, text: str) -> List[str]:
        raw = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in raw if s.strip()]
