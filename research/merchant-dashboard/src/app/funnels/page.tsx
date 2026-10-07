'use client';

import React, { useState, useEffect } from 'react';
import { FunnelChart } from '../../components/FunnelChart';
import { fetchEcommerceFunnel, fetchGranularCheckoutFunnel } from '../../lib/api';
import { FunnelData } from '../../types/merchant';
import {
  Filter,
  AlertTriangle,
  Activity,
  Layers,
  Sparkles,
  Info,
  CheckCircle2,
  ArrowRight
} from 'lucide-react';
import Link from 'next/link';

export default function FunnelsPage() {
  const [activeTab, setActiveTab] = useState<'granular' | 'macro'>('granular');
  const [macroFunnel, setMacroFunnel] = useState<FunnelData | null>(null);
  const [granularFunnel, setGranularFunnel] = useState<FunnelData | null>(null);

  useEffect(() => {
    fetchEcommerceFunnel().then(setMacroFunnel);
    fetchGranularCheckoutFunnel().then(setGranularFunnel);
  }, []);

  return (
    <div className="space-y-8 pb-12">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-black uppercase mb-1">
            <Filter className="w-3 h-3" />
            <span>Behavioral Funnel Analysis</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Conversion Funnels & Drop-Off Diagnostics
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Identify exact steps where customers abandon orders and diagnose the underlying behavioral micro-friction.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center p-1.5 rounded-2xl bg-slate-900 border border-slate-800 self-start sm:self-auto">
          <button
            onClick={() => setActiveTab('granular')}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === 'granular'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/25'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Granular Checkout (5 Steps)
          </button>
          <button
            onClick={() => setActiveTab('macro')}
            className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
              activeTab === 'macro'
                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/25'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Macro Store Funnel (4 Steps)
          </button>
        </div>
      </div>

      {/* Main Funnel Chart Display */}
      {activeTab === 'granular' && granularFunnel && (
        <div className="space-y-6">
          <FunnelChart
            steps={granularFunnel.steps}
            title="Granular Checkout Funnel: Step-by-Step Sub-Events (Last 7 Days)"
            isGranular={true}
          />

          {/* Friction Deep-Dive Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            
            <div className="p-5 rounded-3xl bg-slate-900 border border-red-500/30 space-y-3">
              <div className="flex items-center space-x-2 text-red-400 text-xs font-black uppercase">
                <AlertTriangle className="w-4 h-4" />
                <span>Primary Drop-Off: Step 3</span>
              </div>
              <h4 className="text-sm font-extrabold text-white">44.3% Lost at Delivery Slot & Charges</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                41 users triggered desktop Exit Intent and 64 paused for &gt;1.5s immediately after seeing the ₹60 delivery fee on orders below ₹800.
              </p>
              <div className="pt-2">
                <Link
                  href="/cohorts"
                  className="text-xs font-bold text-amber-400 hover:text-amber-300 flex items-center space-x-1"
                >
                  <span>Configure Loyalty Waiver Action</span>
                  <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>

            <div className="p-5 rounded-3xl bg-slate-900 border border-slate-800 space-y-3">
              <div className="flex items-center space-x-2 text-amber-400 text-xs font-black uppercase">
                <Activity className="w-4 h-4" />
                <span>Form Hesitation: Step 2</span>
              </div>
              <h4 className="text-sm font-extrabold text-white">17.9% Lost at Address Entry</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                28 excessive backspace corrections detected on the Pincode and Phone input fields, indicating validation formatting confusion.
              </p>
              <div className="text-[11px] text-slate-500 font-mono">
                Trigger: user.excessive_corrections
              </div>
            </div>

            <div className="p-5 rounded-3xl bg-slate-900 border border-slate-800 space-y-3">
              <div className="flex items-center space-x-2 text-emerald-400 text-xs font-black uppercase">
                <CheckCircle2 className="w-4 h-4" />
                <span>Payment Conversion: Step 4</span>
              </div>
              <h4 className="text-sm font-extrabold text-white">91.8% Converted from Payment</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                UPI Instant and Luhn card validation handled 78 completed purchases with under 1.2s mean processing latency.
              </p>
              <div className="text-[11px] text-emerald-400 font-bold">
                ✓ Highly Optimized
              </div>
            </div>

          </div>
        </div>
      )}

      {activeTab === 'macro' && macroFunnel && (
        <div className="space-y-6">
          <FunnelChart
            steps={macroFunnel.steps}
            title="Macro E-Commerce Funnel: Browse → Cart → Checkout → Purchase"
          />

          <div className="p-6 rounded-3xl bg-slate-900 border border-slate-800 space-y-3">
            <div className="flex items-center space-x-2 text-blue-400 text-xs font-bold">
              <Info className="w-4 h-4" />
              <span>Macro Funnel Insights</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed max-w-4xl">
              PostHog-level macro funnels reveal that <strong className="text-white">65.97%</strong> of users who view products leave without adding to cart (standard browsing behavior), but <strong className="text-white">52.84%</strong> of those who add to cart proceed to checkout. 
              Switching to the <strong className="text-blue-400">Granular Checkout</strong> view reveals the exact sub-step friction causing final abandonments.
            </p>
          </div>
        </div>
      )}

    </div>
  );
}
