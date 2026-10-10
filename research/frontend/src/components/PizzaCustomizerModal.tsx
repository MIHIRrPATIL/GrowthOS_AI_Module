'use client';

import React, { useState } from 'react';
import { MenuItem, PizzaSize, CrustType } from '../types/store';
import { SIZE_OPTIONS, CRUST_OPTIONS } from '../data/dominos_menu';
import { X, Check, Sparkles, Plus } from 'lucide-react';
import { useCart } from '../context/CartContext';
import { getGrowthOS } from '../lib/growthos';

interface PizzaCustomizerModalProps {
  item: MenuItem | null;
  onClose: () => void;
}

const VEG_TOPPINGS = [
  { id: 'mushroom', name: 'Grilled Mushroom', price: 40 },
  { id: 'paprika', name: 'Red Paprika', price: 40 },
  { id: 'capsicum', name: 'Crisp Capsicum', price: 40 },
  { id: 'jalapeno', name: 'Jalapenos', price: 40 },
  { id: 'olive', name: 'Black Olives', price: 40 },
  { id: 'paneer_chunk', name: 'Fresh Paneer Cubes', price: 50 }
];

export const PizzaCustomizerModal: React.FC<PizzaCustomizerModalProps> = ({ item, onClose }) => {
  const { addToCart } = useCart();
  const [selectedSize, setSelectedSize] = useState<PizzaSize>('regular');
  const [selectedCrust, setSelectedCrust] = useState<CrustType>('new-hand-tossed');
  const [extraCheese, setExtraCheese] = useState<boolean>(false);
  const [selectedToppings, setSelectedToppings] = useState<string[]>([]);

  if (!item) return null;

  const sizeMultiplier = selectedSize === 'regular' ? 1.0 : selectedSize === 'medium' ? 1.75 : 2.5;
  const crustDelta = selectedCrust === 'cheese-burst' ? 99 : selectedCrust === 'fresh-pan' ? 40 : selectedCrust === 'wheat-thin-crust' ? 30 : 0;
  const cheeseCost = extraCheese ? 75 : 0;
  const toppingsCost = selectedToppings.length * 40;

  const calculatedTotal = Math.round(item.basePrice * sizeMultiplier + crustDelta + cheeseCost + toppingsCost);

  const toggleTopping = (toppingName: string) => {
    setSelectedToppings((prev) =>
      prev.includes(toppingName) ? prev.filter((t) => t !== toppingName) : [...prev, toppingName]
    );
  };

  const handleAddToCart = () => {
    addToCart(item, selectedSize, selectedCrust, extraCheese, selectedToppings);

    getGrowthOS().track('product.customized', {
      product_id: item.id,
      name: item.name,
      size: selectedSize,
      crust: selectedCrust,
      extra_cheese: extraCheese,
      toppings_count: selectedToppings.length,
      toppings: selectedToppings,
      total_price: calculatedTotal
    });

    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl max-h-[90vh] overflow-y-auto bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 p-6 sm:p-8">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-start space-x-4 mb-6">
          <img
            src={item.imageUrl}
            alt={item.name}
            className="w-20 h-20 rounded-2xl object-cover border border-slate-200 dark:border-slate-700 shadow"
          />
          <div>
            <span className="text-[10px] font-black uppercase tracking-wider text-blue-600 dark:text-blue-400">
              Customize Your Pizza
            </span>
            <h2 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white">
              {item.name}
            </h2>
            <p className="text-xs text-slate-500 line-clamp-2 mt-0.5">{item.description}</p>
          </div>
        </div>

        {/* Section 1: Choose Size */}
        <div className="mb-6">
          <label className="text-xs font-black uppercase text-slate-400 tracking-wider block mb-2.5">
            1. Select Pizza Size
          </label>
          <div className="grid grid-cols-3 gap-2.5">
            {SIZE_OPTIONS.map((s) => (
              <button
                key={s.id}
                onClick={() => setSelectedSize(s.id)}
                className={`p-3 rounded-2xl border text-left transition-all ${
                  selectedSize === s.id
                    ? 'border-blue-600 bg-blue-50/50 dark:bg-blue-950/40 text-blue-900 dark:text-blue-100 ring-2 ring-blue-600/20'
                    : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-700 dark:text-slate-300'
                }`}
              >
                <div className="font-extrabold text-sm">{s.name}</div>
                <div className="text-[10px] text-slate-500">{s.serves}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Section 2: Choose Crust */}
        <div className="mb-6">
          <label className="text-xs font-black uppercase text-slate-400 tracking-wider block mb-2.5">
            2. Select Crust Type
          </label>
          <div className="space-y-2">
            {CRUST_OPTIONS.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedCrust(c.id)}
                className={`w-full flex items-center justify-between p-3.5 rounded-2xl border text-left transition-all ${
                  selectedCrust === c.id
                    ? 'border-blue-600 bg-blue-50/50 dark:bg-blue-950/40 text-blue-900 dark:text-blue-100 ring-2 ring-blue-600/20'
                    : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-700 dark:text-slate-300'
                }`}
              >
                <div className="font-bold text-xs sm:text-sm">{c.name}</div>
                <div className="text-xs font-extrabold text-slate-900 dark:text-white">
                  {c.priceDelta > 0 ? `+₹${c.priceDelta}` : 'Free'}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Section 3: Extra Cheese */}
        <div className="mb-6">
          <label className="text-xs font-black uppercase text-slate-400 tracking-wider block mb-2.5">
            3. Cheese Upgrades
          </label>
          <div
            onClick={() => setExtraCheese(!extraCheese)}
            className={`flex items-center justify-between p-3.5 rounded-2xl border cursor-pointer transition-all ${
              extraCheese
                ? 'border-amber-500 bg-amber-500/10 text-amber-900 dark:text-amber-100 ring-2 ring-amber-500/20'
                : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-700 dark:text-slate-300'
            }`}
          >
            <div className="flex items-center space-x-2.5">
              <div
                className={`w-5 h-5 rounded-md border flex items-center justify-center ${
                  extraCheese ? 'bg-amber-500 border-amber-500 text-white' : 'border-slate-300 dark:border-slate-600'
                }`}
              >
                {extraCheese && <Check className="w-3.5 h-3.5" />}
              </div>
              <span className="font-bold text-xs sm:text-sm">Extra Mozzarella Cheese (100g)</span>
            </div>
            <span className="text-xs font-black text-slate-900 dark:text-white">+₹75</span>
          </div>
        </div>

        {/* Section 4: Extra Veg Toppings */}
        <div className="mb-6">
          <label className="text-xs font-black uppercase text-slate-400 tracking-wider block mb-2.5">
            4. Add Extra Toppings (+₹40 each)
          </label>
          <div className="grid grid-cols-2 gap-2">
            {VEG_TOPPINGS.map((top) => {
              const isSelected = selectedToppings.includes(top.name);
              return (
                <button
                  key={top.id}
                  onClick={() => toggleTopping(top.name)}
                  className={`flex items-center justify-between p-2.5 rounded-xl border text-xs font-semibold transition-all ${
                    isSelected
                      ? 'border-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-200 ring-1 ring-emerald-600'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:border-slate-300'
                  }`}
                >
                  <span>{top.name}</span>
                  <span className="font-bold">{isSelected ? '✓' : '+₹40'}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Footer Checkout Row */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-800">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Price</span>
            <span className="text-2xl font-black text-slate-900 dark:text-white">₹{calculatedTotal}</span>
          </div>

          <button
            onClick={handleAddToCart}
            className="flex items-center space-x-2 px-6 py-3 rounded-2xl bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white font-extrabold text-sm shadow-lg shadow-emerald-600/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add to Cart</span>
          </button>
        </div>

      </div>
    </div>
  );
};
