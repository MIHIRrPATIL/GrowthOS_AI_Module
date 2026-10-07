'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCart } from '../../context/CartContext';
import { getGrowthOS } from '../../lib/growthos';
import {
  MapPin,
  Clock,
  CreditCard,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Smartphone,
  Banknote,
  Lock
} from 'lucide-react';

export default function CheckoutPage() {
  const router = useRouter();
  const { cart, subtotal, discount, deliveryFee, tax, total, appliedCoupon, clearCart, loyalty } = useCart();

  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Form State
  const [formData, setFormData] = useState({
    fullName: 'Rahul Sharma',
    phone: '9876543210',
    address: 'Flat 402, Green Glen Heights, 12th Main Road, Indiranagar',
    city: 'Bengaluru',
    pincode: '560038',
    deliveryInstructions: 'Leave with security guard if not answering bell.'
  });

  const [paymentMethod, setPaymentMethod] = useState<'upi' | 'card' | 'cod'>('upi');
  const [cardNumber, setCardNumber] = useState<string>('4111 1111 1111 1111');
  const [cardExpiry, setCardExpiry] = useState<string>('12/28');
  const [cardCvv, setCardCvv] = useState<string>('123');

  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleProceedToStep2 = (e: React.FormEvent) => {
    e.preventDefault();
    getGrowthOS().track('checkout.step_completed', {
      step_number: 1,
      step_name: 'delivery_address',
      city: formData.city,
      pincode: formData.pincode
    });
    setStep(2);
  };

  const handleProceedToStep3 = () => {
    getGrowthOS().track('checkout.step_completed', {
      step_number: 2,
      step_name: 'delivery_charges_and_slot',
      delivery_fee: deliveryFee
    });
    setStep(3);
  };

  const handleSimulateAbandonment = () => {
    getGrowthOS().track('checkout.abandoned', {
      abandoned_step: step,
      step_name: step === 2 ? 'delivery_fee_friction' : 'payment_screen',
      cart_subtotal: subtotal,
      delivery_fee: deliveryFee,
      reason: 'delivery_charge_hesitation'
    });
    router.push('/');
  };

  const handlePlaceOrder = () => {
    setIsSubmitting(true);
    const orderId = `DOM-${Date.now().toString().slice(-6)}`;

    // Track purchase.completed
    getGrowthOS().track('purchase.completed', {
      order_id: orderId,
      subtotal,
      discount,
      delivery_fee: deliveryFee,
      tax,
      total_amount: total,
      payment_method: paymentMethod,
      coupon_used: appliedCoupon ? appliedCoupon.code : null,
      loyalty_points_earned: Math.round(total / 10),
      items_count: cart.reduce((s, i) => s + i.quantity, 0),
      items: cart.map((i) => ({
        product_id: i.item.id,
        name: i.item.name,
        category: i.item.category,
        quantity: i.quantity,
        unit_price: i.unitPrice,
        size: i.size,
        crust: i.crust
      }))
    });

    clearCart();
    setTimeout(() => {
      router.push(`/order/${orderId}`);
    }, 600);
  };

  if (cart.length === 0 && !isSubmitting) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4">
        <p className="text-4xl">🛒</p>
        <h2 className="text-2xl font-black text-white">Your checkout is empty</h2>
        <p className="text-xs text-slate-400">Please select pizzas from our menu before checking out.</p>
        <button
          onClick={() => router.push('/')}
          className="px-6 py-3 rounded-2xl bg-red-600 text-white font-bold text-sm shadow-lg shadow-red-600/25"
        >
          Return to Menu
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      
      {/* Checkout Progress Stepper */}
      <div className="flex items-center justify-between max-w-lg mx-auto px-4">
        
        <div className="flex items-center space-x-2">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-black ${
            step >= 1 ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400'
          }`}>
            1
          </div>
          <span className="text-xs font-bold text-slate-300">Address</span>
        </div>

        <div className={`flex-1 h-0.5 mx-4 ${step >= 2 ? 'bg-blue-600' : 'bg-slate-800'}`} />

        <div className="flex items-center space-x-2">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-black ${
            step >= 2 ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400'
          }`}>
            2
          </div>
          <span className="text-xs font-bold text-slate-300">Delivery</span>
        </div>

        <div className={`flex-1 h-0.5 mx-4 ${step >= 3 ? 'bg-blue-600' : 'bg-slate-800'}`} />

        <div className="flex items-center space-x-2">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-black ${
            step >= 3 ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400'
          }`}>
            3
          </div>
          <span className="text-xs font-bold text-slate-300">Payment</span>
        </div>

      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Side: Step Content */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* STEP 1: Address & Contact */}
          {step === 1 && (
            <form onSubmit={handleProceedToStep2} className="p-6 sm:p-8 rounded-3xl bg-slate-900/90 border border-slate-800 space-y-6">
              <div className="flex items-center space-x-3 pb-4 border-b border-slate-800">
                <MapPin className="w-5 h-5 text-red-500" />
                <h3 className="text-lg font-black text-white">Delivery Address & Contact</h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-slate-400 block mb-1.5">Full Name</label>
                  <input
                    type="text"
                    name="fullName"
                    required
                    value={formData.fullName}
                    onChange={handleInputChange}
                    className="w-full bg-slate-950 text-white text-sm px-4 py-2.5 rounded-xl border border-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-400 block mb-1.5">Phone Number</label>
                  <input
                    type="tel"
                    name="phone"
                    required
                    value={formData.phone}
                    onChange={handleInputChange}
                    className="w-full bg-slate-950 text-white text-sm px-4 py-2.5 rounded-xl border border-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-400 block mb-1.5">Street Address & Landmark</label>
                <textarea
                  name="address"
                  required
                  rows={2}
                  value={formData.address}
                  onChange={handleInputChange}
                  className="w-full bg-slate-950 text-white text-sm p-4 rounded-xl border border-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-slate-400 block mb-1.5">City</label>
                  <input
                    type="text"
                    name="city"
                    value={formData.city}
                    onChange={handleInputChange}
                    className="w-full bg-slate-950 text-white text-sm px-4 py-2.5 rounded-xl border border-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-400 block mb-1.5">Pincode</label>
                  <input
                    type="text"
                    name="pincode"
                    value={formData.pincode}
                    onChange={handleInputChange}
                    className="w-full bg-slate-950 text-white text-sm px-4 py-2.5 rounded-xl border border-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-3.5 rounded-2xl bg-blue-600 hover:bg-blue-500 active:scale-98 text-white font-extrabold text-sm shadow-xl shadow-blue-600/20 flex items-center justify-center space-x-2 transition-all"
              >
                <span>Continue to Delivery Options</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          )}

          {/* STEP 2: Delivery Charges & Friction Simulation */}
          {step === 2 && (
            <div className="p-6 sm:p-8 rounded-3xl bg-slate-900/90 border border-slate-800 space-y-6 animate-in fade-in">
              <div className="flex items-center space-x-3 pb-4 border-b border-slate-800">
                <Clock className="w-5 h-5 text-amber-400" />
                <h3 className="text-lg font-black text-white">Delivery Slot & Charges</h3>
              </div>

              <div className="p-4 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-between">
                <div>
                  <div className="text-xs font-extrabold text-blue-300">⚡ Domino's Express Delivery</div>
                  <div className="text-[11px] text-slate-400">Guaranteed hot in 20-25 minutes</div>
                </div>
                <span className="text-xs font-black text-emerald-400">ON TIME</span>
              </div>

              {/* Delivery Fee Friction Point Simulation */}
              <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 space-y-2">
                <div className="flex items-center space-x-2 text-amber-400">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-xs font-extrabold">Delivery Fee Notice</span>
                </div>
                <p className="text-xs text-slate-300">
                  A standard delivery fee of <strong>₹{deliveryFee}</strong> applies to orders under ₹800.
                </p>
                {subtotal < 800 && (
                  <p className="text-[11px] text-slate-400">
                    Add ₹{800 - subtotal} more to your cart to qualify for <strong>FREE Delivery</strong>!
                  </p>
                )}
              </div>

              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleSimulateAbandonment}
                  className="flex-1 py-3 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs border border-slate-700 transition-all"
                >
                  Abandon Checkout (Simulate Drop-off)
                </button>

                <button
                  type="button"
                  onClick={handleProceedToStep3}
                  className="flex-1 py-3.5 rounded-2xl bg-blue-600 hover:bg-blue-500 active:scale-98 text-white font-extrabold text-sm shadow-xl shadow-blue-600/20 flex items-center justify-center space-x-2 transition-all"
                >
                  <span>Proceed to Payment</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: Payment Options */}
          {step === 3 && (
            <div className="p-6 sm:p-8 rounded-3xl bg-slate-900/90 border border-slate-800 space-y-6 animate-in fade-in">
              <div className="flex items-center space-x-3 pb-4 border-b border-slate-800">
                <CreditCard className="w-5 h-5 text-emerald-400" />
                <h3 className="text-lg font-black text-white">Select Payment Method</h3>
              </div>

              {/* Payment Tabs */}
              <div className="grid grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => setPaymentMethod('upi')}
                  className={`p-3.5 rounded-2xl border text-center transition-all ${
                    paymentMethod === 'upi'
                      ? 'border-emerald-500 bg-emerald-500/10 text-emerald-300 ring-2 ring-emerald-500/20'
                      : 'border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  <Smartphone className="w-5 h-5 mx-auto mb-1 text-emerald-400" />
                  <div className="text-xs font-extrabold">UPI Instant</div>
                </button>

                <button
                  type="button"
                  onClick={() => setPaymentMethod('card')}
                  className={`p-3.5 rounded-2xl border text-center transition-all ${
                    paymentMethod === 'card'
                      ? 'border-emerald-500 bg-emerald-500/10 text-emerald-300 ring-2 ring-emerald-500/20'
                      : 'border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  <CreditCard className="w-5 h-5 mx-auto mb-1 text-blue-400" />
                  <div className="text-xs font-extrabold">Card (Auto-Masked)</div>
                </button>

                <button
                  type="button"
                  onClick={() => setPaymentMethod('cod')}
                  className={`p-3.5 rounded-2xl border text-center transition-all ${
                    paymentMethod === 'cod'
                      ? 'border-emerald-500 bg-emerald-500/10 text-emerald-300 ring-2 ring-emerald-500/20'
                      : 'border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  <Banknote className="w-5 h-5 mx-auto mb-1 text-amber-400" />
                  <div className="text-xs font-extrabold">Cash on Delivery</div>
                </button>
              </div>

              {/* Card Details (Auto Masked & PII Safe) */}
              {paymentMethod === 'card' && (
                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-4">
                  <div className="flex items-center space-x-2 text-xs text-slate-400 font-semibold">
                    <Lock className="w-3.5 h-3.5 text-emerald-400" />
                    <span>256-Bit Encrypted (Protected by GrowthOS Zero-Leak PII Masking)</span>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-400 block mb-1">Card Number</label>
                    <input
                      type="text"
                      name="card_number"
                      value={cardNumber}
                      onChange={(e) => setCardNumber(e.target.value)}
                      placeholder="4111 1111 1111 1111"
                      className="w-full bg-slate-900 text-white text-sm px-4 py-2.5 rounded-xl border border-slate-800 focus:outline-none"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-bold text-slate-400 block mb-1">Expiry Date</label>
                      <input
                        type="text"
                        name="card_exp"
                        value={cardExpiry}
                        onChange={(e) => setCardExpiry(e.target.value)}
                        placeholder="MM/YY"
                        className="w-full bg-slate-900 text-white text-sm px-4 py-2.5 rounded-xl border border-slate-800 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-bold text-slate-400 block mb-1">CVV</label>
                      <input
                        type="password"
                        name="card_cvv"
                        value={cardCvv}
                        onChange={(e) => setCardCvv(e.target.value)}
                        placeholder="•••"
                        className="w-full bg-slate-900 text-white text-sm px-4 py-2.5 rounded-xl border border-slate-800 focus:outline-none"
                      />
                    </div>
                  </div>
                </div>
              )}

              <button
                type="button"
                onClick={handlePlaceOrder}
                disabled={isSubmitting}
                className="w-full py-4 rounded-2xl bg-emerald-600 hover:bg-emerald-700 active:scale-98 text-white font-black text-base shadow-xl shadow-emerald-600/25 flex items-center justify-center space-x-2 transition-all"
              >
                {isSubmitting ? (
                  <span>Securing Order...</span>
                ) : (
                  <>
                    <CheckCircle2 className="w-5 h-5" />
                    <span>Pay ₹{total} & Confirm Order</span>
                  </>
                )}
              </button>
            </div>
          )}

        </div>

        {/* Right Side: Order Summary */}
        <div className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 h-fit space-y-4">
          <h3 className="text-sm font-black uppercase tracking-wider text-slate-300">
            Order Summary ({cart.reduce((s, i) => s + i.quantity, 0)} Items)
          </h3>

          <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
            {cart.map((i) => (
              <div key={i.cartItemId} className="flex items-center justify-between text-xs">
                <div>
                  <span className="font-extrabold text-white">{i.item.name}</span>
                  <span className="text-slate-500 ml-1">× {i.quantity}</span>
                  <div className="text-[10px] text-slate-400 capitalize">{i.size} • {i.crust.replace(/-/g, ' ')}</div>
                </div>
                <span className="font-bold text-white">₹{i.totalPrice}</span>
              </div>
            ))}
          </div>

          <div className="pt-4 border-t border-slate-800 space-y-2 text-xs text-slate-400">
            <div className="flex justify-between">
              <span>Subtotal</span>
              <span className="font-bold text-white">₹{subtotal}</span>
            </div>
            {discount > 0 && (
              <div className="flex justify-between text-emerald-400 font-bold">
                <span>Discount</span>
                <span>-₹{discount}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span>Delivery Fee</span>
              <span className="font-bold text-white">{deliveryFee === 0 ? 'FREE' : `₹${deliveryFee}`}</span>
            </div>
            <div className="flex justify-between">
              <span>Taxes (5% GST)</span>
              <span className="font-bold text-white">₹{tax}</span>
            </div>
            <div className="flex justify-between text-base font-black text-white pt-2 border-t border-slate-800">
              <span>Total Payable</span>
              <span className="text-red-400">₹{total}</span>
            </div>
          </div>

          <div className="p-3 rounded-2xl bg-slate-950 border border-slate-800/80 text-[11px] text-slate-400 flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>GrowthOS Behavioral Telemetry & Session Replay Active</span>
          </div>

        </div>

      </div>

    </div>
  );
}
