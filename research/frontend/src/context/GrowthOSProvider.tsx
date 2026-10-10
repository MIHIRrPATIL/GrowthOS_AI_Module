'use client';

import React, { createContext, useContext, useEffect, useState, Suspense } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { getGrowthOS, EventEnvelope } from '../lib/growthos';

interface GrowthOSContextType {
  capturedEvents: EventEnvelope[];
  clearLogs: () => void;
  isQAOpen: boolean;
  setIsQAOpen: (open: boolean) => void;
  anonymousId: string;
  customerId: string;
}

const GrowthOSContext = createContext<GrowthOSContextType | undefined>(undefined);

function RouteTracker() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    const sdk = getGrowthOS();
    sdk.page();
  }, [pathname, searchParams]);

  return null;
}

export const GrowthOSProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [capturedEvents, setCapturedEvents] = useState<EventEnvelope[]>([]);
  const [isQAOpen, setIsQAOpen] = useState<boolean>(false);
  const [anonymousId, setAnonymousId] = useState<string>('');
  const [customerId, setCustomerId] = useState<string>('');

  useEffect(() => {
    const sdk = getGrowthOS();

    // Auto-identify with active demo profile
    sdk.identify('CUST-48291', {
      name: 'Rahul Sharma',
      email: 'rahul.sharma@example.in',
      tier: 'Gold',
      city: 'Bengaluru'
    });

    setAnonymousId(sdk.getAnonymousId());
    setCustomerId(sdk.getCustomerId() || '');

    // Register live event listener for DevTools QA
    const unsubscribe = sdk.addListener((envelope) => {
      setCapturedEvents((prev) => [envelope, ...prev.slice(0, 49)]);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const clearLogs = () => setCapturedEvents([]);

  return (
    <GrowthOSContext.Provider
      value={{
        capturedEvents,
        clearLogs,
        isQAOpen,
        setIsQAOpen,
        anonymousId,
        customerId
      }}
    >
      <Suspense fallback={null}>
        <RouteTracker />
      </Suspense>
      {children}
    </GrowthOSContext.Provider>
  );
};

export const useGrowthOS = () => {
  const context = useContext(GrowthOSContext);
  if (!context) {
    throw new Error('useGrowthOS must be used within GrowthOSProvider');
  }
  return context;
};
