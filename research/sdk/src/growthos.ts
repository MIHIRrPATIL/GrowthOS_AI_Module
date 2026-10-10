import { GrowthOSConfig, ConsentConfig, EventEnvelope, UserTraits, TrackOptions, EngineAdapter } from './types';
import { ConfigManager } from './config';
import { StorageManager } from './storage';
import { SessionManager } from './session';
import { Validator } from './validator';
import { SDK_NAME, SDK_VERSION, EVENTS } from './constants';

import { PageviewCapture } from './capture/pageview';
import { AutocaptureModule } from './capture/autocapture';
import { FormCaptureModule } from './capture/forms';
import { ScrollCaptureModule } from './capture/scroll';
import { UxSignalsModule } from './capture/ux_signals';
import { VisibilityCaptureModule } from './capture/visibility';
import { ClipboardCaptureModule } from './capture/clipboard';
import { MediaCaptureModule } from './capture/media';
import { PerformanceCaptureModule } from './capture/performance';
import { KeystrokeCaptureModule } from './capture/keystrokes';

import { PostHogAdapter } from './adapters/posthog_adapter';
import { HttpAdapter } from './adapters/http_adapter';

export class GrowthOSClient {
  private configManager!: ConfigManager;
  private storage!: StorageManager;
  private session!: SessionManager;
  private adapters: EngineAdapter[] = [];
  private listeners: Array<(envelope: EventEnvelope) => void> = [];
  private isInitialized: boolean = false;

  // Capture Modules
  private pageviewCapture?: PageviewCapture;
  private autocaptureModule?: AutocaptureModule;
  private formCapture?: FormCaptureModule;
  private scrollCapture?: ScrollCaptureModule;
  private uxSignals?: UxSignalsModule;
  private keystrokeCapture?: KeystrokeCaptureModule;
  private visibilityCapture?: VisibilityCaptureModule;
  private clipboardCapture?: ClipboardCaptureModule;
  private mediaCapture?: MediaCaptureModule;
  private performanceCapture?: PerformanceCaptureModule;

  public init(config: GrowthOSConfig): this {
    if (this.isInitialized) {
      if (config.debug) console.warn('[GrowthOS] Already initialized. Updating config.');
      this.configManager.update(config);
      return this;
    }

    try {
      this.configManager = new ConfigManager(config);
      this.storage = new StorageManager();
      this.session = new SessionManager(this.storage, this.configManager.get().sessionInactivityMinutes);

      const cfg = this.configManager.get();

      // Initialize Adapters
      if (cfg.usePosthog) {
        const phAdapter = new PostHogAdapter();
        phAdapter.init(cfg);
        this.adapters.push(phAdapter);
      }

      // Always include HTTP adapter for direct GrowthOS backend pipeline
      const httpAdapter = new HttpAdapter(this.storage);
      httpAdapter.init(cfg);
      this.adapters.push(httpAdapter);

      this.isInitialized = true;

      // Initialize Auto-Capture Modules
      this.setupCaptureModules(cfg);

      if (cfg.debug) {
        console.log(`[GrowthOS] SDK v${SDK_VERSION} initialized successfully for project: ${cfg.projectId}`);
      }
    } catch (err) {
      if (config.debug) {
        console.error('[GrowthOS] Initialization error:', err);
      }
    }

    return this;
  }

  private setupCaptureModules(cfg: GrowthOSConfig): void {
    const handleInternalEvent = (eventName: string, properties: Record<string, any>) => {
      this.track(eventName, properties);
    };

    if (cfg.capturePageviews) {
      this.pageviewCapture = new PageviewCapture((eventName, props) => {
        this.scrollCapture?.resetForNewPage();
        this.uxSignals?.resetExitIntent();
        handleInternalEvent(eventName, props);
      });
      this.pageviewCapture.start();
    }

    if (cfg.autocapture) {
      this.autocaptureModule = new AutocaptureModule(handleInternalEvent);
      this.autocaptureModule.start();
    }

    if (cfg.captureForms) {
      this.formCapture = new FormCaptureModule(handleInternalEvent);
      this.formCapture.start();
    }

    if (cfg.captureScroll) {
      this.scrollCapture = new ScrollCaptureModule(handleInternalEvent);
      this.scrollCapture.start();
    }

    if (cfg.captureUxSignals) {
      this.uxSignals = new UxSignalsModule(handleInternalEvent);
      this.uxSignals.start();
    }

    if (cfg.captureKeystrokes) {
      this.keystrokeCapture = new KeystrokeCaptureModule(handleInternalEvent);
      this.keystrokeCapture.start();
    }

    if (cfg.capturePageviews) {
      this.visibilityCapture = new VisibilityCaptureModule(handleInternalEvent);
      this.visibilityCapture.start();
    }

    if (cfg.captureClipboard) {
      this.clipboardCapture = new ClipboardCaptureModule(handleInternalEvent);
      this.clipboardCapture.start();
    }

    if (cfg.captureMedia) {
      this.mediaCapture = new MediaCaptureModule(handleInternalEvent);
      this.mediaCapture.start();
    }

    if (cfg.capturePerformance) {
      this.performanceCapture = new PerformanceCaptureModule(handleInternalEvent);
      this.performanceCapture.start();
    }
  }

  /**
   * Universal event tracking method
   */
  public track<T extends Record<string, any>>(
    eventName: string,
    properties: T = {} as T,
    options?: TrackOptions
  ): void {
    if (!this.isInitialized) {
      console.warn('[GrowthOS] track() called before init(). Call GrowthOS.init() first.');
      return;
    }

    if (!this.configManager.isTrackingAllowed()) {
      return;
    }

    try {
      const cfg = this.configManager.get();
      const now = new Date().toISOString();
      const anonId = this.storage.getAnonymousId();
      const custId = this.storage.getCustomerId() || undefined;
      const sessionId = this.session.getSessionId();

      const sanitizedProps = Validator.sanitizeProperties(properties, cfg.maskAllInputs);
      const idempotencyKey =
        options?.idempotencyKey || Validator.generateIdempotencyKey(eventName, now, anonId);

      const envelope: EventEnvelope<T> = {
        event_id: 'evt_' + this.storage.generateUUID(),
        event_name: eventName,
        timestamp: now,
        workspace_id: cfg.workspaceId,
        project_id: cfg.projectId,
        anonymous_id: anonId,
        customer_id: custId,
        session_id: sessionId,
        idempotency_key: idempotencyKey,
        page: this.session.getPageMetadata(),
        utm: this.session.getUTMMetadata(),
        device: this.session.getDeviceMetadata(),
        network: this.session.getNetworkMetadata(),
        properties: sanitizedProps,
        metadata: {
          sdk_version: SDK_VERSION,
          sdk_name: SDK_NAME,
          source: 'client',
          environment: cfg.debug ? 'development' : 'production'
        }
      };

      // Dispatch to all initialized adapters
      for (const adapter of this.adapters) {
        adapter.track(envelope);
      }

      // Dispatch to QA & Debug listeners
      for (const listener of this.listeners) {
        try {
          listener(envelope);
        } catch {
          // ignore
        }
      }

      if (cfg.debug) {
        console.log(`[GrowthOS] [Event: ${eventName}]`, envelope);
      }
    } catch (e) {
      if (this.configManager?.isDebug()) {
        console.error('[GrowthOS] Failed to track event:', e);
      }
    }
  }

  /**
   * Register a callback listener for all tracked events (ideal for QA overlays, tests, extensions)
   */
  public addListener(callback: (envelope: EventEnvelope) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== callback);
    };
  }

  public on(event: 'event', callback: (envelope: EventEnvelope) => void): () => void {
    return this.addListener(callback);
  }

  /**
   * Links anonymous session to a recognized user ID
   */
  public identify(customerId: string, traits?: UserTraits): void {
    if (!customerId) return;

    this.storage.setCustomerId(customerId);

    for (const adapter of this.adapters) {
      adapter.identify(customerId, traits);
    }

    // Fire user.logged_in event
    this.track(EVENTS.USER_LOGGED_IN, {
      customer_id: customerId,
      ...(traits || {})
    });
  }

  /**
   * Explicitly tracks a pageview
   */
  public page(name?: string, properties: Record<string, any> = {}): void {
    this.track(EVENTS.PAGE_VIEWED, {
      name: name || document.title,
      ...properties
    });
  }

  /**
   * Resets customer identity and starts a fresh anonymous session (e.g. on logout)
   */
  public reset(): void {
    this.storage.clearCustomerId();
    this.session.refreshSession();

    for (const adapter of this.adapters) {
      adapter.reset();
    }

    this.track(EVENTS.USER_LOGGED_OUT, {});
  }

  /**
   * Updates privacy consent settings
   */
  public setConsent(consent: Partial<ConsentConfig>): void {
    this.configManager.update({ consent: { ...this.configManager.get().consent!, ...consent } });
    const fullConsent = this.configManager.get().consent!;
    for (const adapter of this.adapters) {
      adapter.setConsent(fullConsent);
    }
  }

  public optOut(): void {
    this.setConsent({ analytics: false, marketing: false, sessionReplay: false });
  }

  public optIn(): void {
    this.setConsent({ analytics: true, marketing: true, sessionReplay: true });
  }

  public getSessionId(): string {
    return this.session.getSessionId();
  }

  public getAnonymousId(): string {
    return this.storage.getAnonymousId();
  }

  public getCustomerId(): string | null {
    return this.storage.getCustomerId();
  }

  public async flush(): Promise<void> {
    for (const adapter of this.adapters) {
      await adapter.flush();
    }
  }
}

// Global Singleton Instance
export const GrowthOS = new GrowthOSClient();
