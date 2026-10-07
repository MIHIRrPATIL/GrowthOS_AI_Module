import { MenuItem, CrustOption, SizeOption, Coupon } from '../types/store';

export const SIZE_OPTIONS: SizeOption[] = [
  { id: 'regular', name: 'Regular', serves: 'Serves 1 (4 slices)', priceMultiplier: 1.0 },
  { id: 'medium', name: 'Medium', serves: 'Serves 2 (6 slices)', priceMultiplier: 1.75 },
  { id: 'large', name: 'Large', serves: 'Serves 4 (8 slices)', priceMultiplier: 2.5 }
];

export const CRUST_OPTIONS: CrustOption[] = [
  { id: 'new-hand-tossed', name: 'New Hand Tossed', priceDelta: 0 },
  { id: 'cheese-burst', name: 'Cheese Burst', priceDelta: 99 },
  { id: 'fresh-pan', name: 'Fresh Pan Pizza', priceDelta: 40 },
  { id: 'wheat-thin-crust', name: '100% Wheat Thin Crust', priceDelta: 30 }
];

export const AVAILABLE_COUPONS: Coupon[] = [
  {
    code: 'DOMINOS50',
    description: '50% OFF up to ₹100 on orders above ₹299',
    discountType: 'percentage',
    discountValue: 50,
    minOrderValue: 299
  },
  {
    code: 'WEEKEND20',
    description: 'Flat ₹150 OFF on orders above ₹599',
    discountType: 'flat',
    discountValue: 150,
    minOrderValue: 599
  },
  {
    code: 'CHEESEBURST',
    description: 'Free Cheese Burst Upgrade (Flat ₹99 OFF)',
    discountType: 'flat',
    discountValue: 99,
    minOrderValue: 399
  }
];

export const DOMINOS_MENU: MenuItem[] = [
  // 1. Veg Pizzas
  {
    id: 'PRD-PIZZA-FARMHOUSE',
    name: 'Farmhouse',
    description: 'Delightful combination of onion, crisp capsicum, fresh tomato & grilled mushroom on a rich marinara base.',
    category: 'veg',
    isVeg: true,
    basePrice: 259,
    rating: 4.8,
    reviewCount: 3420,
    isBestseller: true,
    imageUrl: 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=600&q=80',
    customizable: true
  },
  {
    id: 'PRD-PIZZA-PEPPY-PANEER',
    name: 'Peppy Paneer',
    description: 'Flavorful trio of juicy paneer, crisp capsicum with spicy red paprika on freshly baked crust.',
    category: 'veg',
    isVeg: true,
    basePrice: 259,
    rating: 4.7,
    reviewCount: 2890,
    isSpicy: true,
    imageUrl: 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=600&q=80',
    customizable: true
  },
  {
    id: 'PRD-PIZZA-MARGHERITA',
    name: 'Margherita Classic',
    description: 'Authentic Italian classic with 100% real mozzarella cheese on fresh signature herb tomato sauce.',
    category: 'veg',
    isVeg: true,
    basePrice: 99,
    rating: 4.9,
    reviewCount: 5120,
    isBestseller: true,
    imageUrl: 'https://images.unsplash.com/photo-1604382355076-af4b0eb60143?auto=format&fit=crop&w=600&q=80',
    customizable: true
  },
  {
    id: 'PRD-PIZZA-MEXICAN-GREEN-WAVE',
    name: 'Mexican Green Wave',
    description: 'Mexican herbs sprinkled on onion, capsicum, fresh tomato & jalapeno with premium mozzarella.',
    category: 'veg',
    isVeg: true,
    basePrice: 259,
    rating: 4.6,
    reviewCount: 1940,
    isSpicy: true,
    imageUrl: 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=600&q=80',
    customizable: true
  },
  {
    id: 'PRD-PIZZA-CHEESE-VOLCANO-PANEER',
    name: 'Cheese Volcano Peppy Paneer',
    description: 'Center liquid cheese volcano filled with molten cheddar and mozzarella, surrounded by paneer & paprika slices.',
    category: 'cheese-volcano',
    isVeg: true,
    basePrice: 329,
    rating: 4.9,
    reviewCount: 1250,
    isNew: true,
    imageUrl: 'https://images.unsplash.com/photo-1541745537411-b8046dc6d66c?auto=format&fit=crop&w=600&q=80',
    customizable: true
  },

  // 2. Non-Veg Pizzas
  {
    id: 'PRD-PIZZA-PEPPER-BBQ-CHICKEN',
    name: 'Pepper Barbecue Chicken',
    description: 'Pepper barbecue chicken for that extra flavorful kick, topped with signature herbs and gooey mozzarella.',
    category: 'non-veg',
    isVeg: false,
    basePrice: 319,
    rating: 4.8,
    reviewCount: 4200,
    isBestseller: true,
    imageUrl: 'https://images.unsplash.com/photo-1593560708920-61dd98c46a4e?auto=format&fit=crop&w=600&q=80',
    customizable: true
  },
  {
    id: 'PRD-PIZZA-CHICKEN-DOMINATOR',
    name: 'Chicken Dominator',
    description: 'Loaded with double pepper barbecue chicken, peri-peri chicken, chicken tikka & grilled chicken rasher.',
    category: 'non-veg',
    isVeg: false,
    basePrice: 359,
    rating: 4.9,
    reviewCount: 3870,
    isBestseller: true,
    isSpicy: true,
    imageUrl: 'https://images.unsplash.com/photo-1534308983496-4fabb1a015ee?auto=format&fit=crop&w=600&q=80',
    customizable: true
  },
  {
    id: 'PRD-PIZZA-GOLDEN-DELIGHT',
    name: 'Chicken Golden Delight',
    description: 'Double pepper barbecue chicken, golden corn and extra cheese for golden moments.',
    category: 'non-veg',
    isVeg: false,
    basePrice: 319,
    rating: 4.7,
    reviewCount: 2310,
    imageUrl: 'https://images.unsplash.com/photo-1528137871618-79d2761e3fd5?auto=format&fit=crop&w=600&q=80',
    customizable: true
  },

  // 3. Sides & Breads
  {
    id: 'PRD-SIDE-GARLIC-BREADSTICKS',
    name: 'Garlic Breadsticks',
    description: 'Baked to perfection, fresh garlic butter coated breadsticks with sprinkled seasoning.',
    category: 'sides',
    isVeg: true,
    basePrice: 109,
    rating: 4.8,
    reviewCount: 6890,
    isBestseller: true,
    imageUrl: 'https://images.unsplash.com/photo-1619895092538-128341789043?auto=format&fit=crop&w=600&q=80',
    customizable: false
  },
  {
    id: 'PRD-SIDE-STUFFED-GARLIC-BREAD',
    name: 'Stuffed Garlic Bread',
    description: 'Freshly baked garlic bread stuffed with mozzarella cheese, sweet corn & tangy jalapenos.',
    category: 'sides',
    isVeg: true,
    basePrice: 159,
    rating: 4.9,
    reviewCount: 4120,
    imageUrl: 'https://images.unsplash.com/photo-1573140247632-f8fd74997d5c?auto=format&fit=crop&w=600&q=80',
    customizable: false
  },
  {
    id: 'PRD-SIDE-ZINGY-PARCEL',
    name: 'Paneer Zingy Parcel',
    description: 'Snack parcel filled with spicy paneer chunks, creamy harissa sauce and seasoned herbs.',
    category: 'sides',
    isVeg: true,
    basePrice: 49,
    rating: 4.6,
    reviewCount: 2180,
    imageUrl: 'https://images.unsplash.com/photo-1608897013039-887f21d8c804?auto=format&fit=crop&w=600&q=80',
    customizable: false
  },

  // 4. Desserts & Beverages
  {
    id: 'PRD-DESSERT-CHOCO-LAVA',
    name: 'Choco Lava Cake',
    description: 'Warm chocolate cake with a gooey, molten chocolate truffle fudge center.',
    category: 'desserts',
    isVeg: true,
    basePrice: 109,
    rating: 5.0,
    reviewCount: 8940,
    isBestseller: true,
    imageUrl: 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=600&q=80',
    customizable: false
  },
  {
    id: 'PRD-BEV-PEPSI',
    name: 'Pepsi 500ml',
    description: 'Chilled bottle of refreshing sparkling cola.',
    category: 'beverages',
    isVeg: true,
    basePrice: 60,
    rating: 4.7,
    reviewCount: 3100,
    imageUrl: 'https://images.unsplash.com/photo-1629203851122-3726ecdf080e?auto=format&fit=crop&w=600&q=80',
    customizable: false
  }
];
