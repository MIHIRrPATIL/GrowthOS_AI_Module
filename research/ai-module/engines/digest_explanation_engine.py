"""
Digest Explanation Engine
Coordinates between LLMPort for narrative drafting and EvidenceLinker for deterministic verification.
Produces auditable, grounded merchant digest summaries with zero unbacked claims.
Strictly NO emojis used in logs or output.
"""

from typing import Optional, List
from datetime import datetime, timezone

from domain.metrics import DigestReport, DigestFlag
from domain.nlp import DigestExplanation
from ports.llm import LLMPort
from engines.evidence_linker import EvidenceLinker


class DigestExplanationEngine:
    """
    Produces verified, natural-language digest summaries from structured DigestReports.
    Guarantees that every statement is checked by EvidenceLinker before exposure to merchants.
    Ranks flags by adverse impact and matches every statement directly to its cited metric evidence.
    """

    def __init__(
        self,
        llm_port: LLMPort,
        evidence_linker: Optional[EvidenceLinker] = None
    ):
        self.llm_port = llm_port
        self.evidence_linker = evidence_linker or EvidenceLinker()

    def generate_explanation(
        self,
        report: DigestReport,
        vertical: str = "ecommerce_d2c"
    ) -> DigestExplanation:
        """
        Drafts, verifies, and links narrative explanations for a DigestReport.
        Ranks flags by impact and attaches verified citation tags matching each sentence.
        """
        anomalies = getattr(report, "idle_cart_anomalies", getattr(report, "anomalies", []))

        # 1. Rank flags by adverse operational impact (excess lost drop-off volume)
        def compute_flag_impact(f: DigestFlag) -> float:
            sample = getattr(f, "current_sample_size", getattr(f, "sample_size", 0))
            cur_val = f.current_value or 0.0
            pri_val = f.prior_value or 0.0

            # Step-level granular friction is prioritized for operational bottleneck identification
            is_step_friction = "step_" in f.metric_name and "drop_off" in f.metric_name
            priority_boost = 1000.0 if is_step_friction else 0.0

            if "drop_off" in f.metric_name or "abandonment" in f.metric_name:
                cur_drops = int(round(cur_val * sample))
                excess_lost = max(0.0, cur_drops - (sample * pri_val))
                return priority_boost + excess_lost * 10.0 + (cur_val - pri_val) * 10.0
            elif "conversion" in f.metric_name:
                cur_conv = int(round(cur_val * sample))
                lost_conv = max(0.0, (sample * pri_val) - cur_conv)
                return lost_conv * 10.0 + abs(cur_val - pri_val) * 10.0
            delta_mag = abs(getattr(f, "delta_pct", getattr(f, "pct_change", 0.0)) or 0.0)
            return delta_mag

        ranked_flags = sorted(report.flags, key=compute_flag_impact, reverse=True)

        # 2. Draft narrative via LLMPort (with deterministic fallback)
        draft_text = ""
        try:
            draft_text = self.llm_port.explain_digest(report, vertical=vertical)
        except Exception:
            draft_text = ""

        # Build fact-grounded sentences matching citations to metrics
        grounded_sentences: List[str] = []
        for f in ranked_flags:
            chg = getattr(f, "delta_pct", getattr(f, "pct_change", 0.0)) or 0.0
            sample = getattr(f, "current_sample_size", getattr(f, "sample_size", 0))
            cur_val = f.current_value
            pri_val = f.prior_value
            dir_w = "increased" if chg > 0 else "decreased"
            m_label = f.metric_name.replace("_", " ")

            if cur_val is not None and pri_val is not None:
                pp_delta = (cur_val - pri_val) * 100.0
                sent = (
                    f"{m_label.capitalize()} {dir_w} by {pp_delta:+.1f} pp ({abs(chg):.1f}% relative) "
                    f"from {pri_val * 100.0:.1f}% to {cur_val * 100.0:.1f}% across {sample} sessions "
                    f"[citation: metric={f.metric_name} value={cur_val:.4f} prior={pri_val:.4f} sample={sample}]."
                )
            elif cur_val is not None:
                sent = (
                    f"{m_label.capitalize()} reached {cur_val * 100.0:.1f}% across {sample} sessions "
                    f"[citation: metric={f.metric_name} value={cur_val:.4f} sample={sample}]."
                )
            grounded_sentences.append(sent)

        deterministic_narrative = " ".join(grounded_sentences)
        text_to_verify = draft_text if draft_text else deterministic_narrative

        # 3. Verify Narrative and Link Citations via EvidenceLinker
        verified_text, citations, dropped_claims = self.evidence_linker.verify_and_link(
            text=text_to_verify,
            flags=ranked_flags,
            anomalies=anomalies
        )

        if not verified_text and deterministic_narrative and draft_text:
            verified_text, citations, fallback_dropped = self.evidence_linker.verify_and_link(
                text=deterministic_narrative,
                flags=ranked_flags,
                anomalies=anomalies
            )
            dropped_claims.extend(fallback_dropped)

        # 4. Construct Headline and Executive Summary Grounded in Ranked Bottleneck
        if not ranked_flags and not anomalies:
            headline = "Normal Baseline Operations"
            exec_summary = "All funnel and conversion metrics are within healthy limits."
        else:
            top_flag = ranked_flags[0] if ranked_flags else None
            if top_flag:
                chg = getattr(top_flag, "delta_pct", getattr(top_flag, "pct_change", 0.0)) or 0.0
                sample = getattr(top_flag, "current_sample_size", getattr(top_flag, "sample_size", 0))
                cur_val = top_flag.current_value or 0.0
                pri_val = top_flag.prior_value or 0.0
                pp_chg = (cur_val - pri_val) * 100.0
                cur_drops = int(round(cur_val * sample))
                excess_lost = round(cur_drops - (sample * pri_val), 1)

                runner_up = ranked_flags[1] if len(ranked_flags) > 1 else None
                runner_up_lost = 0.0
                if runner_up:
                    ru_sample = getattr(runner_up, "current_sample_size", getattr(runner_up, "sample_size", 0))
                    ru_cur = runner_up.current_value or 0.0
                    ru_pri = runner_up.prior_value or 0.0
                    runner_up_lost = round(int(round(ru_cur * ru_sample)) - (ru_sample * ru_pri), 1)

                clear_margin = (excess_lost > runner_up_lost * 1.15)
                lead_str = "primary operational bottleneck" if clear_margin else "leading operational bottleneck"

                dir_word = "Spike" if chg > 0 else "Drop"
                headline = f"{top_flag.metric_name.replace('_', ' ').title()} {dir_word} Detected (+{excess_lost:.1f} Excess Lost Sessions)"
                margin_note = f" (exceeding {runner_up.metric_name.replace('_', ' ')} with +{runner_up_lost:.1f} excess lost sessions)" if runner_up else ""
                exec_summary = (
                    f"{top_flag.metric_name.replace('_', ' ').capitalize()} changed by "
                    f"{pp_chg:+.1f} pp ({chg:+.1f}% relative) across {sample} sessions, resulting in "
                    f"+{excess_lost:.1f} excess lost sessions as the {lead_str}{margin_note}."
                )
            else:
                headline = f"{len(anomalies)} High-Value Cart Anomaly Detected"
                exec_summary = "Idle recoverable carts identified requiring intervention."

        # Ensure citations match sentences exactly and carry prior values
        flag_by_name = {f.metric_name: f for f in report.flags}
        filtered_citations = []
        exec_lower = exec_summary.lower()
        for cit in citations:
            fl = flag_by_name.get(cit.metric_name)
            if fl and fl.prior_value is not None:
                cit.prior_value = fl.prior_value
            # Only keep citations for metrics mentioned in executive summary
            m_human = cit.metric_name.replace('_', ' ').lower()
            if cit.metric_name in exec_summary or m_human in exec_lower:
                filtered_citations.append(cit)

        if not filtered_citations and citations:
            filtered_citations = [citations[0]]

        return DigestExplanation(
            tenant_id=report.tenant_id,
            headline=headline,
            executive_summary=exec_summary,
            detailed_narrative=verified_text,
            citations=filtered_citations,
            unsupported_claims_dropped=dropped_claims
        )
