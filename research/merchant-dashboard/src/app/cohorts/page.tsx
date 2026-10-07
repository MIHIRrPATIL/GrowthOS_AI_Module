'use client';

import React, { useState, useEffect } from 'react';
import { fetchDormantCarts } from '../../lib/api';
import { DormantCohortResponse, DormantCustomer } from '../../types/merchant';
import { RetentionModal } from '../../components/RetentionModal';
import {
  Users,
  Clock,
  Award,
  Smartphone,
  Tag,
  AlertCircle,
  Zap,
  Sparkles,
  CheckCircle2,
  Send,
  HelpCircle
} from 'lucide-react';

export default function CohortsPage() {
  const [cohortData, setCohortData] = useState<DormantCohortResponse | null>(null);
  const [selectedCustomer, setSelectedCustomer] = useState<DormantCustomer | null>(null);
  const [autoRuleEnabled, setAutoRuleEnabled] = useState<boolean>(true);

  useEffect(() => {
    fetchDormantCarts().then(setCohortData);
  }, []);

  const handleActionSuccess = (customerId: string, actionType: string) => {
    if (cohortData) {
      setCohortData({
        ...cohortData,
        customers: cohortData.customers.map((c) =>
          c.customer_id === customerId
            ? { ...c, action_status: `executed (${actionType})` }
            : c
        )
      });
    }
  };

  return (
    <div className="space-y-8 pb-12">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-black uppercase mb-1">
            <Clock className="w-3 h-3" />
            <span>Absence Signal & Retention Hub</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Dormant Carts & Churn Recovery
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Track absence signals (added to cart &gt;1h ago with no purchase) and trigger instant loyalty point fee waivers or WhatsApp recovery links.
          </p>
        </div>

        <div className="flex items-center space-x-2 px-3 py-2 rounded-2xl bg-slate-900 border border-slate-800 text-xs text-slate-300">
          <span className="text-slate-400 font-bold">At-Risk Value:</span>
          <span className="font-black text-white text-sm">₹{cohortData?.total_at_risk_revenue || 947}</span>
        </div>
      </div>

      {/* Conceptual Guide Banner */}
      <div className="p-5 rounded-3xl bg-slate-900/90 border border-slate-800 space-y-2">
        <div className="flex items-center space-x-2 text-blue-400 text-xs font-black uppercase tracking-wider">
          <HelpCircle className="w-4 h-4" />
          <span>Understanding Absence Signals</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed max-w-4xl">
          An <strong className="text-white">Absence Signal</strong> does not track what happened, but what <strong className="text-amber-300">didn't happen</strong> within an expected time window. 
          PostHog identifies the cohort: <code className="bg-slate-950 text-blue-300 px-2 py-0.5 rounded text-[11px] font-mono">performed cart.item_added in last 24h AND did NOT perform purchase.completed</code>. 
          GrowthOS Module 4 immediately surfaces this cohort and triggers retention policies before the lead goes permanently cold.
        </p>
      </div>

      {/* Automated Policy Switchboard */}
      <div className="p-6 rounded-3xl bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-950 border border-indigo-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <Zap className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-extrabold text-white">
              Auto-Pilot: Module 1 Loyalty Delivery Waiver Rule
            </h3>
          </div>
          <p className="text-xs text-slate-400">
            Automatically deduct 60 Loyalty Points to waive the delivery fee if a Gold member hesitates at Step 2 for &gt;45 minutes.
          </p>
        </div>

        <button
          onClick={() => setAutoRuleEnabled(!autoRuleEnabled)}
          className={`px-4 py-2 rounded-xl text-xs font-black transition-all ${
            autoRuleEnabled
              ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/25'
              : 'bg-slate-800 text-slate-400'
          }`}
        >
          {autoRuleEnabled ? '✓ Auto-Pilot Active' : 'Auto-Pilot Paused'}
        </button>
      </div>

      {/* Dormant Cart Customers Table / List */}
      <div className="space-y-4">
        <h2 className="text-base font-extrabold text-white">Active Dormant Carts ({cohortData?.customers.length || 0})</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {cohortData?.customers.map((customer) => (
            <div
              key={customer.customer_id}
              className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 space-y-4 hover:border-slate-700 transition-all"
            >
              {/* Header */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="text-base font-black text-white">{customer.customer_name}</h3>
                    <span
                      className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full ${
                        customer.tier === 'Gold'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {customer.tier} Tier
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5 font-mono">
                    {customer.email} • {customer.phone}
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-lg font-black text-white">₹{customer.cart_total}</div>
                  <div className="text-[10px] text-amber-400 font-bold">{customer.loyalty_points} Points Avail</div>
                </div>
              </div>

              {/* Items in Cart */}
              <div className="p-3 rounded-2xl bg-slate-950 border border-slate-800/80 space-y-1.5 text-xs">
                <span className="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Cart Items:</span>
                <ul className="space-y-1">
                  {customer.cart_items.map((item, idx) => (
                    <li key={idx} className="flex justify-between text-slate-300 text-[11px]">
                      <span>{item.name} <strong className="text-slate-500">(x{item.quantity})</strong></span>
                      <span className="font-mono text-slate-400">₹{item.price}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Friction & Inactivity Summary */}
              <div className="space-y-1 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Dormant Time:</span>
                  <strong className="text-amber-400">{customer.dormant_duration_minutes} minutes ago</strong>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Abandonment Step:</span>
                  <strong className="text-red-400 truncate max-w-[200px]">{customer.abandoned_step}</strong>
                </div>
              </div>

              {/* Action Recommendation */}
              <div className="p-3 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-300 text-xs font-semibold flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-blue-400 shrink-0" />
                <span>Rec: {customer.recommended_action}</span>
              </div>

              {/* Action Button */}
              <div className="pt-1">
                {customer.action_status === 'pending' ? (
                  <button
                    onClick={() => setSelectedCustomer(customer)}
                    className="w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 active:scale-95 text-white font-black text-xs shadow-lg shadow-blue-600/20 flex items-center justify-center space-x-2 transition-all"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Trigger Retention Action</span>
                  </button>
                ) : (
                  <div className="w-full py-2.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-bold flex items-center justify-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>Action Dispatched: {customer.action_status}</span>
                  </div>
                )}
              </div>

            </div>
          ))}
        </div>
      </div>

      {/* Retention Action Dialog */}
      <RetentionModal
        customer={selectedCustomer}
        onClose={() => setSelectedCustomer(null)}
        onSuccess={handleActionSuccess}
      />

    </div>
  );
}
