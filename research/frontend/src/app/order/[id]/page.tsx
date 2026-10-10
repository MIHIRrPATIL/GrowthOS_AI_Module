'use client';

import React, { use } from 'react';
import Link from 'next/link';
import { CheckCircle2, Flame, Award, ArrowRight, Clock, MapPin, Share2 } from 'lucide-react';

export default function OrderSuccessPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const orderId = resolvedParams.id;

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-8 text-center pb-20">
      
      {/* Success Badge */}
      <div className="space-y-3">
        <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 mx-auto flex items-center justify-center animate-bounce">
          <CheckCircle2 className="w-9 h-9" />
        </div>

        <h1 className="text-3xl font-black text-white tracking-tight">
          Order Confirmed!
        </h1>
        <p className="text-xs text-slate-400">
          Order ID: <strong className="text-white font-mono">{orderId}</strong> • Estimated Delivery in <strong className="text-emerald-400">22 Mins</strong>
        </p>
      </div>

      {/* Live Pizza Tracker */}
      <div className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 text-left space-y-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2">
            <Flame className="w-5 h-5 text-amber-500 animate-pulse" />
            <h3 className="text-sm font-extrabold text-white">Live Domino's Tracker</h3>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
            BAKING IN 450° OVEN
          </span>
        </div>

        <div className="space-y-4">
          
          <div className="flex items-start space-x-3">
            <div className="w-5 h-5 rounded-full bg-emerald-500 text-white flex items-center justify-center text-[10px] font-black mt-0.5">
              ✓
            </div>
            <div>
              <div className="text-xs font-black text-white">Order Accepted & Sent to Kitchen</div>
              <div className="text-[10px] text-slate-500">Store: Indiranagar 100ft Road Kitchen</div>
            </div>
          </div>

          <div className="flex items-start space-x-3">
            <div className="w-5 h-5 rounded-full bg-amber-500 text-white flex items-center justify-center text-[10px] font-black mt-0.5 animate-ping" />
            <div>
              <div className="text-xs font-black text-amber-400">Hand-Tossing Dough & Baking in Oven</div>
              <div className="text-[10px] text-slate-400">Baking at 450°F with 100% Mozzarella</div>
            </div>
          </div>

          <div className="flex items-start space-x-3 opacity-40">
            <div className="w-5 h-5 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center text-[10px] font-black mt-0.5">
              3
            </div>
            <div>
              <div className="text-xs font-black text-white">Quality Check & Hot Packing</div>
              <div className="text-[10px] text-slate-500">Sealed in thermal insulated delivery bag</div>
            </div>
          </div>

          <div className="flex items-start space-x-3 opacity-40">
            <div className="w-5 h-5 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center text-[10px] font-black mt-0.5">
              4
            </div>
            <div>
              <div className="text-xs font-black text-white">Out for Delivery (Rider: Suresh K.)</div>
              <div className="text-[10px] text-slate-500">Delivering to Indiranagar, Bengaluru</div>
            </div>
          </div>

        </div>
      </div>

      {/* Module 1: Loyalty Reward Points Credited */}
      <div className="p-5 rounded-3xl bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent border border-amber-500/20 text-left flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-3 rounded-2xl bg-amber-500/20 text-amber-400">
            <Award className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs font-black text-white">+35 Gold Loyalty Points Earned!</div>
            <div className="text-[10px] text-slate-400">Credited to Rahul Sharma's Gold Wallet</div>
          </div>
        </div>

        <span className="text-xs font-black text-amber-400 bg-amber-500/20 px-3 py-1.5 rounded-xl border border-amber-500/30">
          Total: 285 pts
        </span>
      </div>

      {/* Action CTA */}
      <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-3">
        <Link
          href="/"
          className="w-full sm:w-auto px-8 py-3.5 rounded-2xl bg-red-600 hover:bg-red-700 active:scale-98 text-white font-extrabold text-sm shadow-xl shadow-red-600/25 flex items-center justify-center space-x-2 transition-all"
        >
          <span>Order More Pizzas</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

    </div>
  );
}
