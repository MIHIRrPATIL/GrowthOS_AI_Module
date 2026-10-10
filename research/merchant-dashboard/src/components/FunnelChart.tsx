'use client';

import React from 'react';
import { FunnelStep } from '../types/merchant';
import { AlertTriangle, ArrowDown, Activity, Zap } from 'lucide-react';

interface FunnelChartProps {
  steps: FunnelStep[];
  title: string;
  isGranular?: boolean;
}

export const FunnelChart: React.FC<FunnelChartProps> = ({ steps, title, isGranular = false }) => {
  const maxCount = Math.max(...steps.map((s) => s.sessions_count || s.count || 1));

  return (
    <div className="rounded-[1.75rem] p-1 bg-gradient-to-b from-white/[0.08] to-white/[0.02] border border-white/[0.06] shadow-[0_12px_36px_-12px_rgba(0,0,0,0.6)]">
      <div className="rounded-[calc(1.75rem-4px)] bg-[#090b10]/95 p-6 sm:p-7 space-y-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
        
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-5">
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-base font-bold text-white tracking-tight">{title}</h3>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-white/[0.04] text-white/50 border border-white/[0.06]">
                Telemetry Stream
              </span>
            </div>
            <p className="text-xs text-white/40 mt-1">
              Deterministic drop-off tracking powered by Beacon API and micro-friction observers
            </p>
          </div>

          {/* Legend */}
          <div className="flex items-center space-x-3 text-xs">
            <span className="flex items-center space-x-1.5 text-white/70">
              <span className="w-2 h-2 rounded-full bg-[#5e6ad2]" aria-hidden="true" />
              <span>Conversion Flow</span>
            </span>
            <span className="flex items-center space-x-1.5 text-rose-400">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" aria-hidden="true" />
              <span>Friction Drop-off</span>
            </span>
          </div>
        </div>

        {/* Step Items List */}
        <div className="space-y-5">
          {steps.map((step, idx) => {
            const count = step.sessions_count || step.count || 0;
            const pct = Math.max(10, Math.round((count / maxCount) * 100));
            const stepName = step.step_name || step.name || step.event;
            const dropOffPct = step.drop_off_percentage || step.drop_off_pct || 0;
            const isBottleneck = step.bottleneck || dropOffPct > 40;

            return (
              <div key={idx} className="space-y-2.5">
                
                {/* Step Metadata Header */}
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2.5">
                    <span className="w-5 h-5 rounded-lg bg-white/[0.05] border border-white/[0.08] text-white/80 font-mono text-[10px] font-bold flex items-center justify-center">
                      {idx + 1}
                    </span>
                    <span className="font-semibold text-white tracking-tight">{stepName}</span>
                    <span className="text-white/40 font-mono text-[10px]">({step.event})</span>
                  </div>

                  <div className="flex items-center space-x-3 tabular-nums">
                    <span className="font-bold text-white text-sm">
                      {count.toLocaleString()} <span className="text-xs font-normal text-white/40">sessions</span>
                    </span>
                    <span className="text-xs font-medium text-white/50 px-2 py-0.5 rounded-md bg-white/[0.03] border border-white/[0.06]">
                      {step.conversion_from_previous || step.conversion_pct}% of prev
                    </span>
                  </div>
                </div>

                {/* Visual Telemetry Bar */}
                <div className="w-full h-8 rounded-xl bg-[#030508] p-1 border border-white/[0.06] relative overflow-hidden flex items-center">
                  <div
                    style={{ width: `${pct}%` }}
                    className={`h-full rounded-lg transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] flex items-center justify-between px-3 ${
                      isBottleneck
                        ? 'bg-gradient-to-r from-amber-600/80 via-rose-600/90 to-rose-500 shadow-[0_0_15px_rgba(244,63,94,0.3)]'
                        : 'bg-gradient-to-r from-[#5e6ad2] to-[#7985ea] shadow-[0_0_15px_rgba(94,106,210,0.25)]'
                    }`}
                  >
                    <span className="text-[10px] font-bold text-white drop-shadow tabular-nums">
                      {step.conversion_pct || step.conversion_from_previous}%
                    </span>
                  </div>
                </div>

                {/* Drop-off & Friction Detail Row */}
                {idx > 0 && dropOffPct > 0 && (
                  <div className="flex flex-wrap items-center justify-between gap-2 pl-7 pr-1 text-[11px] pt-0.5">
                    <div className="flex items-center space-x-1.5 text-rose-400 font-medium tabular-nums">
                      <ArrowDown className="w-3 h-3 text-rose-400" aria-hidden="true" />
                      <span>
                        Drop-off: {dropOffPct}% ({step.drop_off_count ? `${step.drop_off_count} users dropped` : 'churned'})
                      </span>
                    </div>

                    {step.friction_reason && (
                      <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/25 text-amber-300 font-medium">
                        <AlertTriangle className="w-3 h-3 text-amber-400" aria-hidden="true" />
                        <span>{step.friction_reason}</span>
                      </div>
                    )}

                    {step.friction_signals && Object.keys(step.friction_signals).length > 0 && (
                      <div className="flex items-center space-x-2 text-[10px] text-white/40 font-mono">
                        {Object.entries(step.friction_signals).map(([sigKey, sigVal]) => (
                          <span key={sigKey} className="px-1.5 py-0.5 rounded bg-white/[0.03] border border-white/[0.05]">
                            {sigKey.replace(/_/g, ' ')}: {sigVal}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

              </div>
            );
          })}
        </div>

      </div>
    </div>
  );
};
