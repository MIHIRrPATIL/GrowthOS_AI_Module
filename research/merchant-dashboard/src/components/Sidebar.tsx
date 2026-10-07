'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Filter,
  Users,
  Layers,
  Activity,
  BrainCircuit,
  Store,
  Radio
} from 'lucide-react';

const NAV_ITEMS = [
  { href: '/', label: 'Overview', icon: LayoutDashboard, badge: null },
  { href: '/funnels', label: 'Funnel Analytics', icon: Filter, badge: 'High Friction' },
  { href: '/cohorts', label: 'Dormant Carts', icon: Users, badge: '2 At Risk' },
  { href: '/templates', label: 'Vertical Templates', icon: Layers, badge: '4 Presets' },
  { href: '/live-stream', label: 'Live Telemetry', icon: Activity, badge: 'Active' },
  { href: '/ai-brain', label: 'AI Growth Brain', icon: BrainCircuit, badge: 'Module 4' }
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  return (
    <aside 
      className="hidden w-[272px] bg-[#091511] border-r border-white/[0.07] lg:flex flex-col justify-between p-4 shrink-0 min-h-screen select-none"
      aria-label="Main sidebar navigation"
    >
      
      {/* Top Brand & Navigation Group */}
      <div className="space-y-6">
        
        {/* Brand Header */}
        <div className="flex items-center space-x-3 px-2 pt-2">
          <div className="w-8 h-8 rounded-lg bg-[#b7e65c] flex items-center justify-center text-[#07110f] font-black text-sm border border-[#d8f69e]">
            G
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="font-extrabold text-sm tracking-tight text-white">GrowthOS</span>
              <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-[#b7e65c]/10 text-[#d7f5a5] border border-[#b7e65c]/20">
                Merchant
              </span>
            </div>
            <p className="text-[10px] text-white/40 font-medium">Behavioral Intelligence Layer</p>
          </div>
        </div>

        {/* Tenant / Workspace Selector Card (Double-Bezel) */}
        <div className="rounded-xl p-3 bg-[#10211c] border border-white/[0.07] space-y-2">
            <div className="flex items-center justify-between text-[10px] font-bold tracking-wider text-white/40 uppercase">
              <span>Active Merchant</span>
              <span className="text-[#b7e65c] flex items-center space-x-1 font-mono text-[9px]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#b7e65c]" aria-hidden="true" />
                <span>ONLINE</span>
              </span>
            </div>

            <div className="flex items-center space-x-2.5">
              <div className="w-7 h-7 rounded-lg bg-[#b7e65c]/10 border border-[#b7e65c]/20 flex items-center justify-center text-[#c9ef88] shrink-0">
                <Store className="w-3.5 h-3.5" aria-hidden="true" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-xs font-bold text-white truncate">Domino&apos;s Pizza India</div>
                <div className="text-[10px] text-white/40 font-mono truncate">ws_dominos_in • Port 4000</div>
              </div>
            </div>
        </div>

        {/* Navigation Items */}
        <nav className="space-y-1" aria-label="Sidebar sections">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group relative flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 focus-visible:ring-2 focus-visible:ring-[#5e6ad2]/50 focus-visible:outline-none ${
                  isActive
                    ? 'bg-[#b7e65c]/12 text-white border border-[#b7e65c]/24 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]'
                    : 'text-white/60 hover:text-white hover:bg-white/[0.04] border border-transparent'
                }`}
                aria-current={isActive ? 'page' : undefined}
              >
                <div className="flex items-center space-x-2.5">
                  <Icon
                    className={`w-4 h-4 transition-colors duration-200 ${
                      isActive ? 'text-[#b7e65c]' : 'text-white/40 group-hover:text-white/80'
                    }`}
                    aria-hidden="true"
                  />
                  <span className="tracking-tight">{item.label}</span>
                </div>

                {item.badge && (
                  <span
                    className={`text-[9px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full transition-colors ${
                      isActive
                        ? 'bg-[#b7e65c]/20 text-[#e5f8bd] border border-[#b7e65c]/30'
                        : item.badge === 'High Friction'
                        ? 'bg-amber-500/15 text-amber-300 border border-amber-500/25'
                        : item.badge === '2 At Risk'
                        ? 'bg-red-500/15 text-red-300 border border-red-500/25'
                        : 'bg-white/[0.06] text-white/60 border border-white/[0.08]'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

      </div>

      {/* Bottom Infrastructure & System Status Widget */}
      <div className="space-y-3 pt-4 border-t border-white/[0.06]">
        <div className="rounded-xl p-3 bg-white/[0.025] border border-white/[0.06] space-y-2">
          <div className="flex items-center justify-between text-[10px] font-bold text-white/40 uppercase tracking-wider">
            <span className="flex items-center space-x-1.5">
              <Radio className="w-3 h-3 text-[#b7e65c]" aria-hidden="true" />
              <span>Pipeline Health</span>
            </span>
            <span className="text-[#b7e65c] font-mono text-[9px]">99.98%</span>
          </div>

          <div className="space-y-1 text-[10px] font-mono text-white/60">
            <div className="flex items-center justify-between">
              <span className="text-white/40">PostHog Engine:</span>
              <span className="text-[#c9ef88]">Connected</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-white/40">Bridge Queue:</span>
              <span className="text-white/80">0 ms lag</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-white/40">Module 4 Graph:</span>
              <span className="text-[#c9ef88]">Synced</span>
            </div>
          </div>
        </div>

        <div className="px-2 text-[10px] text-white/30 text-center font-mono">
          GrowthOS Intelligence • v1.0.4
        </div>
      </div>

    </aside>
  );
};
