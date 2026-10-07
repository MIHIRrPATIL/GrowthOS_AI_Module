'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { CartItem, MenuItem, PizzaSize, CrustType, Coupon, LoyaltyProfile } from '../types/store';
import { AVAILABLE_COUPONS } from '../data/dominos_menu';
import { getGrowthOS } from '../lib/growthos';

interface CartContextType {
  cart: CartItem[];
  addToCart: (item: MenuItem, size?: PizzaSize, crust?: CrustType, extraCheese?: boolean, extraToppings?: string[]) => void;
  removeFromCart: (cartItemId: string) => void;
  updateQuantity: (cartItemId: string, quantity: number) => void;
  clearCart: () => void;
  appliedCoupon: Coupon | null;
  applyCoupon: (code: string) => { success: boolean; message: string };
  removeCoupon: () => void;
  loyalty: LoyaltyProfile;
  redeemLoyaltyPoints: boolean;
  setRedeemLoyaltyPoints: (redeem: boolean) => void;
  subtotal: number;
  discount: number;
  deliveryFee: number;
  tax: number;
  total: number;
  totalItemCount: number;
  isCartDrawerOpen: boolean;
  setIsCartDrawerOpen: (open: boolean) => void;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [appliedCoupon, setAppliedCoupon] = useState<Coupon | null>(null);
  const [redeemLoyaltyPoints, setRedeemLoyaltyPoints] = useState<boolean>(false);
  const [isCartDrawerOpen, setIsCartDrawerOpen] = useState<boolean>(false);

  // Default Mock Loyalty User (Domino's Gold Member)
  const [loyalty] = useState<LoyaltyProfile>({
    customerId: 'CUST-48291',
    name: 'Rahul Sharma',
    phone: '+91 98765 43210',
    tier: 'Gold',
    pointsBalance: 250,
    pointsValueRupees: 250
  });

  // Calculate pricing
  const subtotal = cart.reduce((sum, item) => sum + item.totalPrice, 0);

  let discount = 0;
  if (appliedCoupon && subtotal >= appliedCoupon.minOrderValue) {
    if (appliedCoupon.discountType === 'percentage') {
      discount = Math.min(100, Math.round((subtotal * appliedCoupon.discountValue) / 100));
    } else {
      discount = appliedCoupon.discountValue;
    }
  }

  const loyaltyDiscount = redeemLoyaltyPoints ? Math.min(subtotal, loyalty.pointsValueRupees) : 0;
  const totalDiscount = discount + loyaltyDiscount;

  // Domino's standard delivery fee (₹60) - friction point
  const deliveryFee = subtotal > 0 ? (subtotal > 800 ? 0 : 60) : 0;
  const tax = subtotal > 0 ? Math.round((subtotal - totalDiscount) * 0.05) : 0;
  const total = Math.max(0, subtotal - totalDiscount + deliveryFee + tax);
  const totalItemCount = cart.reduce((sum, item) => sum + item.quantity, 0);

  const addToCart = (
    item: MenuItem,
    size: PizzaSize = 'regular',
    crust: CrustType = 'new-hand-tossed',
    extraCheese: boolean = false,
    extraToppings: string[] = []
  ) => {
    const sizeMultiplier = size === 'regular' ? 1.0 : size === 'medium' ? 1.75 : 2.5;
    const crustDelta = crust === 'cheese-burst' ? 99 : crust === 'fresh-pan' ? 40 : crust === 'wheat-thin-crust' ? 30 : 0;
    const extraCheeseCost = extraCheese ? 75 : 0;
    const toppingsCost = extraToppings.length * 40;

    const unitPrice = Math.round(item.basePrice * sizeMultiplier + crustDelta + extraCheeseCost + toppingsCost);
    const cartItemId = `${item.id}-${size}-${crust}-${extraCheese}-${extraToppings.sort().join('_')}`;

    setCart((prev) => {
      const existing = prev.find((i) => i.cartItemId === cartItemId);
      if (existing) {
        return prev.map((i) =>
          i.cartItemId === cartItemId
            ? { ...i, quantity: i.quantity + 1, totalPrice: (i.quantity + 1) * unitPrice }
            : i
        );
      }
      return [
        ...prev,
        {
          cartItemId,
          item,
          size,
          crust,
          quantity: 1,
          unitPrice,
          totalPrice: unitPrice,
          extraCheese,
          extraToppings
        }
      ];
    });

    // Track GrowthOS Event
    const sdk = getGrowthOS();
    sdk.track('cart.item_added', {
      product_id: item.id,
      name: item.name,
      category: item.category,
      size,
      crust,
      unit_price: unitPrice,
      quantity: 1,
      cart_total: subtotal + unitPrice,
      is_veg: item.isVeg
    });

    setIsCartDrawerOpen(true);
  };

  const removeFromCart = (cartItemId: string) => {
    const item = cart.find((i) => i.cartItemId === cartItemId);
    if (item) {
      const sdk = getGrowthOS();
      sdk.track('cart.item_removed', {
        product_id: item.item.id,
        name: item.item.name,
        quantity: item.quantity,
        cart_total: Math.max(0, subtotal - item.totalPrice)
      });
    }

    setCart((prev) => prev.filter((i) => i.cartItemId !== cartItemId));
  };

  const updateQuantity = (cartItemId: string, quantity: number) => {
    if (quantity <= 0) {
      removeFromCart(cartItemId);
      return;
    }
    setCart((prev) =>
      prev.map((i) =>
        i.cartItemId === cartItemId
          ? { ...i, quantity, totalPrice: i.unitPrice * quantity }
          : i
      )
    );
  };

  const clearCart = () => {
    setCart([]);
    setAppliedCoupon(null);
    setRedeemLoyaltyPoints(false);
    getGrowthOS().track('cart.cleared', {});
  };

  const applyCoupon = (code: string): { success: boolean; message: string } => {
    const normalized = code.trim().toUpperCase();
    const coupon = AVAILABLE_COUPONS.find((c) => c.code === normalized);

    if (!coupon) {
      return { success: false, message: 'Invalid coupon code.' };
    }

    if (subtotal < coupon.minOrderValue) {
      return {
        success: false,
        message: `Coupon requires minimum order value of ₹${coupon.minOrderValue}.`
      };
    }

    setAppliedCoupon(coupon);
    getGrowthOS().track('cart.coupon_applied', {
      coupon_code: coupon.code,
      discount_type: coupon.discountType,
      discount_value: coupon.discountValue,
      cart_subtotal: subtotal
    });

    return { success: true, message: `Coupon ${coupon.code} applied successfully!` };
  };

  const removeCoupon = () => {
    setAppliedCoupon(null);
  };

  return (
    <CartContext.Provider
      value={{
        cart,
        addToCart,
        removeFromCart,
        updateQuantity,
        clearCart,
        appliedCoupon,
        applyCoupon,
        removeCoupon,
        loyalty,
        redeemLoyaltyPoints,
        setRedeemLoyaltyPoints,
        subtotal,
        discount: totalDiscount,
        deliveryFee,
        tax,
        total,
        totalItemCount,
        isCartDrawerOpen,
        setIsCartDrawerOpen
      }}
    >
      {children}
    </CartContext.Provider>
  );
};

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
};
