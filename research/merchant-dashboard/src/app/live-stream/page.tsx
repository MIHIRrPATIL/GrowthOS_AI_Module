'use client';

import React, { useState, useEffect } from 'react';
import {
  Activity,
  Filter,
  Layers,
  Sparkles,
  Search,
  CheckCircle2,
  AlertTriangle,
  Flame,
  ArrowRight,
  ShieldCheck
} from 'lucide-react';

interface LiveEvent {
  event_id: string;
  event_name: string;
  timestamp: string;
  customer_id?: string;
  anonymous_id: string;
  session_id: string;
  category: 'ecommerce' | 'ux' | 'form' | 'autocapture';
  properties: Record<string, any>;
}

const INITIAL_EVENTS: LiveEvent[] = [
  {
    event_id: 'evt_984a1',
    event_name: 'purchase.completed',
    timestamp: '2026-08-25T14:34:00.000Z',
    customer_id: 'CUST-48291',
    anonymous_id: 'anon_d892f',
    session_id: 'sess_1904a',
    category: 'ecommerce',
    properties: { order_id: 'DOM-918231', total_amount: 588, loyalty_points_earned: 58, payment_method: 'UPI' }
  },
  {
    event_id: 'evt_984a2',
    event_name: 'checkout.step_completed',
    timestamp: '2026-08-25T14:33:35.000Z',
    customer_id: 'CUST-48291',
    anonymous_id: 'anon_d892f',
    session_id: 'sess_1904a',
    category: 'ecommerce',
    properties: { step_number: 2, step_name: 'delivery_charges_and_slot', delivery_fee: 60 }
  },
  {
    event_id: 'evt_984a3',
    event_name: 'user.typing_dynamics',
    timestamp: '2026-08-25T14:33:10.000Z',
    anonymous_id: 'anon_d892f',
    session_id: 'sess_1904a',
    category: 'ux',
    properties: { keystroke_count: 14, backspace_count: 1, typing_speed_cpm: 240, avg_flight_time_ms: 180 }
  },
  {
    event_id: 'evt_984a4',
    event_name: 'cart.coupon_applied',
    timestamp: '2026-08-25T14:32:30.000Z',
    customer_id: 'CUST-48291',
    anonymous_id: 'anon_d892f',
    session_id: 'sess_1904a',
    category: 'ecommerce',
    properties: { coupon_code: 'DOMINOS50', discount_value: 50, cart_subtotal: 588 }
  },
  {
    event_id: 'evt_984a5',
    event_name: 'product.customized',
    timestamp: '2026-08-25T14:32:00.000Z',
    anonymous_id: 'anon_d892f',
    session_id: 'sess_1904a',
    category: 'ecommerce',
    properties: { name: 'Farmhouse Pizza', size: 'Medium', crust: 'Cheese Burst', extra_cheese: true }
  },
  {
    event_id: 'evt_984a6',
    event_name: 'scroll.milestone',
    timestamp: '2026-08-25T14:31:20.000Z',
    anonymous_id: 'anon_d892f',
    session_id: 'sess_1904a',
    category: 'autocapture',
    properties: { milestone: '75%', max_depth_pct: 78 }
  },
  {
    event_id: 'evt_984a7',
    event_name: 'user.rage_click',
    timestamp: '2026-08-25T14:30:20.000Z',
    anonymous_id: 'anon_394bc',
    session_id: 'sess_9921b',
    category: 'ux',
    properties: { click_count: 3, time_window_ms: 410, target_tag: 'BUTTON', target_id: 'btnApplyCoupon' }
  }
];

export default function LiveStreamPage() {
  const [events, setEvents] = useState<LiveEvent[]>(INITIAL_EVENTS);
  const [mounted, setMounted] = useState<boolean>(false);
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Poll backend bridge if running
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch('http://localhost:8000/api/v1/events?limit=20');
        if (res.ok) {
          const data = await res.json();
          if (data.events && data.events.length > 0) {
            const mapped: LiveEvent[] = data.events.map((e: any) => ({
              event_id: e.event_id || `evt_${Math.random().toString(36).slice(2, 7)}`,
              event_name: e.event_name,
              timestamp: e.timestamp,
              customer_id: e.customer_id,
              anonymous_id: e.anonymous_id,
              session_id: e.session_id,
              category: e.event_name.startsWith('user.')
                ? 'ux'
                : e.event_name.startsWith('form.')
                ? 'form'
                : e.event_name.startsWith('autocapture.') || e.event_name.startsWith('scroll.')
                ? 'autocapture'
                : 'ecommerce',
              properties: e.properties || {}
            }));
            setEvents((prev) => {
              const combined = [...mapped.reverse(), ...prev];
              const unique = Array.from(new Map(combined.map((item) => [item.event_id, item])).values());
              return unique.slice(0, 50);
            });
          }
        }
      } catch (e) {
        // Fallback to initial stream
      }
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  const filteredEvents = events.filter((e) => {
    const matchesCat = filterCategory === 'all' || e.category === filterCategory;
    const matchesSearch =
      e.event_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (e.customer_id && e.customer_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
      JSON.stringify(e.properties).toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div className="space-y-8 pb-12">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-black uppercase mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            <span>Real-Time Ingestion</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Live Telemetry & Event Inspector
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Stream raw events and micro-friction signals received directly from the storefront browser SDK.
          </p>
        </div>

        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-300">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-bold">{filteredEvents.length} Events In Buffer</span>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 rounded-2xl bg-slate-900 border border-slate-800">
        <div className="flex items-center space-x-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {['all', 'ecommerce', 'ux', 'form', 'autocapture'].map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-3 py-1.5 rounded-xl text-xs font-black uppercase tracking-wider transition-all ${
                filterCategory === cat
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/25'
                  : 'text-slate-400 hover:text-white bg-slate-950/60'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search event or payload..."
            className="w-full pl-8 pr-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Live Stream Feed */}
      <div className="space-y-2.5">
        {filteredEvents.map((e) => {
          const isExpanded = expandedEventId === e.event_id;
          const isFriction = e.event_name.startsWith('user.rage') || e.event_name.startsWith('user.excessive') || e.event_name.startsWith('user.exit');

          return (
            <div
              key={e.event_id}
              className={`rounded-2xl border transition-all ${
                isFriction
                  ? 'bg-red-950/20 border-red-500/30'
                  : 'bg-slate-900/80 border-slate-800/80 hover:border-slate-700'
              }`}
            >
              {/* Row Header */}
              <div
                onClick={() => setExpandedEventId(isExpanded ? null : e.event_id)}
                className="p-3.5 flex items-center justify-between cursor-pointer"
              >
                <div className="flex items-center space-x-3">
                  <span className="text-[10px] text-slate-500 font-mono" suppressHydrationWarning>
                    {mounted ? new Date(e.timestamp).toLocaleTimeString() : 'Live'}
                  </span>

                  <span
                    className={`font-mono text-xs font-black px-2 py-0.5 rounded-lg ${
                      isFriction
                        ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                        : 'bg-blue-500/10 text-blue-400'
                    }`}
                  >
                    {e.event_name}
                  </span>

                  {e.customer_id && (
                    <span className="text-[10px] font-bold text-amber-300 bg-amber-500/15 px-2 py-0.5 rounded-md">
                      {e.customer_id}
                    </span>
                  )}
                </div>

                <div className="flex items-center space-x-3">
                  <span className="text-[10px] text-slate-500 font-mono hidden md:inline">
                    {e.anonymous_id}
                  </span>
                  <span className="text-xs text-slate-400 font-bold">
                    {isExpanded ? 'Hide' : 'Inspect'} →
                  </span>
                </div>
              </div>

              {/* Expanded JSON Inspector */}
              {isExpanded && (
                <div className="p-4 border-t border-slate-800 bg-slate-950 rounded-b-2xl space-y-2">
                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <span>Session: {e.session_id}</span>
                    <span>Event ID: {e.event_id}</span>
                  </div>
                  <pre className="p-3 rounded-xl bg-slate-900 text-emerald-300 font-mono text-[11px] overflow-x-auto border border-slate-800">
                    {JSON.stringify(e.properties, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>

    </div>
  );
}
