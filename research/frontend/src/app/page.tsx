'use client';

import React, { useState, useMemo } from 'react';
import { HeroBanner } from '../components/HeroBanner';
import { CategoryFilter } from '../components/CategoryFilter';
import { PizzaCard } from '../components/PizzaCard';
import { PizzaCustomizerModal } from '../components/PizzaCustomizerModal';
import { DOMINOS_MENU } from '../data/dominos_menu';
import { MenuItem } from '../types/store';
import { Search, SlidersHorizontal, Flame, Sparkles, Check } from 'lucide-react';
import { getGrowthOS } from '../lib/growthos';

export default function Home() {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [vegOnly, setVegOnly] = useState<boolean>(false);
  const [bestsellersOnly, setBestsellersOnly] = useState<boolean>(false);
  const [spicyOnly, setSpicyOnly] = useState<boolean>(false);

  const [customizingItem, setCustomizingItem] = useState<MenuItem | null>(null);

  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    if (query.trim().length >= 3) {
      getGrowthOS().track('product.searched', {
        query: query.trim(),
        results_count: filteredItems.length
      });
    }
  };

  const filteredItems = useMemo(() => {
    return DOMINOS_MENU.filter((item) => {
      // Category filter
      if (selectedCategory !== 'all' && item.category !== selectedCategory) {
        return false;
      }
      // Veg toggle
      if (vegOnly && !item.isVeg) {
        return false;
      }
      // Bestseller toggle
      if (bestsellersOnly && !item.isBestseller) {
        return false;
      }
      // Spicy toggle
      if (spicyOnly && !item.isSpicy) {
        return false;
      }
      // Search query
      if (searchQuery.trim() !== '') {
        const q = searchQuery.toLowerCase();
        const matchesName = item.name.toLowerCase().includes(q);
        const matchesDesc = item.description.toLowerCase().includes(q);
        if (!matchesName && !matchesDesc) return false;
      }
      return true;
    });
  }, [selectedCategory, vegOnly, bestsellersOnly, spicyOnly, searchQuery]);

  return (
    <div className="space-y-8 pb-16">
      
      {/* 1. Hero Promo Banner */}
      <HeroBanner />

      {/* 2. Controls & Search Row */}
      <div className="space-y-4">
        
        {/* Search and Quick Filters */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
            <input
              type="text"
              name="search_pizzas"
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search Farmhouse, Peppy Paneer, Garlic Bread..."
              className="w-full bg-slate-900/80 text-white placeholder-slate-500 text-sm pl-10 pr-4 py-2.5 rounded-2xl border border-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            />
          </div>

          {/* Toggle Pills */}
          <div className="flex items-center space-x-2 overflow-x-auto pb-1">
            
            {/* Veg Only */}
            <button
              onClick={() => setVegOnly(!vegOnly)}
              className={`flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-bold transition-all ${
                vegOnly
                  ? 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 ring-1 ring-emerald-500'
                  : 'bg-slate-900/80 border border-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              <div className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>Veg Only</span>
              {vegOnly && <Check className="w-3 h-3 text-emerald-400" />}
            </button>

            {/* Bestsellers */}
            <button
              onClick={() => setBestsellersOnly(!bestsellersOnly)}
              className={`flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-bold transition-all ${
                bestsellersOnly
                  ? 'bg-amber-500/20 border border-amber-500/40 text-amber-300 ring-1 ring-amber-500'
                  : 'bg-slate-900/80 border border-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              <Sparkles className="w-3 h-3 text-amber-400" />
              <span>Bestsellers</span>
            </button>

            {/* Spicy */}
            <button
              onClick={() => setSpicyOnly(!spicyOnly)}
              className={`flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-bold transition-all ${
                spicyOnly
                  ? 'bg-red-500/20 border border-red-500/40 text-red-300 ring-1 ring-red-500'
                  : 'bg-slate-900/80 border border-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              <Flame className="w-3 h-3 text-red-400" />
              <span>Spicy</span>
            </button>

          </div>

        </div>

        {/* Category Tabs */}
        <CategoryFilter
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
        />

      </div>

      {/* 3. Product Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-extrabold text-white tracking-tight">
            {selectedCategory === 'all' ? 'Popular Menu Items' : `${selectedCategory.replace(/-/g, ' ').toUpperCase()}`}
          </h2>
          <span className="text-xs text-slate-400 font-semibold">
            Showing {filteredItems.length} items
          </span>
        </div>

        {filteredItems.length === 0 ? (
          <div className="p-12 rounded-3xl bg-slate-900/40 border border-slate-800 text-center space-y-3">
            <p className="text-3xl">🍕</p>
            <h3 className="text-base font-bold text-white">No matching pizzas found</h3>
            <p className="text-xs text-slate-400">Try changing your search term or filter toggles.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredItems.map((item) => (
              <PizzaCard
                key={item.id}
                item={item}
                onOpenCustomizer={(it) => setCustomizingItem(it)}
              />
            ))}
          </div>
        )}
      </div>

      {/* 4. Pizza Customizer Modal */}
      <PizzaCustomizerModal
        item={customizingItem}
        onClose={() => setCustomizingItem(null)}
      />

    </div>
  );
}
