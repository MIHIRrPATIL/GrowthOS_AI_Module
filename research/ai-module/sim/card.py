"""
Scenario Card and Ground Truth Renderer
GrowthOS Randomized Scenario Test Environment

Strictly NO emojis in code, terminal output, or logs.
"""

from typing import List
from .scenario import ScenarioSpec


def render_scenario_card(scenario: ScenarioSpec, reveal_planted: bool = False) -> str:
    """
    Renders an ASCII scenario card detailing the active simulation configuration.
    """
    tenant = scenario.tenants[0] if scenario.tenants else None
    t_id = tenant.tenant_id if tenant else "t00"
    vertical = tenant.vertical.value if tenant else "unknown"
    city = tenant.city if tenant else "Mumbai"
    tz = "IST"
    sessions_day = scenario.traffic.sessions_per_day
    aov_inr = int(tenant.aov_paise // 100) if tenant else 0
    del_fee_inr = int(tenant.delivery_fee_paise // 100) if tenant else 0
    cod_pct = int(round(tenant.payment_mix.get("cod", 0.0) * 100)) if tenant else 0

    # Traffic
    mobile_pct = int(round(scenario.traffic.mobile_share * 100))
    paid_pct = int(round(scenario.traffic.channel_mix.get("paid_search", 0.0) * 100))
    new_pct = int(round(scenario.traffic.new_vs_returning_ratio * 100))
    bots_pct = int(round(scenario.traffic.bot_share * 100))
    ad_block_pct = int(round(scenario.traffic.ad_blocker_share * 100))

    # Loyalty
    loyalty = tenant.loyalty if tenant else None
    if loyalty:
        earn_text = f"1pt/{int(1 / loyalty.points_earn_ratio)} INR" if loyalty.points_earn_ratio > 0 else "0pt"
        burn_inr = loyalty.points_burn_rate_paise // 100
        burn_text = f"{burn_inr} INR/pt"
        waiver_cost = f"{loyalty.delivery_fee_waiver_cost_points}pt"
        daily_cap_inr = loyalty.daily_waiver_budget_paise // 100
        cooldown_h = f"{loyalty.waiver_cooldown_hours}h"
        loyalty_line = (
            f"LOYALTY   earn {earn_text}  burn {burn_text}  waiver_cost {waiver_cost}  "
            f"tiers [B,S,G,P]  cooldown {cooldown_h}  waiver_budget {daily_cap_inr:,} INR/day"
        )
    else:
        loyalty_line = "LOYALTY   disabled"

    # Ads
    total_budget_inr = scenario.ads.total_daily_budget_paise // 100
    google_camps = sum(1 for c in scenario.ads.campaigns if c.platform.value == "google")
    meta_camps = sum(1 for c in scenario.ads.campaigns if c.platform.value == "meta")
    avg_target_cpa_inr = (
        int(sum(c.target_cpa_paise for c in scenario.ads.campaigns) / len(scenario.ads.campaigns) // 100)
        if scenario.ads.campaigns else 0
    )

    # Faults
    dup_pct = f"{scenario.faults.duplicate_rate * 100:.1f}%"
    late_pct = f"{scenario.faults.late_event_rate * 100:.1f}%"
    to_succ = "yes" if scenario.faults.adapter_timeout_after_success else "none"
    cb_fails = f"{scenario.faults.circuit_breaker_failures}"
    llm_fault = f"at call {scenario.faults.llm_429_call_index}" if scenario.faults.llm_429_call_index is not None else "none"

    # Planted effects
    if reveal_planted:
        if scenario.planted_effects:
            planted_items = [
                f"{p.effect_type} (mag={p.magnitude}, start_day={p.start_day}, dur={p.duration_days}d)"
                for p in scenario.planted_effects
            ]
            planted_text = ", ".join(planted_items)
        else:
            planted_text = "none (null scenario)"
    else:
        planted_text = "hidden (shown at the end of run, or with --reveal)"

    lines = [
        "+" + "-" * 78 + "+",
        f"| SCENARIO  seed={scenario.seed}  hash={scenario.scenario_hash()}  catalog={scenario.catalog_version}  mode={scenario.mode.value}  size={scenario.size.value}".ljust(79) + "|",
        "+" + "-" * 78 + "+",
        f"| TENANT    {t_id}  {vertical}  {city} ({tz})  ~{sessions_day:,} sessions/day  AOV {aov_inr} INR  fee {del_fee_inr} INR  COD {cod_pct}%".ljust(79) + "|",
        f"|           traffic: mobile {mobile_pct}%  paid {paid_pct}%  new {new_pct}%  bots {bots_pct}%  ad-block {ad_block_pct}%".ljust(79) + "|",
        f"| {loyalty_line}".ljust(79) + "|",
        f"| ADS       {len(scenario.ads.campaigns)} campaigns  total budget {total_budget_inr:,} INR/day  google {google_camps}, meta {meta_camps}  target CPA {avg_target_cpa_inr} INR".ljust(79) + "|",
        f"| FAULTS    duplicates {dup_pct}  late events {late_pct}  timeout_after_success {to_succ}  cb_trips {cb_fails}  llm_429 {llm_fault}".ljust(79) + "|",
        f"| PLANTED   {planted_text}".ljust(79) + "|",
        "+" + "-" * 78 + "+",
    ]
    return "\n".join(lines)


def render_ground_truth(scenario: ScenarioSpec) -> str:
    """
    Renders the revealed ground truth and planted effects at conclusion of simulation run.
    """
    lines = [
        "\n" + "+" + "=" * 78 + "+",
        "| GROUND TRUTH REVEAL & HIDDEN GENERATOR LEDGER".ljust(79) + "|",
        "+" + "=" * 78 + "+",
    ]
    if scenario.planted_effects:
        for idx, p in enumerate(scenario.planted_effects, 1):
            lines.append(
                f"| Planted #{idx}: type={p.effect_type} magnitude={p.magnitude} days={p.start_day}..{p.start_day + p.duration_days} segment={p.target_segment or 'all'}".ljust(79) + "|"
            )
    else:
        lines.append("| Planted effects: None (True Null Scenario)".ljust(79) + "|")

    # True ROAS by campaign
    lines.append("| Hidden True ROAS per Campaign:".ljust(79) + "|")
    for c in scenario.ads.campaigns:
        lines.append(
            f"|   [{c.campaign_id}] {c.name[:30].ljust(30)} -> True ROAS: {c.true_roas:.2f} (Quality: {c.quality_score})".ljust(79) + "|"
        )

    # Loyalty ground truth
    tenant = scenario.tenants[0] if scenario.tenants else None
    if tenant and tenant.loyalty:
        lines.append(
            f"| Loyalty Ground Truth: Daily Fee Waiver Budget Cap = {tenant.loyalty.daily_waiver_budget_paise // 100:,} INR ({tenant.loyalty.daily_waiver_budget_paise} paise)".ljust(79) + "|"
        )

    lines.append("+" + "=" * 78 + "+")
    return "\n".join(lines)
