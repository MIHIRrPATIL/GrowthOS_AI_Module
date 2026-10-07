import { STORAGE_KEYS } from './constants';
import { EventEnvelope } from './types';

export class StorageManager {
  private memoryStore: Map<string, string> = new Map();
  private hasLocalStorage: boolean;

  constructor() {
    this.hasLocalStorage = this.checkLocalStorage();
  }

  private checkLocalStorage(): boolean {
    try {
      if (typeof window === 'undefined' || !window.localStorage) return false;
      const testKey = '__growthos_test__';
      window.localStorage.setItem(testKey, testKey);
      window.localStorage.removeItem(testKey);
      return true;
    } catch {
      return false;
    }
  }

  public get(key: string): string | null {
    try {
      if (this.hasLocalStorage) {
        return window.localStorage.getItem(key);
      }
      return this.memoryStore.get(key) || null;
    } catch {
      return this.memoryStore.get(key) || null;
    }
  }

  public set(key: string, value: string): void {
    try {
      if (this.hasLocalStorage) {
        window.localStorage.setItem(key, value);
      }
      this.memoryStore.set(key, value);
    } catch {
      this.memoryStore.set(key, value);
    }
  }

  public remove(key: string): void {
    try {
      if (this.hasLocalStorage) {
        window.localStorage.removeItem(key);
      }
      this.memoryStore.delete(key);
    } catch {
      this.memoryStore.delete(key);
    }
  }

  public getAnonymousId(): string {
    let anonId = this.get(STORAGE_KEYS.ANONYMOUS_ID);
    if (!anonId) {
      anonId = 'anon_' + this.generateUUID();
      this.set(STORAGE_KEYS.ANONYMOUS_ID, anonId);
    }
    return anonId;
  }

  public getCustomerId(): string | null {
    return this.get(STORAGE_KEYS.CUSTOMER_ID);
  }

  public setCustomerId(customerId: string): void {
    this.set(STORAGE_KEYS.CUSTOMER_ID, customerId);
  }

  public clearCustomerId(): void {
    this.remove(STORAGE_KEYS.CUSTOMER_ID);
  }

  public getEventQueue(): EventEnvelope[] {
    const raw = this.get(STORAGE_KEYS.EVENT_QUEUE);
    if (!raw) return [];
    try {
      return JSON.parse(raw);
    } catch {
      return [];
    }
  }

  public saveEventQueue(queue: EventEnvelope[]): void {
    try {
      this.set(STORAGE_KEYS.EVENT_QUEUE, JSON.stringify(queue));
    } catch {
      // ignore storage quota errors
    }
  }

  public generateUUID(): string {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }
}
