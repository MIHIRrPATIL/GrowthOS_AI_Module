'use client';

import React, { useState, useEffect } from 'react';
import { fetchVerticalTemplates, registerCustomEvent } from '../../lib/api';
import { VerticalTemplate, CustomMerchantEvent } from '../../types/merchant';
import {
  Layers,
  Check,
  Plus,
  ShoppingCart,
  Laptop,
  Calendar,
  BookOpen,
  Sparkles,
  ToggleLeft,
  ToggleRight,
  ShieldCheck,
  Code
} from 'lucide-react';

const ICON_MAP: Record<string, any> = {
  ShoppingCart,
  Laptop,
  Calendar,
  BookOpen
};

export default function TemplatesPage() {
  const [verticals, setVerticals] = useState<VerticalTemplate[]>([]);
  const [selectedVerticalId, setSelectedVerticalId] = useState<string>('ecommerce');
  const [customEvents, setCustomEvents] = useState<CustomMerchantEvent[]>([]);
  const [eventStates, setEventStates] = useState<Record<string, boolean>>({});

  // Custom Event Form State
  const [isCreatingCustom, setIsCreatingCustom] = useState<boolean>(false);
  const [customEventName, setCustomEventName] = useState<string>('');
  const [customDescription, setCustomDescription] = useState<string>('');
  const [propKey, setPropKey] = useState<string>('vehicle_model');
  const [propType, setPropType] = useState<string>('string');
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    fetchVerticalTemplates().then((data) => {
      setVerticals(data.verticals);
      setCustomEvents(data.custom_events);
      // Initialize toggle states
      const initialStates: Record<string, boolean> = {};
      data.verticals.forEach((v) => {
        v.modular_events.forEach((e) => {
          initialStates[e.event] = e.enabled;
        });
      });
      setEventStates(initialStates);
    });
  }, []);

  const currentVertical = verticals.find((v) => v.id === selectedVerticalId) || verticals[0];

  const handleToggleEvent = (eventName: string) => {
    setEventStates((prev) => ({
      ...prev,
      [eventName]: !prev[eventName]
    }));
  };

  const handleCreateCustomEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customEventName) return;

    const res = await registerCustomEvent({
      event_name: customEventName.toLowerCase().replace(/\s+/g, '_'),
      description: customDescription,
      vertical: selectedVerticalId,
      properties: [{ name: propKey, type: propType }]
    });

    if (res.status === 'success') {
      setCustomEvents((prev) => [...prev, res.event]);
      setEventStates((prev) => ({ ...prev, [res.event.event]: true }));
      setFeedback(`Custom event '${res.event.event}' registered successfully!`);
      setCustomEventName('');
      setCustomDescription('');
      setTimeout(() => {
        setIsCreatingCustom(false);
        setFeedback(null);
      }, 1200);
    }
  };

  return (
    <div className="space-y-8 pb-12">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-[10px] font-black uppercase mb-1">
            <Layers className="w-3 h-3" />
            <span>Layer 2 & 3 Modular Event Engine</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Vertical Templates & Event Switchboard
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Select your industry vertical template to pre-wire funnel steps, or toggle modular event triggers with zero developer code.
          </p>
        </div>

        <button
          onClick={() => setIsCreatingCustom(true)}
          className="flex items-center space-x-2 px-4 py-2 rounded-2xl bg-blue-600 hover:bg-blue-500 active:scale-95 text-white font-extrabold text-xs shadow-lg shadow-blue-600/25 transition-all self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Define Custom Event</span>
        </button>
      </div>

      {/* 1. Vertical Template Cards Grid */}
      <div className="space-y-3">
        <h2 className="text-sm font-black uppercase tracking-wider text-slate-400">
          Select Business Vertical Template
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {verticals.map((v) => {
            const Icon = ICON_MAP[v.icon] || ShoppingCart;
            const isSelected = v.id === selectedVerticalId;

            return (
              <div
                key={v.id}
                onClick={() => setSelectedVerticalId(v.id)}
                className={`p-5 rounded-3xl border cursor-pointer transition-all space-y-3 ${
                  isSelected
                    ? 'bg-gradient-to-br from-blue-600/20 via-slate-900 to-slate-950 border-blue-500 ring-1 ring-blue-500/30 shadow-xl'
                    : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className={`p-2.5 rounded-2xl ${isSelected ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400'}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  {isSelected && (
                    <span className="text-[10px] font-black uppercase bg-blue-500 text-white px-2 py-0.5 rounded-md flex items-center space-x-1">
                      <Check className="w-3 h-3" />
                      <span>Active</span>
                    </span>
                  )}
                </div>

                <div>
                  <h3 className="text-sm font-black text-white">{v.name}</h3>
                  <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{v.description}</p>
                </div>

                <div className="pt-2 border-t border-slate-800 text-[10px] font-mono text-slate-400">
                  {v.modular_events.length} Modular Triggers
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Suggested Funnel Preview */}
      {currentVertical && (
        <div className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[10px] font-black uppercase text-blue-400 tracking-wider">Suggested Default Funnel</span>
              <h3 className="text-base font-black text-white">{currentVertical.name} Conversion Path</h3>
            </div>
            <span className="text-xs text-slate-400 font-bold">Pre-wired in PostHog</span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {currentVertical.default_funnel.map((step, idx) => (
              <React.Fragment key={step}>
                <div className="flex items-center space-x-2 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-white">
                  <span className="w-4 h-4 rounded-md bg-blue-600/30 text-blue-400 text-[10px] font-black flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <span>{step}</span>
                </div>
                {idx < currentVertical.default_funnel.length - 1 && (
                  <span className="text-slate-600 font-black">→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* 3. Modular Event Trigger Switchboard */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-extrabold text-white">Modular Event Trigger Switchboard</h2>
            <p className="text-xs text-slate-400">Toggle individual events on or off without writing any frontend code.</p>
          </div>
          <span className="text-xs text-emerald-400 font-bold flex items-center space-x-1">
            <ShieldCheck className="w-4 h-4" />
            <span>Zero-Config Autocapture Active</span>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {currentVertical?.modular_events.map((e) => {
            const isEnabled = eventStates[e.event] ?? true;

            return (
              <div
                key={e.event}
                className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 flex items-center justify-between hover:border-slate-700 transition-all"
              >
                <div className="space-y-1 max-w-[80%]">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-black text-white">{e.event}</span>
                    <span className="text-[9px] uppercase px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 font-bold">
                      {e.category}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400">{e.description}</p>
                </div>

                <button
                  onClick={() => handleToggleEvent(e.event)}
                  className={`p-1 rounded-xl transition-all ${
                    isEnabled ? 'text-blue-400 hover:text-blue-300' : 'text-slate-600 hover:text-slate-500'
                  }`}
                >
                  {isEnabled ? <ToggleRight className="w-7 h-7" /> : <ToggleLeft className="w-7 h-7" />}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Custom Events Section (Layer 3) */}
      {customEvents.length > 0 && (
        <div className="space-y-4 pt-4 border-t border-slate-800">
          <h2 className="text-base font-extrabold text-white">Custom Merchant Events (Layer 3)</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {customEvents.map((ce) => (
              <div
                key={ce.event}
                className="p-4 rounded-2xl bg-slate-900/90 border border-purple-500/30 flex items-center justify-between"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-xs font-black text-purple-300">{ce.event}</span>
                    <span className="text-[9px] uppercase px-1.5 py-0.2 rounded bg-purple-500/20 text-purple-300 font-bold">
                      Custom
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400">{ce.description}</p>
                  <div className="text-[10px] text-slate-500 font-mono">
                    Props: {ce.properties.map((p) => `${p.name}: ${p.type}`).join(', ')}
                  </div>
                </div>
                <span className="text-xs text-emerald-400 font-bold">Active</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal: Define Custom Event */}
      {isCreatingCustom && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md bg-slate-900 rounded-3xl border border-slate-800 shadow-2xl p-6 sm:p-8 space-y-6">
            
            <div className="space-y-1">
              <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 text-[10px] font-black uppercase">
                <Code className="w-3 h-3" />
                <span>Layer 3 Custom Event Definition</span>
              </div>
              <h2 className="text-xl font-black text-white">Create Custom Event</h2>
              <p className="text-xs text-slate-400">Define a merchant-specific event trigger with typed payload properties.</p>
            </div>

            <form onSubmit={handleCreateCustomEvent} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300">Event Name (e.g. test_drive_booked)</label>
                <input
                  type="text"
                  required
                  value={customEventName}
                  onChange={(e) => setCustomEventName(e.target.value)}
                  placeholder="e.g. recipe_downloaded"
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-300">Description</label>
                <input
                  type="text"
                  required
                  value={customDescription}
                  onChange={(e) => setCustomDescription(e.target.value)}
                  placeholder="e.g. Triggered when user saves a custom chef pizza recipe"
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300">Property Key</label>
                  <input
                    type="text"
                    value={propKey}
                    onChange={(e) => setPropKey(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white font-mono"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-300">Property Type</label>
                  <select
                    value={propType}
                    onChange={(e) => setPropType(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white"
                  >
                    <option value="string">string</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                    <option value="object">object</option>
                  </select>
                </div>
              </div>

              {feedback && (
                <div className="p-3 rounded-xl bg-emerald-500/15 text-emerald-300 text-xs font-bold">
                  {feedback}
                </div>
              )}

              <div className="flex items-center justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreatingCustom(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-black"
                >
                  Register Event
                </button>
              </div>
            </form>

          </div>
        </div>
      )}

    </div>
  );
}
