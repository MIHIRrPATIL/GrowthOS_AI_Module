import posthog from 'posthog-js';
import { EngineAdapter, EventEnvelope, GrowthOSConfig, ConsentConfig, UserTraits } from '../types';

export class PostHogAdapter implements EngineAdapter {
  public name = 'PostHogAdapter';
  private client: any = null;
  private isInitialized = false;

  public async init(config: GrowthOSConfig): Promise<void> {
    if (typeof window === 'undefined') return;

    try {
      const apiKey = config.posthogApiKey || config.projectId;
      const apiHost = config.posthogHost || 'https://us.i.posthog.com';

      // Check if global posthog instance exists or use bundled import
      this.client = (window as any).posthog || posthog;

      if (this.client && typeof this.client.init === 'function') {
        this.client.init(apiKey, {
          api_host: apiHost,
          autocapture: Boolean(config.autocapture),
          capture_pageview: false, // GrowthOS handles pageviews explicitly
          capture_pageleave: true,
          disable_session_recording: !config.consent?.sessionReplay,
          mask_all_element_attributes: false,
          mask_all_text: Boolean(config.maskAllInputs),
          opt_out_capturing_by_default: config.consent?.required && !config.consent?.analytics,
          loaded: (ph: any) => {
            if (config.debug) {
              console.log('[GrowthOS] PostHog engine initialized successfully.');
            }
          }
        });
        this.isInitialized = true;
      }
    } catch (e) {
      if (config.debug) {
        console.error('[GrowthOS] Failed to initialize PostHog adapter:', e);
      }
    }
  }

  public track(envelope: EventEnvelope): void {
    if (!this.client || !this.isInitialized) return;

    try {
      this.client.capture(envelope.event_name, {
        ...envelope.properties,
        $current_url: envelope.page.url,
        $pathname: envelope.page.path,
        $referrer: envelope.page.referrer,
        $device_type: envelope.device.device_type,
        $screen_width: envelope.device.screen_width,
        $screen_height: envelope.device.screen_height,
        workspace_id: envelope.workspace_id,
        project_id: envelope.project_id,
        session_id: envelope.session_id,
        idempotency_key: envelope.idempotency_key,
        growthos_event_id: envelope.event_id,
        sdk_version: envelope.metadata.sdk_version
      });
    } catch (e) {
      // Fail silently
    }
  }

  public identify(distinctId: string, traits?: UserTraits): void {
    if (!this.client || !this.isInitialized) return;
    try {
      this.client.identify(distinctId, traits);
    } catch (e) {
      // Fail silently
    }
  }

  public reset(): void {
    if (!this.client || !this.isInitialized) return;
    try {
      this.client.reset();
    } catch (e) {
      // Fail silently
    }
  }

  public setConsent(consent: ConsentConfig): void {
    if (!this.client || !this.isInitialized) return;
    try {
      if (consent.analytics) {
        this.client.opt_in_capturing();
      } else {
        this.client.opt_out_capturing();
      }
    } catch (e) {
      // Fail silently
    }
  }

  public async flush(): Promise<void> {
    // PostHog handles its own beacon & flushing on page unload
  }
}
