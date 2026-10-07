'use client';

import React, { useState } from 'react';
import {
  BrainCircuit,
  Sparkles,
  Send,
  HelpCircle,
  Award,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  TrendingUp,
  ShieldCheck,
  Zap
} from 'lucide-react';

interface AIInsight {
  id: string;
  query: string;
  category: 'friction' | 'retention' | 'acquisition' | 'pricing';
  confidence: number;
  headline: string;
  diagnosis: string;
  evidence: string[];
  recommended_policy: string;
  action_label: string;
  action_dispatched: boolean;
}

const PRESET_QUERIES = [
  'Why did checkout conversion drop this weekend?',
  'Which customers added pizzas to cart but didn’t buy?',
  'What retention policy should we trigger for Gold members?',
  'How do delivery fees affect order drop-offs?'
];

const INITIAL_INSIGHTS: AIInsight[] = [
  {
    id: 'ins_1',
    query: 'Why did checkout conversion drop this weekend?',
    category: 'friction',
    confidence: 94,
    headline: 'Checkout Step 2 Delivery Fee Friction on Sub-₹800 Orders',
    diagnosis: 'Analysis across 223 checkout sessions reveals that 44.27% of users bail out specifically at Step 2 (Delivery Slot & Charges) after the ₹60 delivery fee is added to sub-₹800 carts. Users show 64 hesitation pauses and 41 exit intent spikes.',
    evidence: [
      'Checkout Step 2 conversion dropped from 82.1% to 55.7%',
      'Average hesitation dwell on delivery fee screen exceeded 18.4s',
      '41 desktop exit-intent signals triggered within 3 seconds of delivery fee rendering'
    ],
    recommended_policy: 'Module 1 Loyalty Rule: Automatically waive ₹60 delivery fee using 60 Loyalty Points for Gold/Silver tier members with cart value > ₹400.',
    action_label: 'Activate 1-Click Loyalty Delivery Waiver Policy',
    action_dispatched: false
  },
  {
    id: 'ins_2',
    query: 'Which customers added pizzas to cart but didn’t buy?',
    category: 'retention',
    confidence: 91,
    headline: '2 High-Value Dormant Carts (₹947 GMV at Risk)',
    diagnosis: 'Two identified members (Rahul Sharma, Priya Patel) have dormant carts exceeding 1 hour. Both reached Step 2 of the checkout funnel before abandoning.',
    evidence: [
      'Rahul Sharma (Gold, 250 pts): ₹588 cart (Medium Cheese Burst Farmhouse + Sides) dormant for 142 minutes',
      'Priya Patel (Silver, 80 pts): ₹359 cart dormant for 85 minutes'
    ],
    recommended_policy: 'Dispatch personalized WhatsApp recovery links with instant 1-click cart restore and dynamic coupon DOMINOS50.',
    action_label: 'Dispatch WhatsApp Cart Recovery Campaign',
    action_dispatched: false
  }
];

export default function AIBrainPage() {
  const [queryInput, setQueryInput] = useState<string>('');
  const [insights, setInsights] = useState<AIInsight[]>(INITIAL_INSIGHTS);
  const [isThinking, setIsThinking] = useState<boolean>(false);

  const handleAskQuery = (query: string) => {
    if (!query.trim()) return;
    setIsThinking(true);
    setQueryInput(query);

    setTimeout(() => {
      const newInsight: AIInsight = {
        id: `ins_${Date.now()}`,
        query,
        category: 'pricing',
        confidence: 89,
        headline: `Semantic AI Analysis: ${query}`,
        diagnosis: `Module 4 cross-correlated telemetry across 1,240 storefront sessions. High intent users who customize crusts (Cheese Burst +₹99) convert at 68% if presented with a free Garlic Bread pairing, compared to 34% baseline.`,
        evidence: [
          'Product customizer modal triggers high purchase intent (2.4x higher than standard quick-add)',
          'Cart-to-checkout velocity is 42% faster for customized orders'
        ],
        recommended_policy: 'Trigger dynamic bundle recommendation: "Add Garlic Bread for ₹49 when selecting Cheese Burst Crust".',
        action_label: 'Enable Dynamic Upsell Policy',
        action_dispatched: false
      };
      setInsights([newInsight, ...insights]);
      setIsThinking(false);
      setQueryInput('');
    }, 1000);
  };

  const handleDispatchAction = (id: string) => {
    setInsights(
      insights.map((ins) =>
        ins.id === id ? { ...ins, action_dispatched: true } : ins
      )
    );
  };

  return (
    <div className="space-y-8 pb-12">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[10px] font-black uppercase mb-1">
            <BrainCircuit className="w-3 h-3" />
            <span>GrowthOS Module 4 — Customer Intelligence</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            AI Growth Brain Assistant
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Natural language semantic reasoning across storefront telemetry, drop-off funnels, and customer retention graphs.
          </p>
        </div>

        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-2xl bg-indigo-950/40 border border-indigo-500/30 text-indigo-300 text-xs font-extrabold">
          <Sparkles className="w-4 h-4 text-indigo-400 animate-pulse" />
          <span>Reasoning Engine Live</span>
        </div>
      </div>

      {/* Query Bar */}
      <div className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 space-y-4 shadow-xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAskQuery(queryInput);
          }}
          className="relative flex items-center"
        >
          <input
            type="text"
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            placeholder="Ask the AI Brain: e.g., 'Why did checkout conversion drop this weekend?'"
            className="w-full pl-5 pr-28 py-4 rounded-2xl bg-slate-950 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 shadow-inner"
          />
          <button
            type="submit"
            disabled={isThinking || !queryInput.trim()}
            className="absolute right-2.5 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-black text-xs shadow-lg shadow-indigo-600/20 flex items-center space-x-2 disabled:opacity-50 transition-all"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{isThinking ? 'Reasoning...' : 'Ask AI'}</span>
          </button>
        </form>

        {/* Preset Query Chips */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[11px] font-bold text-slate-500">Suggested queries:</span>
          {PRESET_QUERIES.map((q) => (
            <button
              key={q}
              onClick={() => handleAskQuery(q)}
              className="text-xs px-3 py-1 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Reasoning Cards Stream */}
      <div className="space-y-6">
        <h2 className="text-base font-extrabold text-white">AI Diagnostic Reasoning & Recommendations</h2>

        {insights.map((insight) => (
          <div
            key={insight.id}
            className="p-6 sm:p-8 rounded-3xl bg-slate-900/90 border border-slate-800 space-y-5 hover:border-slate-700 transition-all shadow-lg"
          >
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
              <div className="space-y-1">
                <div className="text-[11px] font-mono text-indigo-400 font-bold">
                  Q: "{insight.query}"
                </div>
                <h3 className="text-lg font-black text-white">{insight.headline}</h3>
              </div>

              <div className="flex items-center space-x-2 self-start sm:self-auto">
                <span className="text-xs font-black px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">
                  {insight.confidence}% Confidence
                </span>
              </div>
            </div>

            {/* Diagnosis */}
            <div className="space-y-2">
              <h4 className="text-xs font-black uppercase text-slate-400 tracking-wider">
                Behavioral Diagnosis
              </h4>
              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                {insight.diagnosis}
              </p>
            </div>

            {/* Evidence Points */}
            <div className="space-y-2">
              <h4 className="text-xs font-black uppercase text-slate-400 tracking-wider">
                Telemetry Evidence & Signals
              </h4>
              <ul className="space-y-1.5">
                {insight.evidence.map((ev, idx) => (
                  <li key={idx} className="flex items-start space-x-2 text-xs text-slate-400">
                    <span className="text-indigo-400 font-bold mt-0.5">•</span>
                    <span>{ev}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Recommended Policy & Action */}
            <div className="p-5 rounded-2xl bg-gradient-to-r from-indigo-950/40 via-slate-950 to-slate-950 border border-indigo-500/30 space-y-3">
              <div className="flex items-center space-x-2 text-indigo-300 text-xs font-black uppercase">
                <Zap className="w-4 h-4 text-amber-400" />
                <span>Recommended Retention Policy</span>
              </div>

              <p className="text-xs text-slate-200 leading-relaxed font-medium">
                {insight.recommended_policy}
              </p>

              <div className="pt-2">
                {insight.action_dispatched ? (
                  <div className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-black">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>Policy Dispatched & Active</span>
                  </div>
                ) : (
                  <button
                    onClick={() => handleDispatchAction(insight.id)}
                    className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-black text-xs shadow-md shadow-indigo-600/25 flex items-center space-x-2 transition-all"
                  >
                    <span>{insight.action_label}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

          </div>
        ))}
      </div>

    </div>
  );
}
