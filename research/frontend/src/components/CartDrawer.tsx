'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { X, Trash2, Plus, Minus, Tag, ArrowRight, ShieldCheck, Award } from 'lucide-react';
import { useCart } from '../context/CartContext';
import { getGrowthOS } from '../lib/growthos';

export const CartDrawer: React.FC = () => {
  const router = useRouter();
  const {
    cart,
    removeFromCart,
    updateQuantity,
    subtotal,
    discount,
    deliveryFee,
    tax,
    total,
    appliedCoupon,
    applyCoupon,
    removeCoupon,
    loyalty,
    redeemLoyaltyPoints,
    setRedeemLoyaltyPoints,
    isCartDrawerOpen,
    setIsCartDrawerOpen
  } = useCart();

  const [couponCodeInput, setCouponCodeInput] = useState<string>('');
  const [couponFeedback, setCouponFeedback] = useState<{ success: boolean; message: string } | null>(null);

  if (!isCartDrawerOpen) return null;

  const handleApplyCoupon = (e: React.FormEvent) => {
    e.preventDefault();
    if (!couponCodeInput) return;
    const res = applyCoupon(couponCodeInput);
    setCouponFeedback(res);
    if (res.success) {
      setCouponCodeInput('');
    }
  };

  const handleProceedToCheckout = () => {
    getGrowthOS().track('checkout.started', {
      cart_total: total,
      item_count: cart.reduce((s, i) => s + i.quantity, 0),
      items: cart.map((i) => ({
        product_id: i.item.id,
        name: i.item.name,
        quantity: i.quantity,
        price: i.unitPrice
      })),
      coupon_applied: appliedCoupon ? appliedCoupon.code : null,
      delivery_fee: deliveryFee
    });

    setIsCartDrawerOpen(false);
    router.push('/checkout');
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        onClick={() => setIsCartDrawerOpen(false)}
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity animate-in fade-in"
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col justify-between">
          
          {/* Header */}
          <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <h2 className="text-lg font-black text-slate-900 dark:text-white">Your Order</h2>
              <span className="bg-red-100 dark:bg-red-950/50 text-red-600 dark:text-red-400 text-xs font-black px-2 py-0.5 rounded-full">
                {cart.reduce((s, i) => s + i.quantity, 0)} Items
              </span>
            </div>
            <button
              onClick={() => setIsCartDrawerOpen(false)}
              className="p-2 rounded-full text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Cart Item List */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {cart.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6">
                <div className="w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 mb-4">
                  🍕
                </div>
                <h3 className="font-extrabold text-slate-900 dark:text-white text-base">Your Cart is Empty</h3>
                <p className="text-xs text-slate-500 max-w-xs mt-1">
                  Add some delicious hot pizzas, garlic breads, and choco lava cake to get started.
                </p>
              </div>
            ) : (
              cart.map((cartItem) => (
                <div
                  key={cartItem.cartItemId}
                  className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/80 space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex space-x-3">
                      <img
                        src={cartItem.item.imageUrl}
                        alt={cartItem.item.name}
                        className="w-12 h-12 rounded-xl object-cover border border-slate-200 dark:border-slate-700"
                      />
                      <div>
                        <h4 className="font-extrabold text-sm text-slate-900 dark:text-white leading-tight">
                          {cartItem.item.name}
                        </h4>
                        <div className="text-[11px] text-slate-500 capitalize">
                          {cartItem.size} • {cartItem.crust.replace(/-/g, ' ')}
                        </div>
                        {cartItem.extraCheese && (
                          <div className="text-[10px] text-amber-600 dark:text-amber-400 font-semibold">
                            + Extra Cheese
                          </div>
                        )}
                        {cartItem.extraToppings.length > 0 && (
                          <div className="text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold">
                            + {cartItem.extraToppings.join(', ')}
                          </div>
                        )}
                      </div>
                    </div>

                    <span className="font-black text-sm text-slate-900 dark:text-white">
                      ₹{cartItem.totalPrice}
                    </span>
                  </div>

                  {/* Quantity & Remove */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-200/60 dark:border-slate-700/60">
                    <button
                      onClick={() => removeFromCart(cartItem.cartItemId)}
                      className="text-xs text-slate-400 hover:text-red-600 flex items-center space-x-1 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Remove</span>
                    </button>

                    <div className="flex items-center space-x-2 bg-white dark:bg-slate-900 px-2 py-1 rounded-xl border border-slate-200 dark:border-slate-700">
                      <button
                        onClick={() => updateQuantity(cartItem.cartItemId, cartItem.quantity - 1)}
                        className="p-1 hover:text-red-600 text-slate-600 dark:text-slate-300"
                      >
                        <Minus className="w-3 h-3" />
                      </button>
                      <span className="text-xs font-black px-1.5">{cartItem.quantity}</span>
                      <button
                        onClick={() => updateQuantity(cartItem.cartItemId, cartItem.quantity + 1)}
                        className="p-1 hover:text-emerald-600 text-slate-600 dark:text-slate-300"
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Checkout Footer & Discounts */}
          {cart.length > 0 && (
            <div className="p-6 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 space-y-4">
              
              {/* Coupon Code Input */}
              <div>
                <form onSubmit={handleApplyCoupon} className="flex space-x-2">
                  <div className="relative flex-1">
                    <Tag className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="text"
                      name="coupon_code"
                      value={couponCodeInput}
                      onChange={(e) => setCouponCodeInput(e.target.value)}
                      placeholder="Enter Coupon (e.g. DOMINOS50)"
                      className="w-full bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs font-bold pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500 uppercase"
                    />
                  </div>
                  <button
                    type="submit"
                    className="px-4 py-2.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-xs font-extrabold rounded-xl hover:opacity-90 active:scale-95 transition-all"
                  >
                    Apply
                  </button>
                </form>

                {couponFeedback && (
                  <p className={`text-[11px] mt-1.5 font-medium ${couponFeedback.success ? 'text-emerald-600' : 'text-red-500'}`}>
                    {couponFeedback.message}
                  </p>
                )}

                {appliedCoupon && (
                  <div className="flex items-center justify-between mt-2 p-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-300 font-bold">
                    <span>Coupon <strong>{appliedCoupon.code}</strong> Applied</span>
                    <button onClick={removeCoupon} className="text-red-500 hover:text-red-700 text-[10px]">Remove</button>
                  </div>
                )}
              </div>

              {/* Loyalty Redemption Toggle */}
              <div className="flex items-center justify-between p-3 rounded-2xl bg-amber-500/10 border border-amber-500/20">
                <div className="flex items-center space-x-2">
                  <Award className="w-4 h-4 text-amber-500" />
                  <div>
                    <div className="text-xs font-extrabold text-amber-900 dark:text-amber-200">Redeem Gold Points</div>
                    <div className="text-[10px] text-amber-700 dark:text-amber-400">Balance: {loyalty.pointsBalance} pts (₹{loyalty.pointsValueRupees})</div>
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={redeemLoyaltyPoints}
                  onChange={(e) => setRedeemLoyaltyPoints(e.target.checked)}
                  className="w-4 h-4 accent-amber-600 cursor-pointer"
                />
              </div>

              {/* Bill Details */}
              <div className="space-y-1.5 text-xs text-slate-500 dark:text-slate-400">
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span className="font-bold text-slate-900 dark:text-white">₹{subtotal}</span>
                </div>
                {discount > 0 && (
                  <div className="flex justify-between text-emerald-600 dark:text-emerald-400 font-bold">
                    <span>Discount Savings</span>
                    <span>-₹{discount}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>Delivery Charge</span>
                  <span className="font-bold text-slate-900 dark:text-white">
                    {deliveryFee === 0 ? 'FREE' : `₹${deliveryFee}`}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Taxes (GST 5%)</span>
                  <span className="font-bold text-slate-900 dark:text-white">₹{tax}</span>
                </div>
                <div className="flex justify-between text-sm font-black text-slate-900 dark:text-white pt-2 border-t border-slate-200 dark:border-slate-800">
                  <span>Grand Total</span>
                  <span className="text-lg text-red-600 dark:text-red-400">₹{total}</span>
                </div>
              </div>

              {/* Proceed CTA */}
              <button
                onClick={handleProceedToCheckout}
                className="w-full py-3.5 rounded-2xl bg-red-600 hover:bg-red-700 active:scale-98 text-white font-black text-sm shadow-xl shadow-red-600/25 flex items-center justify-center space-x-2 transition-all"
              >
                <span>Proceed to Checkout</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};
