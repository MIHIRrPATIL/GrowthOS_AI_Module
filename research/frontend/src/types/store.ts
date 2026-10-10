export type PizzaCategory =
  | 'veg'
  | 'non-veg'
  | 'cheese-volcano'
  | 'pizza-mania'
  | 'sides'
  | 'desserts'
  | 'beverages';

export type PizzaSize = 'regular' | 'medium' | 'large';

export type CrustType =
  | 'new-hand-tossed'
  | 'cheese-burst'
  | 'fresh-pan'
  | 'wheat-thin-crust';

export interface CrustOption {
  id: CrustType;
  name: string;
  priceDelta: number;
}

export interface SizeOption {
  id: PizzaSize;
  name: string;
  serves: string;
  priceMultiplier: number;
}

export interface MenuItem {
  id: string;
  name: string;
  description: string;
  category: PizzaCategory;
  isVeg: boolean;
  basePrice: number;
  rating: number;
  reviewCount: number;
  isBestseller?: boolean;
  isSpicy?: boolean;
  isNew?: boolean;
  imageUrl: string;
  customizable?: boolean;
}

export interface CartItem {
  cartItemId: string;
  item: MenuItem;
  size: PizzaSize;
  crust: CrustType;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  extraCheese: boolean;
  extraToppings: string[];
}

export interface Coupon {
  code: string;
  description: string;
  discountType: 'percentage' | 'flat';
  discountValue: number;
  minOrderValue: number;
}

export interface LoyaltyProfile {
  customerId: string;
  name: string;
  phone: string;
  tier: 'Silver' | 'Gold' | 'Platinum';
  pointsBalance: number;
  pointsValueRupees: number;
}
