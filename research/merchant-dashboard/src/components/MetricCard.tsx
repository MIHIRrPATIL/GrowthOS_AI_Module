'use client';

import React from 'react';
import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: LucideIcon;
  trend?: {
    value: string;
    isPositive: boolean;
  };
  highlight?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  highlight = false
}) => {
  return (
    <div
      className={`group relative rounded-xl p-4 transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] ${
        highlight
          ? 'bg-amber-500/[0.09] border border-amber-400/30'
          : 'bg-[#10211c]/80 border border-white/[0.07] hover:border-white/[0.14] hover:bg-[#132820]'
      }`}
    >
      <div className="h-full flex flex-col justify-between">
        {/* Card Header: Eyebrow Title & Icon Shell */}
        <div className="flex items-center justify-between gap-2 mb-4">
          <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-white/50 truncate">
            {title}
          </span>
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center transition-transform duration-300 group-hover:scale-105 ${
              highlight
                ? 'bg-amber-500/15 border border-amber-500/30 text-amber-300'
                : 'bg-[#b7e65c]/10 border border-[#b7e65c]/18 text-[#d7f5a5]'
            }`}
            aria-hidden="true"
          >
            <Icon className="w-4 h-4" />
          </div>
        </div>

        {/* Card Body: Metric Value & Trend Pill */}
        <div className="space-y-1.5">
          <div className="flex items-baseline space-x-2.5">
            <span className="text-2xl sm:text-3xl font-black text-white tracking-[-0.03em] tabular-nums">
              {value}
            </span>
            {trend && (
              <span
                className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-bold tracking-tight border tabular-nums ${
                  trend.isPositive
                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                    : 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                }`}
              >
                {trend.isPositive ? (
                  <TrendingUp className="w-3 h-3" aria-hidden="true" />
                ) : (
                  <TrendingDown className="w-3 h-3" aria-hidden="true" />
                )}
                <span>{trend.value}</span>
              </span>
            )}
          </div>

          <p className="text-xs text-white/50 font-normal leading-relaxed text-pretty">
            {subtitle}
          </p>
        </div>
      </div>
    </div>
  );
};
