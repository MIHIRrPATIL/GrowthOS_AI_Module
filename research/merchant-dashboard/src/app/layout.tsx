import type { Metadata } from 'next';
import { Plus_Jakarta_Sans } from 'next/font/google';
import './globals.css';
import { Sidebar } from '../components/Sidebar';
import { Sparkles, ExternalLink, Search, Command, Menu } from 'lucide-react';

const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-jakarta',
  display: 'swap'
});

export const metadata: Metadata = {
  title: 'GrowthOS Merchant Console - Behavior Intelligence & Retention',
  description: 'High-end merchant admin dashboard for funnel diagnostics, dormant cart recovery, and AI Growth Brain orchestration.'
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${jakarta.variable} font-sans bg-[#07110f] text-[#f4f7f2] antialiased min-h-screen flex selection:bg-[#b7e65c] selection:text-[#07110f]`}>
        
        {/* Accessibility Skip Link */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 z-50 px-4 py-2 bg-[#b7e65c] text-[#07110f] rounded-lg text-xs font-bold shadow-2xl focus:outline-none"
        >
          Skip to main content
        </a>

        {/* Left Navigation Sidebar */}
        <Sidebar />

        {/* Right Main Content Shell */}
        <div className="flex-1 flex flex-col min-w-0">
          
          {/* Topbar Navigation Header */}
          <header className="sticky top-0 z-30 h-16 border-b border-white/[0.08] bg-[#07110f]/90 backdrop-blur-xl px-4 sm:px-8 flex items-center justify-between transition-colors">
            
            {/* Left: Store Selector & Environment Pill */}
            <div className="flex min-w-0 items-center gap-2 sm:gap-3">
              <button className="lg:hidden inline-flex h-9 w-9 items-center justify-center rounded-lg border border-white/[0.1] bg-white/[0.03] text-white/70" aria-label="Open navigation">
                <Menu className="h-4 w-4" aria-hidden="true" />
              </button>
              <div className="flex min-w-0 items-center gap-2.5 rounded-lg border border-white/[0.09] bg-white/[0.035] px-3 py-1.5 text-xs font-semibold text-white/90">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#b7e65c]" aria-hidden="true" />
                <span className="truncate font-bold tracking-tight">Domino&apos;s Pizza India</span>
                <span className="hidden text-[10px] text-[#c9ef88] font-mono sm:inline">LIVE</span>
              </div>
            </div>

            {/* Right: Quick Telemetry & Status Badges */}
            <div className="flex items-center space-x-3">
              {/* Quick Search Shortcut */}
              <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.06] text-xs text-white/40">
                <Search className="w-3.5 h-3.5 text-white/40" aria-hidden="true" />
                <span className="text-xs">Search metrics or cohorts</span>
                <kbd className="inline-flex items-center gap-0.5 rounded bg-white/[0.08] px-1.5 py-0.5 text-[10px] font-mono text-white/70 border border-white/[0.08]">
                  <Command className="w-2.5 h-2.5" /> K
                </kbd>
              </div>

              {/* Module 4 AI Brain Status */}
              <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#b7e65c]/10 border border-[#b7e65c]/20 text-[#d7f5a5] text-xs font-semibold">
                <Sparkles className="w-3.5 h-3.5 text-[#b7e65c]" aria-hidden="true" />
                <span>AI Brain Engine Active</span>
              </div>

              {/* Live Storefront Quick Link */}
              <a
                href="http://localhost:3000"
                target="_blank"
                rel="noreferrer"
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] hover:border-white/[0.12] text-xs font-semibold text-white/80 transition-all active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-[#b7e65c]/50 focus-visible:outline-none"
                aria-label="Open storefront in new tab"
              >
                <span>Storefront</span>
                <ExternalLink className="w-3 h-3 text-white/50" aria-hidden="true" />
              </a>
            </div>
          </header>

          {/* Main Page Workspace Container */}
          <main id="main-content" className="flex-1 p-4 sm:p-7 lg:p-9 max-w-[1440px] w-full mx-auto overflow-y-auto">
            {children}
          </main>

        </div>

      </body>
    </html>
  );
}
