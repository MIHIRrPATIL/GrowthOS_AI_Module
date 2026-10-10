'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { MetricCard } from '../components/MetricCard';
import { FunnelChart } from '../components/FunnelChart';
import { RetentionModal } from '../components/RetentionModal';
import {
  fetchEcommerceFunnel,
  fetchDormantCarts
} from '../lib/api';
import { FunnelData, DormantCohortResponse, DormantCustomer } from '../types/merchant';
import {
  TrendingUp,
  AlertTriangle,
  Users,
  ShoppingCart,
  ArrowRight,
  BrainCircuit,
  Sparkles,
  Activity,
  CheckCircle2,
  Clock
} from 'lucide-react';

export default function OverviewPage() {
  const [macroFunnel, setMacroFunnel] = useState<FunnelData | null>(null);
  const [dormantData, setDormantData] = useState<DormantCohortResponse | null>(null);
  const [selectedRetentionCustomer, setSelectedRetentionCustomer] = useState<DormantCustomer | null>(null);

  useEffect(() => {
    fetchEcommerceFunnel().then(setMacroFunnel);
    fetchDormantCarts().then(setDormantData);
  }, []);

  const handleRetentionSuccess = (customerId: string, actionType: string) => {
    if (dormantData) {
      setDormantData({
        ...dormantData,
        customers: dormantData.customers.map((c) =>
          c.customer_id === customerId
            ? { ...c, action_status: `executed (${actionType})` }
            : c
        )
      });
    }
  };

  return (
    <div className="space-y-7 pb-12">
      
      {/* 1. Page Header (Display Typography & Breadcrumb Context) */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-1">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.18em] text-[#c9ef88]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#b7e65c]" aria-hidden="true" />
            <span>Merchant intelligence</span>
          </div>
          <h1 className="text-3xl sm:text-[2.45rem] font-black text-white tracking-[-0.045em]">
            Today&apos;s revenue opportunities
          </h1>
          <p className="text-xs sm:text-sm text-white/50 max-w-xl leading-relaxed">
            Prioritize checkout friction, recover at-risk carts, and turn live shopper behavior into action.
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <Link
            href="/ai-brain"
            className="group relative inline-flex items-center pl-4 pr-2 py-2 rounded-lg bg-[#b7e65c] hover:bg-[#c8f377] text-[#07110f] font-bold text-xs transition-all active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-[#b7e65c]/50 focus-visible:outline-none"
          >
            <span className="mr-2.5">Ask AI Brain</span>
            <span className="w-6 h-6 rounded-md bg-[#07110f]/10 flex items-center justify-center transition-colors" aria-hidden="true">
              <BrainCircuit className="w-3.5 h-3.5" />
            </span>
          </Link>
        </div>
      </div>

      {/* 2. Primary Metrics Row (Double-Bezel Cards Grid) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        <MetricCard
          title="Store Conversion Rate"
          value="10.97%"
          subtitle="Browse to checkout completed"
          icon={TrendingUp}
          trend={{ value: '+1.4% vs last week', isPositive: true }}
        />

        <MetricCard
          title="Checkout Step 2 Drop-Off"
          value="44.27%"
          subtitle="₹60 delivery fee friction spike"
          icon={AlertTriangle}
          trend={{ value: '+8.2% drop spike', isPositive: false }}
          highlight={true}
        />

        <MetricCard
          title="At-Risk Cart Revenue"
          value={`₹${dormantData?.total_at_risk_revenue || 947}`}
          subtitle={`${dormantData?.total_at_risk_customers || 2} abandoned carts (>1h inactive)`}
          icon={ShoppingCart}
          trend={{ value: '2 recoverable', isPositive: true }}
        />

        <MetricCard
          title="Telemetry Observers"
          value="11 Triggers"
          subtitle="Autocapture, forms, scroll & keystrokes"
          icon={Activity}
        />
      </div>

      {/* 3. AI Growth Brain Urgent Insight Spotlight (Obsidian Glass Card) */}
      <div className="relative overflow-hidden rounded-xl border border-[#b7e65c]/25 bg-[#10211c] p-5 sm:p-7">
        
        {/* Ambient Warm Glow */}
        <div className="absolute right-0 top-0 h-64 w-64 rounded-full bg-[#b7e65c]/[0.07] blur-3xl pointer-events-none" aria-hidden="true" />

        <div className="relative space-y-5">
          
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-[#b7e65c]" aria-hidden="true" />
              <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#c9ef88]">
                AI opportunity detected
              </span>
            </div>
            
            <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-[#b7e65c]/10 border border-[#b7e65c]/20 text-[#d7f5a5] text-[10px] font-mono font-bold">
              <Sparkles className="w-3 h-3 text-[#b7e65c]" aria-hidden="true" />
              <span>94% Confidence</span>
            </div>
          </div>

          <div className="space-y-2">
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight text-balance">
              Delivery fee friction is stopping high-intent orders
            </h2>
            <p className="text-xs sm:text-sm text-white/60 max-w-4xl leading-relaxed text-pretty">
              Behavior across <strong className="text-white">1,240 sessions</strong> shows a sharp exit pattern when shoppers see the ₹60 delivery charge at checkout.
            </p>
          </div>

          {/* Impact & Autonomous Action Row */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-white/[0.06]">
            <div className="flex flex-wrap items-center gap-4 text-xs">
              <div className="flex items-center space-x-2">
                <span className="text-white/40">Potential Recovery:</span>
                <span className="font-bold text-[#c9ef88] font-mono">+28 orders/day</span>
              </div>
              <div className="h-3 w-px bg-white/10 hidden sm:block" />
              <div className="flex items-center space-x-2">
                <span className="text-white/40">Projected GMV Lift:</span>
                <span className="font-bold text-[#c9ef88] font-mono">₹14,200 / day</span>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Link
                href="/funnels"
                className="text-xs font-semibold text-white/55 hover:text-white transition-colors"
              >
                Inspect Step Breakdown →
              </Link>
              <Link
                href="/cohorts"
                className="group relative inline-flex items-center pl-4 pr-2 py-2 rounded-lg bg-[#b7e65c] hover:bg-[#c8f377] active:scale-[0.98] text-[#07110f] font-bold text-xs transition-all focus-visible:ring-2 focus-visible:ring-[#b7e65c] focus-visible:outline-none"
              >
                <span className="mr-2">Review Dormant Carts</span>
                <span className="w-5 h-5 rounded-md bg-[#07110f]/10 flex items-center justify-center transition-transform group-hover:translate-x-0.5" aria-hidden="true">
                  <ArrowRight className="w-3 h-3 text-[#07110f]" />
                </span>
              </Link>
            </div>
          </div>

        </div>
      </div>

      {/* 4. Asymmetrical Bento Layout: Macro Funnel (2 Cols) + Dormant Cohort (1 Col) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8 items-start">
        
        {/* Left 2 Columns: Macro Funnel Telemetry */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-white tracking-tight">Macro Conversion Funnel</h2>
              <span className="text-[10px] font-mono text-white/40 px-2 py-0.5 rounded bg-white/[0.03] border border-white/[0.06]">
                Last 7 Days
              </span>
            </div>
            <Link
              href="/funnels"
              className="text-xs font-semibold text-[#828fff] hover:text-white transition-colors flex items-center space-x-1"
            >
              <span>Granular Sub-Steps</span>
              <ArrowRight className="w-3 h-3" aria-hidden="true" />
            </Link>
          </div>

          {macroFunnel && (
            <FunnelChart
              steps={macroFunnel.steps}
              title="Browse → Cart → Checkout → Purchase"
            />
          )}
        </div>

        {/* Right 1 Column: Urgent Dormant Carts Cohort Card (Double-Bezel) */}
        <div className="rounded-[1.75rem] p-1 bg-gradient-to-b from-white/[0.08] to-white/[0.02] border border-white/[0.06] shadow-xl space-y-4">
          <div className="rounded-[calc(1.75rem-4px)] bg-[#090b10]/95 p-6 space-y-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
            
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/[0.06] pb-4">
              <div className="flex items-center space-x-2.5">
                <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                  <Users className="w-4 h-4" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                    Dormant Carts
                  </h3>
                  <p className="text-[10px] text-white/40">Inactivity &gt; 1 Hour</p>
                </div>
              </div>
              <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-300 border border-rose-500/25">
                2 At Risk
              </span>
            </div>

            {/* List of Abandoned Customers */}
            <div className="space-y-3">
              {dormantData?.customers.map((c) => (
                <div
                  key={c.customer_id}
                  className="rounded-2xl p-4 bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.05] hover:border-white/[0.1] transition-all space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2.5">
                      <div className="w-7 h-7 rounded-xl bg-gradient-to-tr from-[#5e6ad2]/30 to-[#828fff]/20 border border-[#5e6ad2]/40 flex items-center justify-center text-white text-xs font-bold font-mono">
                        {c.customer_name.charAt(0)}
                      </div>
                      <div>
                        <div className="text-xs font-bold text-white">{c.customer_name}</div>
                        <div className="text-[10px] text-white/40">
                          {c.tier} Member • {c.loyalty_points} pts
                        </div>
                      </div>
                    </div>
                    <span className="text-sm font-black text-white font-mono tabular-nums">
                      ₹{c.cart_total}
                    </span>
                  </div>

                  <div className="text-[11px] text-amber-400/90 font-medium truncate flex items-center space-x-1.5">
                    <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0" aria-hidden="true" />
                    <span className="truncate">{c.abandoned_step}</span>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-white/[0.04] text-[10px]">
                    <span className="text-white/40 font-mono flex items-center space-x-1">
                      <Clock className="w-2.5 h-2.5" aria-hidden="true" />
                      <span>{c.dormant_duration_minutes}m ago</span>
                    </span>

                    {c.action_status === 'pending' ? (
                      <button
                        type="button"
                        onClick={() => setSelectedRetentionCustomer(c)}
                        className="group inline-flex items-center pl-3 pr-1.5 py-1 rounded-full bg-[#5e6ad2] hover:bg-[#6c78e3] active:scale-[0.98] text-white text-[10px] font-bold transition-all shadow-[0_0_12px_rgba(94,106,210,0.35)] focus-visible:ring-2 focus-visible:ring-[#5e6ad2] focus-visible:outline-none"
                      >
                        <span className="mr-1.5">Recover</span>
                        <span className="w-4 h-4 rounded-full bg-white/20 flex items-center justify-center transition-transform group-hover:translate-x-0.5" aria-hidden="true">
                          <ArrowRight className="w-2.5 h-2.5" />
                        </span>
                      </button>
                    ) : (
                      <span className="inline-flex items-center space-x-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                        <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
                        <span>Recovered</span>
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Link to Cohorts View */}
            <Link
              href="/cohorts"
              className="block text-center text-xs font-semibold text-white/50 hover:text-white pt-1 transition-colors"
            >
              View All Cohorts & Automated Rules →
            </Link>

          </div>
        </div>

      </div>

      {/* Retention Action Modal */}
      <RetentionModal
        customer={selectedRetentionCustomer}
        onClose={() => setSelectedRetentionCustomer(null)}
        onSuccess={handleRetentionSuccess}
      />

    </div>
  );
}
