/**
 * GrowthOS SDK Types & Data Contracts
 * Module 2: Behavior Intelligence SDK
 */

declare module 'posthog-js';

export type ConsentStatus = 'granted' | 'denied' | 'pending';

export interface ConsentConfig {
  analytics: boolean;
  marketing: boolean;
  sessionReplay: boolean;
  required: boolean;
}

export interface GrowthOSConfig {
  projectId: string;
  writeKey?: string;
  workspaceId?: string;
  apiHost?: string;
  posthogHost?: string;
  posthogApiKey?: string;
  usePosthog?: boolean;
  autocapture?: boolean;
  capturePageviews?: boolean;
  captureForms?: boolean;
  captureScroll?: boolean;
  captureUxSignals?: boolean;
  captureKeystrokes?: boolean;
  captureMedia?: boolean;
  capturePerformance?: boolean;
  captureClipboard?: boolean;
  maskAllInputs?: boolean;
  maskTextSelector?: string;
  sessionInactivityMinutes?: number;
  batchSize?: number;
  flushIntervalMs?: number;
  maxQueueSize?: number;
  debug?: boolean;
  consent?: ConsentConfig;
  customEndpoint?: string;
}

export interface PageMetadata {
  url: string;
  path: string;
  title: string;
  referrer: string;
  search: string;
}

export interface UTMMetadata {
  source: string | null;
  medium: string | null;
  campaign: string | null;
  term: string | null;
  content: string | null;
}

export interface DeviceMetadata {
  screen_width: number;
  screen_height: number;
  viewport_width: number;
  viewport_height: number;
  pixel_ratio: number;
  orientation: string;
  user_agent: string;
  browser: string;
  browser_version: string;
  os: string;
  os_version: string;
  device_type: 'mobile' | 'tablet' | 'desktop';
  language: string;
  timezone: string;
  timezone_offset: number;
}

export interface NetworkMetadata {
  effective_type?: string;
  downlink?: number;
  rtt?: number;
  save_data?: boolean;
}

export interface EventEnvelope<T = Record<string, any>> {
  event_id: string;
  event_name: string;
  timestamp: string;
  workspace_id?: string;
  project_id: string;
  anonymous_id: string;
  customer_id?: string;
  session_id: string;
  idempotency_key: string;
  page: PageMetadata;
  utm: UTMMetadata;
  device: DeviceMetadata;
  network?: NetworkMetadata;
  properties: T;
  metadata: {
    sdk_version: string;
    sdk_name: string;
    source: 'client' | 'server';
    environment?: string;
  };
}

export interface UserTraits {
  email?: string;
  name?: string;
  phone?: string;
  tier?: string;
  loyalty_points?: number;
  created_at?: string;
  [key: string]: any;
}

export interface TrackOptions {
  idempotencyKey?: string;
  sendImmediately?: boolean;
}

export interface EngineAdapter {
  name: string;
  init(config: GrowthOSConfig): Promise<void> | void;
  track(envelope: EventEnvelope): void;
  identify(distinctId: string, traits?: UserTraits): void;
  reset(): void;
  setConsent(consent: ConsentConfig): void;
  flush(): Promise<void>;
}
