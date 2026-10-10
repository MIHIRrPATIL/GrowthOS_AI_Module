import { EventEnvelope, GrowthOSConfig } from './types';
import { StorageManager } from './storage';

export class TransportManager {
  private config: GrowthOSConfig;
  private storage: StorageManager;
  private queue: EventEnvelope[] = [];
  private flushTimer: any = null;
  private isFlushing: boolean = false;
  private retryCount: number = 0;

  constructor(config: GrowthOSConfig, storage: StorageManager) {
    this.config = config;
    this.storage = storage;

    // Restore persisted queue if any
    this.queue = this.storage.getEventQueue();

    this.startPeriodicFlush();
    this.setupUnloadHandler();
  }

  public enqueue(envelope: EventEnvelope, sendImmediately: boolean = false): void {
    if (this.queue.length >= (this.config.maxQueueSize || 500)) {
      this.queue.shift(); // Evict oldest event if max queue reached
    }

    this.queue.push(envelope);
    this.storage.saveEventQueue(this.queue);

    if (sendImmediately || this.queue.length >= (this.config.batchSize || 15)) {
      this.flush();
    }
  }

  public async flush(): Promise<void> {
    if (this.isFlushing || this.queue.length === 0) return;

    this.isFlushing = true;
    const batch = [...this.queue];
    const endpoint = this.config.customEndpoint || `${this.config.apiHost}/api/v1/events/batch`;

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-GrowthOS-Project-ID': this.config.projectId,
          'X-GrowthOS-Workspace-ID': this.config.workspaceId || ''
        },
        body: JSON.stringify({ events: batch }),
        keepalive: true
      });

      if (response.ok) {
        // Remove successfully sent items
        this.queue = this.queue.slice(batch.length);
        this.storage.saveEventQueue(this.queue);
        this.retryCount = 0;
      } else {
        this.handleFlushError();
      }
    } catch (err) {
      this.handleFlushError();
    } finally {
      this.isFlushing = false;
    }
  }

  private handleFlushError(): void {
    this.retryCount++;
    const backoffMs = Math.min(30000, 1000 * Math.pow(2, this.retryCount));
    if (this.config.debug) {
      console.warn(`[GrowthOS] Flush failed. Retrying in ${backoffMs}ms (Attempt ${this.retryCount})`);
    }
    setTimeout(() => this.flush(), backoffMs);
  }

  private startPeriodicFlush(): void {
    const interval = this.config.flushIntervalMs || 3000;
    this.flushTimer = setInterval(() => {
      if (this.queue.length > 0) {
        this.flush();
      }
    }, interval);
  }

  private setupUnloadHandler(): void {
    if (typeof window === 'undefined') return;

    const handleUnload = () => {
      if (this.queue.length === 0) return;

      const endpoint = this.config.customEndpoint || `${this.config.apiHost}/api/v1/events/batch`;
      const payload = JSON.stringify({ events: this.queue });

      if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
        const blob = new Blob([payload], { type: 'application/json' });
        navigator.sendBeacon(endpoint, blob);
      } else {
        fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: payload,
          keepalive: true
        });
      }
    };

    window.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        handleUnload();
      }
    });

    window.addEventListener('pagehide', handleUnload);
  }

  public getQueueLength(): number {
    return this.queue.length;
  }
}
