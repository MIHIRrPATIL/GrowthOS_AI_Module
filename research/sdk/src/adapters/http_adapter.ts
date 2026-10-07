import { EngineAdapter, EventEnvelope, GrowthOSConfig, ConsentConfig, UserTraits } from '../types';
import { TransportManager } from '../transport';
import { StorageManager } from '../storage';

export class HttpAdapter implements EngineAdapter {
  public name = 'HttpAdapter';
  private transport: TransportManager | null = null;
  private storage: StorageManager;
  private isOptedOut: boolean = false;

  constructor(storage: StorageManager) {
    this.storage = storage;
  }

  public init(config: GrowthOSConfig): void {
    this.transport = new TransportManager(config, this.storage);
    if (config.consent?.required && !config.consent?.analytics) {
      this.isOptedOut = true;
    }
  }

  public track(envelope: EventEnvelope): void {
    if (this.isOptedOut || !this.transport) return;
    this.transport.enqueue(envelope);
  }

  public identify(distinctId: string, traits?: UserTraits): void {
    this.storage.setCustomerId(distinctId);
  }

  public reset(): void {
    this.storage.clearCustomerId();
  }

  public setConsent(consent: ConsentConfig): void {
    this.isOptedOut = !consent.analytics;
  }

  public async flush(): Promise<void> {
    if (this.transport) {
      await this.transport.flush();
    }
  }
}
