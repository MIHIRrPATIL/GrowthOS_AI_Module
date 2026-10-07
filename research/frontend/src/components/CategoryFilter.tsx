'use client';

import React from 'react';
import { PizzaCategory } from '../types/store';
import { Pizza, Flame, Cake, Coffee, Sparkles, UtensilsCrossed } from 'lucide-react';
import { getGrowthOS } from '../lib/growthos';

interface CategoryFilterProps {
  selectedCategory: string;
  onSelectCategory: (category: string) => void;
}

const CATEGORIES = [
  { id: 'all', label: 'All Items', icon: UtensilsCrossed },
  { id: 'veg', label: 'Veg Pizzas', icon: Pizza, color: 'text-emerald-500' },
  { id: 'non-veg', label: 'Non-Veg Pizzas', icon: Pizza, color: 'text-red-500' },
  { id: 'cheese-volcano', label: 'Cheese Volcano', icon: Flame, color: 'text-amber-500' },
  { id: 'sides', label: 'Sides & Breads', icon: Sparkles, color: 'text-orange-500' },
  { id: 'desserts', label: 'Desserts', icon: Cake, color: 'text-pink-500' },
  { id: 'beverages', label: 'Beverages', icon: Coffee, color: 'text-blue-500' }
];

export const CategoryFilter: React.FC<CategoryFilterProps> = ({
  selectedCategory,
  onSelectCategory
}) => {
  const handleSelect = (id: string) => {
    onSelectCategory(id);
    getGrowthOS().track('category.selected', {
      category_id: id,
      previous_category: selectedCategory
    });
  };

  return (
    <div className="flex items-center space-x-2 overflow-x-auto pb-2 scrollbar-none py-1">
      {CATEGORIES.map((cat) => {
        const Icon = cat.icon;
        const isSelected = selectedCategory === cat.id;

        return (
          <button
            key={cat.id}
            onClick={() => handleSelect(cat.id)}
            className={`flex items-center space-x-2 px-4 py-2.5 rounded-2xl text-xs sm:text-sm font-bold whitespace-nowrap transition-all duration-200 ${
              isSelected
                ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-md scale-105'
                : 'bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            <Icon className={`w-4 h-4 ${isSelected ? 'text-white dark:text-slate-900' : cat.color || 'text-slate-500'}`} />
            <span>{cat.label}</span>
          </button>
        );
      })}
    </div>
  );
};
