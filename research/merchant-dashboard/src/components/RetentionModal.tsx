'use client';

import React, { useState, useEffect } from 'react';
import { DormantCustomer } from '../types/merchant';
import { triggerRetentionAction } from '../lib/api';
import { X, Award, Smartphone, Send, CheckCircle2, ShieldCheck, Tag, Sparkles, ArrowRight, Loader2 } from 'lucide-react';

interface RetentionModalProps {
  customer: DormantCustomer | null;
  onClose: () => void;
  onSuccess: (customerId: string, actionType: string) => void;
}

export const RetentionModal: React.FC<RetentionModalProps> = ({ customer, onClose, onSuccess }) => {
  const [selectedAction, setSelectedAction] = useState<string>('loyalty_delivery_waiver');
  const [couponCode, setCouponCode] = useState<string>('DOMINOS50');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (customer) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [customer, onClose]);

  if (!customer) return null;

  const handleExecute = async () => {
    setIsSubmitting(true);
    const res = await triggerRetentionAction(customer.customer_id, selectedAction, couponCode);
    setIsSubmitting(false);

    if (res.success) {
      setFeedback(res.message);
      setTimeout(() => {
        onSuccess(customer.customer_id, selectedAction);
        onClose();
      }, 1000);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="retention-modal-title"
    >
      {/* Modal Double-Bezel Container */}
      <div className="relative w-full max-w-lg rounded-[2rem] p-1 bg-gradient-to-b from-white/[0.12] to-white/[0.04] border border-white/[0.1] shadow-2xl">
        <div className="rounded-[calc(2rem-4px)] bg-[#090b10] p-6 sm:p-8 space-y-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
          
          {/* Close Button */}
          <button
            onClick={onClose}
            className="absolute top-6 right-6 p-2 rounded-full bg-white/[0.04] hover:bg-white/[0.1] border border-white/[0.08] text-white/50 hover:text-white transition-all active:scale-95 focus-visible:ring-2 focus-visible:ring-[#5e6ad2]/50 focus-visible:outline-none"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>

          {/* Header */}
          <div className="space-y-1.5 pr-8">
            <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-[#5e6ad2]/15 border border-[#5e6ad2]/30 text-[#828fff] text-[10px] font-bold uppercase tracking-wider">
              <Sparkles className="w-3 h-3 text-[#5e6ad2]" aria-hidden="true" />
              <span>Module 1 & 4 Retention Action</span>
            </div>
            <h2 id="retention-modal-title" className="text-xl font-bold text-white tracking-tight">
              Recover Cart for {customer.customer_name}
            </h2>
            <p className="text-xs text-white/50 font-normal">
              {customer.tier} Tier • {customer.loyalty_points} Points Balance • ₹{customer.cart_total} At Risk
            </p>
          </div>

          {/* Abandonment Diagnostic Context */}
          <div className="rounded-2xl p-4 bg-white/[0.02] border border-white/[0.06] space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-white/40">Dormant Duration:</span>
              <span className="font-semibold text-amber-400 font-mono tabular-nums">
                {customer.dormant_duration_minutes} mins inactive
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-white/40">Friction Point:</span>
              <span className="font-semibold text-rose-300 truncate max-w-[240px]">
                {customer.abandoned_step}
              </span>
            </div>
            <div className="pt-2 border-t border-white/[0.04] text-[11px] text-white/50">
              <span className="font-medium text-white/70">Cart Items: </span>
              {customer.cart_items.map((i) => `${i.name} (x${i.quantity})`).join(', ')}
            </div>
          </div>

          {/* Action Policy Selection */}
          <div className="space-y-2.5">
            <label className="text-[10px] font-bold uppercase tracking-[0.16em] text-white/40 block">
              Select Automated Retention Action
            </label>

            {/* Option 1: Loyalty Fee Waiver */}
            <div
              onClick={() => setSelectedAction('loyalty_delivery_waiver')}
              className={`p-4 rounded-2xl border cursor-pointer transition-all duration-200 ${
                selectedAction === 'loyalty_delivery_waiver'
                  ? 'border-[#5e6ad2] bg-[#5e6ad2]/10 ring-1 ring-[#5e6ad2]/30 text-white'
                  : 'border-white/[0.06] bg-white/[0.02] text-white/60 hover:text-white hover:border-white/[0.12]'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <div className="w-6 h-6 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                    <Award className="w-3.5 h-3.5" aria-hidden="true" />
                  </div>
                  <div className="text-xs font-semibold text-white">Auto-Waive Delivery Fee (Use 60 Loyalty Pts)</div>
                </div>
                <span className="text-[9px] font-bold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full">
                  AI Recommended
                </span>
              </div>
              <p className="text-[11px] text-white/40 mt-2 pl-8 leading-relaxed">
                Deducts 60 points from customer&apos;s existing balance to zero out delivery charges and triggers direct notification.
              </p>
            </div>

            {/* Option 2: WhatsApp Link */}
            <div
              onClick={() => setSelectedAction('whatsapp_cart_link')}
              className={`p-4 rounded-2xl border cursor-pointer transition-all duration-200 ${
                selectedAction === 'whatsapp_cart_link'
                  ? 'border-[#5e6ad2] bg-[#5e6ad2]/10 ring-1 ring-[#5e6ad2]/30 text-white'
                  : 'border-white/[0.06] bg-white/[0.02] text-white/60 hover:text-white hover:border-white/[0.12]'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2.5">
                  <div className="w-6 h-6 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                    <Smartphone className="w-3.5 h-3.5" aria-hidden="true" />
                  </div>
                  <div className="text-xs font-semibold text-white">Direct 1-Click WhatsApp Recovery</div>
                </div>
                <span className="text-[9px] font-mono text-white/40">WhatsApp API</span>
              </div>
              <p className="text-[11px] text-white/40 mt-2 pl-8 leading-relaxed">
                Dispatches a rich pre-filled cart restore link to {customer.phone}.
              </p>
            </div>
          </div>

          {/* Feedback or Action Footer */}
          {feedback ? (
            <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center space-x-2.5 text-emerald-300 text-xs font-semibold animate-in fade-in" aria-live="polite">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" aria-hidden="true" />
              <span>{feedback}</span>
            </div>
          ) : (
            <div className="pt-2 flex items-center justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 rounded-full text-xs font-semibold text-white/60 hover:text-white hover:bg-white/[0.04] transition-colors focus-visible:ring-2 focus-visible:ring-white/20 focus-visible:outline-none"
              >
                Cancel
              </button>

              {/* Button-in-Button CTA */}
              <button
                type="button"
                onClick={handleExecute}
                disabled={isSubmitting}
                className="group relative inline-flex items-center pl-5 pr-2 py-2 rounded-full bg-[#5e6ad2] hover:bg-[#6c78e3] active:scale-[0.98] text-white font-semibold text-xs transition-all shadow-[0_0_24px_rgba(94,106,210,0.4)] disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-[#5e6ad2] focus-visible:outline-none"
              >
                <span className="mr-3">
                  {isSubmitting ? 'Executing Policy…' : 'Dispatch Retention Action'}
                </span>
                <span className="w-7 h-7 rounded-full bg-white/15 flex items-center justify-center transition-transform group-hover:translate-x-0.5 group-hover:scale-105" aria-hidden="true">
                  {isSubmitting ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <ArrowRight className="w-3.5 h-3.5" />
                  )}
                </span>
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};
