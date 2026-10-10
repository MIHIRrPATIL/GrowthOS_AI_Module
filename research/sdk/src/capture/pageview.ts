import { EVENTS } from '../constants';

export type PageviewCallback = (eventName: string, properties: Record<string, any>) => void;

export class PageviewCapture {
  private callback: PageviewCallback;
  private lastUrl: string = '';
  private isListening: boolean = false;

  constructor(callback: PageviewCallback) {
    this.callback = callback;
  }

  public start(): void {
    if (typeof window === 'undefined' || this.isListening) return;

    this.lastUrl = window.location.href;

    // 1. Initial Pageview
    this.firePageview(false);

    // 2. SPA Navigation: Listen to popstate & hashchange
    window.addEventListener('popstate', () => this.handleUrlChange(true));
    window.addEventListener('hashchange', () => this.handleUrlChange(true));

    // 3. Monkey-patch history.pushState & history.replaceState for SPAs (React, Next.js, Vue)
    this.patchHistoryMethod('pushState');
    this.patchHistoryMethod('replaceState');

    this.isListening = true;
  }

  private patchHistoryMethod(method: 'pushState' | 'replaceState'): void {
    const original = window.history[method];
    if (typeof original === 'function') {
      window.history[method] = (data: any, unused: string, url?: string | URL | null) => {
        const result = (original as any).apply(window.history, [data, unused, url]);
        this.handleUrlChange(true);
        return result;
      };
    }
  }

  private handleUrlChange(isSpa: boolean): void {
    if (typeof window === 'undefined') return;
    const currentUrl = window.location.href;
    if (currentUrl !== this.lastUrl) {
      const previousUrl = this.lastUrl;
      this.lastUrl = currentUrl;
      this.firePageview(isSpa, previousUrl);
    }
  }

  private firePageview(isSpa: boolean, previousUrl?: string): void {
    if (typeof document === 'undefined') return;

    this.callback(EVENTS.PAGE_VIEWED, {
      title: document.title,
      is_spa_transition: isSpa,
      previous_url: previousUrl || null,
      path: window.location.pathname,
      search: window.location.search
    });
  }
}
