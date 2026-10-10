'use client';

import React from 'react';
import Link from 'next/link';
import { ShoppingBag, MapPin, Award, Activity, Sparkles } from 'lucide-react';
import { useCart } from '../context/CartContext';
import { useGrowthOS } from '../context/GrowthOSProvider';

export const Navbar: React.FC = () => {
  const { totalItemCount, setIsCartDrawerOpen, loyalty } = useCart();
  const { isQAOpen, setIsQAOpen, capturedEvents } = useGrowthOS();

  return (
    <header className="sticky top-0 z-40 w-full backdrop-blur-md bg-white/90 dark:bg-slate-900/90 border-b border-slate-200 dark:border-slate-800 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand & Location */}
        <div className="flex items-center space-x-6">
          <Link href="/" className="flex items-center space-x-2.5 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-red-600 flex items-center justify-center text-white font-black text-xl shadow-md group-hover:scale-105 transition-transform">
              D
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="font-extrabold text-lg tracking-tight text-slate-900 dark:text-white">
                  Domino's
                </span>
                <span className="text-xs uppercase tracking-wider px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 font-semibold">
                  GrowthOS
                </span>
              </div>
              <p className="text-[10px] text-slate-500 font-medium">Behavior Intelligence Storefront</p>
            </div>
          </Link>

          {/* Delivery Location */}
          <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 text-xs font-medium">
            <MapPin className="w-3.5 h-3.5 text-red-500" />
            <span>Delivering to: <strong className="text-slate-900 dark:text-white">Indiranagar, Bengaluru</strong></span>
            <span className="text-emerald-500 font-semibold ml-1">● 25 Mins</span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-3">
          
          {/* Loyalty Badge */}
          <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 text-xs font-semibold">
            <Award className="w-4 h-4 text-amber-500" />
            <span>{loyalty.tier} Member</span>
            <span className="bg-amber-500 text-white text-[10px] px-1.5 py-0.2 rounded-full font-bold">
              {loyalty.pointsBalance} pts
            </span>
          </div>

          {/* QA Debugger Trigger */}
          <button
            onClick={() => setIsQAOpen(!isQAOpen)}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 text-xs font-semibold hover:bg-indigo-100 dark:hover:bg-indigo-900 transition-colors"
            title="Toggle GrowthOS QA Event Debugger"
          >
            <Activity className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 animate-pulse" />
            <span>QA Stream</span>
            {capturedEvents.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-indigo-600 text-white text-[10px] font-bold">
                {capturedEvents.length}
              </span>
            )}
          </button>

          {/* Cart Trigger */}
          <button
            onClick={() => setIsCartDrawerOpen(true)}
            className="relative flex items-center space-x-2 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 active:scale-95 text-white text-sm font-bold shadow-md shadow-red-500/20 transition-all"
          >
            <ShoppingBag className="w-4 h-4" />
            <span className="hidden sm:inline">Cart</span>
            {totalItemCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 bg-blue-600 text-white text-xs font-black rounded-full w-5 h-5 flex items-center justify-center ring-2 ring-white dark:ring-slate-900">
                {totalItemCount}
              </span>
            )}
          </button>
        </div>

      </div>
    </header>
  );
};
