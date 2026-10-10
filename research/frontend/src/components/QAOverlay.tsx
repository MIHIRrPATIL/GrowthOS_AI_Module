'use client';

import React, { useState } from 'react';
import { useGrowthOS } from '../context/GrowthOSProvider';
import { Activity, X, ChevronDown, ChevronUp, Trash2, Filter, Zap } from 'lucide-react';

export const QAOverlay: React.FC = () => {
  const { capturedEvents, clearLogs, isQAOpen, setIsQAOpen, anonymousId, customerId } = useGrowthOS();
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  if (!isQAOpen) {
    return (
      <div className="fixed bottom-4 left-4 z-40">
        <button
          onClick={() => setIsQAOpen(true)}
          className="flex items-center space-x-2 px-4 py-2.5 rounded-full bg-slate-900 text-white shadow-2xl hover:scale-105 active:scale-95 border border-slate-700 transition-all"
        >
          <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
          <span className="text-xs font-black tracking-wide">GrowthOS QA Stream</span>
          {capturedEvents.length > 0 && (
            <span className="bg-emerald-500 text-slate-950 font-black text-[10px] px-1.5 py-0.2 rounded-full">
              {capturedEvents.length}
            </span>
          )}
        </button>
      </div>
    );
  }

  const filteredEvents = capturedEvents.filter((evt) => {
    if (selectedCategory === 'all') return true;
    if (selectedCategory === 'ecommerce') return evt.event_name.startsWith('product.') || evt.event_name.startsWith('cart.') || evt.event_name.startsWith('checkout.') || evt.event_name.startsWith('purchase.');
    if (selectedCategory === 'ux') return evt.event_name.startsWith('user.');
    if (selectedCategory === 'form') return evt.event_name.startsWith('form.');
    return true;
  });

  return (
    <div className="fixed bottom-4 right-4 z-50 w-full max-w-lg bg-slate-950/95 backdrop-blur-md rounded-3xl border border-slate-800 text-slate-200 shadow-2xl overflow-hidden flex flex-col max-h-[550px] animate-in slide-in-from-bottom-5">
      
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
        <div className="flex items-center space-x-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
          <h3 className="text-xs font-black uppercase tracking-wider text-white">
            GrowthOS Live Telemetry
          </h3>
          <span className="text-[10px] text-slate-400 font-mono">({capturedEvents.length} events)</span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={clearLogs}
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors"
            title="Clear Stream"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setIsQAOpen(false)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Identity Bar */}
      <div className="px-4 py-2 bg-slate-900/40 border-b border-slate-800/80 text-[10px] flex items-center justify-between font-mono text-slate-400">
        <div>
          <span>Anon: </span>
          <span className="text-blue-400">{anonymousId.slice(0, 10)}...</span>
        </div>
        <div>
          <span>Customer: </span>
          <span className="text-emerald-400">{customerId || 'Guest'}</span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex space-x-1.5 p-2 bg-slate-900/60 border-b border-slate-800 text-[10px] font-bold">
        {['all', 'ecommerce', 'ux', 'form'].map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-2.5 py-1 rounded-lg capitalize transition-all ${
              selectedCategory === cat
                ? 'bg-blue-600 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Event Stream Log */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 font-mono text-xs">
        {filteredEvents.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs">
            Interact with pizzas, forms, or coupons to stream events in real time.
          </div>
        ) : (
          filteredEvents.map((evt) => {
            const isExpanded = expandedEventId === evt.event_id;
            const isEcommerce = evt.event_name.startsWith('cart.') || evt.event_name.startsWith('product.') || evt.event_name.startsWith('checkout.') || evt.event_name.startsWith('purchase.');
            const isUx = evt.event_name.startsWith('user.');
            const isForm = evt.event_name.startsWith('form.');

            const badgeColor = isEcommerce
              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
              : isUx
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
              : isForm
              ? 'bg-blue-500/20 text-blue-300 border-blue-500/30'
              : 'bg-purple-500/20 text-purple-300 border-purple-500/30';

            return (
              <div
                key={evt.event_id}
                className="rounded-xl bg-slate-900/90 border border-slate-800/80 p-2.5 hover:border-slate-700 transition-all"
              >
                <div
                  onClick={() => setExpandedEventId(isExpanded ? null : evt.event_id)}
                  className="flex items-center justify-between cursor-pointer"
                >
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-0.5 rounded-md border text-[10px] font-bold ${badgeColor}`}>
                      {evt.event_name}
                    </span>
                    <span className="text-[10px] text-slate-500" suppressHydrationWarning>
                      {new Date(evt.timestamp).toLocaleTimeString()}
                    </span>
                  </div>

                  {isExpanded ? (
                    <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  )}
                </div>

                {isExpanded && (
                  <div className="mt-2 pt-2 border-t border-slate-800 text-[11px] text-slate-300 bg-slate-950 p-2 rounded-lg overflow-x-auto">
                    <pre>{JSON.stringify(evt.properties, null, 2)}</pre>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

    </div>
  );
};
