'use client';

import React from 'react';
import { Tag, Sparkles, Flame, Clock } from 'lucide-react';
import { useCart } from '../context/CartContext';
import { getGrowthOS } from '../lib/growthos';

export const HeroBanner: React.FC = () => {
  const { applyCoupon, setIsCartDrawerOpen } = useCart();

  const handleApplyPromo = (code: string) => {
    applyCoupon(code);
    setIsCartDrawerOpen(true);
    getGrowthOS().track('promo.banner_clicked', {
      promo_code: code,
      banner_campaign: 'weekend_dominos_rush',
      utm_source: 'growthos_storefront',
      utm_medium: 'banner'
    });
  };

  return (
    <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900 text-white p-6 sm:p-10 shadow-2xl border border-slate-800">
      
      {/* Decorative Glow */}
      <div className="absolute top-0 right-0 -mt-12 -mr-12 w-96 h-96 bg-red-600/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-1/3 -mb-12 w-80 h-80 bg-blue-600/20 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 max-w-3xl">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-red-500/20 border border-red-500/30 text-red-300 text-xs font-bold mb-4">
          <Flame className="w-3.5 h-3.5 text-red-400 animate-bounce" />
          <span>EVERYDAY VALUE OFFERS</span>
        </div>

        <h1 className="text-3xl sm:text-5xl font-black tracking-tight leading-tight mb-4">
          Hot & Fresh Pizzas <br />
          <span className="bg-gradient-to-r from-red-400 via-amber-300 to-white bg-clip-text text-transparent">
            Delivered in 20 Minutes
          </span>
        </h1>

        <p className="text-slate-300 text-sm sm:text-base mb-6 max-w-xl">
          Crafted with 100% real mozzarella, hand-stretched dough, and premium toppings. Instrumented with GrowthOS behavioral intelligence.
        </p>

        {/* Promo Code Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          
          <div className="flex items-center justify-between p-3.5 rounded-2xl bg-white/10 backdrop-blur-md border border-white/15 hover:border-white/30 transition-all">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-red-500/30 text-red-300">
                <Tag className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-extrabold text-white">50% OFF Up to ₹100</div>
                <div className="text-[10px] text-slate-300">Min. order ₹299 • Code: <strong>DOMINOS50</strong></div>
              </div>
            </div>
            <button
              onClick={() => handleApplyPromo('DOMINOS50')}
              className="px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 active:scale-95 text-white text-xs font-bold transition-all shadow"
            >
              Apply
            </button>
          </div>

          <div className="flex items-center justify-between p-3.5 rounded-2xl bg-white/10 backdrop-blur-md border border-white/15 hover:border-white/30 transition-all">
            <div className="flex items-center space-x-3">
              <div className="p-2 rounded-xl bg-amber-500/30 text-amber-300">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-extrabold text-white">Flat ₹150 OFF</div>
                <div className="text-[10px] text-slate-300">Weekend Special • Code: <strong>WEEKEND20</strong></div>
              </div>
            </div>
            <button
              onClick={() => handleApplyPromo('WEEKEND20')}
              className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 active:scale-95 text-white text-xs font-bold transition-all shadow"
            >
              Apply
            </button>
          </div>

        </div>
      </div>
    </div>
  );
};
