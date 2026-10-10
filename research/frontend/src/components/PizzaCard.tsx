'use client';

import React, { useState } from 'react';
import { MenuItem, PizzaSize, CrustType } from '../types/store';
import { CRUST_OPTIONS, SIZE_OPTIONS } from '../data/dominos_menu';
import { Star, Plus, Sliders, Flame, Sparkles } from 'lucide-react';
import { useCart } from '../context/CartContext';
import { getGrowthOS } from '../lib/growthos';

interface PizzaCardProps {
  item: MenuItem;
  onOpenCustomizer: (item: MenuItem) => void;
}

export const PizzaCard: React.FC<PizzaCardProps> = ({ item, onOpenCustomizer }) => {
  const { addToCart } = useCart();
  const [selectedSize, setSelectedSize] = useState<PizzaSize>('regular');
  const [selectedCrust, setSelectedCrust] = useState<CrustType>('new-hand-tossed');

  const sizeMultiplier = selectedSize === 'regular' ? 1.0 : selectedSize === 'medium' ? 1.75 : 2.5;
  const crustDelta = selectedCrust === 'cheese-burst' ? 99 : selectedCrust === 'fresh-pan' ? 40 : selectedCrust === 'wheat-thin-crust' ? 30 : 0;
  const calculatedPrice = Math.round(item.basePrice * sizeMultiplier + crustDelta);

  const handleQuickAdd = () => {
    addToCart(item, selectedSize, selectedCrust, false, []);
  };

  const handleCardClick = () => {
    getGrowthOS().track('product.viewed', {
      product_id: item.id,
      name: item.name,
      category: item.category,
      base_price: item.basePrice,
      is_veg: item.isVeg
    });
  };

  return (
    <div
      onClick={handleCardClick}
      className="group relative flex flex-col justify-between rounded-3xl bg-white dark:bg-slate-800/90 border border-slate-200/80 dark:border-slate-700/80 shadow-sm hover:shadow-xl hover:border-slate-300 dark:hover:border-slate-600 transition-all duration-300 overflow-hidden"
    >
      {/* Top Media & Badges */}
      <div className="relative w-full h-48 sm:h-52 overflow-hidden bg-slate-100 dark:bg-slate-900">
        <img
          src={item.imageUrl}
          alt={item.name}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          loading="lazy"
        />

        {/* Veg / Non-Veg Indicator */}
        <div className="absolute top-3 left-3 bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm flex items-center justify-center">
          <div
            className={`w-3.5 h-3.5 border-2 flex items-center justify-center ${
              item.isVeg ? 'border-emerald-600' : 'border-red-600'
            }`}
          >
            <div
              className={`w-1.5 h-1.5 rounded-full ${
                item.isVeg ? 'bg-emerald-600' : 'bg-red-600'
              }`}
            />
          </div>
        </div>

        {/* Badges */}
        <div className="absolute top-3 right-3 flex flex-col space-y-1.5 items-end">
          {item.isBestseller && (
            <span className="flex items-center space-x-1 px-2 py-0.5 rounded-md bg-amber-500 text-white text-[10px] font-black uppercase tracking-wider shadow">
              <Sparkles className="w-3 h-3" />
              <span>Bestseller</span>
            </span>
          )}
          {item.isSpicy && (
            <span className="flex items-center space-x-1 px-2 py-0.5 rounded-md bg-red-600 text-white text-[10px] font-black uppercase tracking-wider shadow">
              <Flame className="w-3 h-3" />
              <span>Spicy</span>
            </span>
          )}
          {item.isNew && (
            <span className="px-2 py-0.5 rounded-md bg-blue-600 text-white text-[10px] font-black uppercase tracking-wider shadow">
              New
            </span>
          )}
        </div>

        {/* Rating overlay */}
        <div className="absolute bottom-3 left-3 flex items-center space-x-1 px-2 py-0.5 rounded-md bg-slate-900/80 backdrop-blur-sm text-amber-400 text-xs font-bold">
          <Star className="w-3.5 h-3.5 fill-current" />
          <span>{item.rating}</span>
          <span className="text-slate-400 text-[10px]">({item.reviewCount})</span>
        </div>
      </div>

      {/* Body Content */}
      <div className="p-5 flex-1 flex flex-col justify-between">
        <div>
          <h3 className="font-extrabold text-base sm:text-lg text-slate-900 dark:text-white leading-tight mb-1">
            {item.name}
          </h3>
          <p className="text-slate-500 dark:text-slate-400 text-xs leading-relaxed line-clamp-2 mb-4">
            {item.description}
          </p>
        </div>

        {/* Size and Crust Quick Selectors for Customizable Items */}
        {item.customizable && (
          <div className="space-y-2 mb-4 pt-2 border-t border-slate-100 dark:border-slate-700/50">
            {/* Size Options */}
            <div className="flex items-center space-x-1.5 bg-slate-100 dark:bg-slate-900/60 p-1 rounded-xl">
              {SIZE_OPTIONS.map((s) => (
                <button
                  key={s.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedSize(s.id);
                  }}
                  className={`flex-1 py-1 text-[11px] font-bold rounded-lg transition-all ${
                    selectedSize === s.id
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm'
                      : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                  }`}
                >
                  {s.name}
                </button>
              ))}
            </div>

            {/* Crust Dropdown */}
            <select
              value={selectedCrust}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => setSelectedCrust(e.target.value as CrustType)}
              className="w-full bg-slate-100 dark:bg-slate-900/60 text-slate-700 dark:text-slate-300 text-xs font-semibold rounded-xl px-2.5 py-1.5 border-none focus:ring-1 focus:ring-blue-500 outline-none"
            >
              {CRUST_OPTIONS.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.priceDelta > 0 ? `(+₹${c.priceDelta})` : ''}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Price & Action Row */}
        <div className="flex items-center justify-between pt-2">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">Price</span>
            <span className="text-lg sm:text-xl font-black text-slate-900 dark:text-white">
              ₹{calculatedPrice}
            </span>
          </div>

          <div className="flex items-center space-x-2">
            {item.customizable && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenCustomizer(item);
                }}
                className="p-2 rounded-xl bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                title="Customize toppings and cheese"
              >
                <Sliders className="w-4 h-4" />
              </button>
            )}

            <button
              onClick={(e) => {
                e.stopPropagation();
                handleQuickAdd();
              }}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white text-xs font-extrabold shadow-md shadow-emerald-600/20 transition-all"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>ADD</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
