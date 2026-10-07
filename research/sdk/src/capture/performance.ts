import { EVENTS } from '../constants';

export type PerformanceCallback = (eventName: string, properties: Record<string, any>) => void;

export class PerformanceCaptureModule {
  private callback: PerformanceCallback;
  private metrics: Record<string, number> = {};
  private reported: boolean = false;

  constructor(callback: PerformanceCallback) {
    this.callback = callback;
  }

  public start(): void {
    if (typeof window === 'undefined' || typeof PerformanceObserver === 'undefined') return;

    try {
      // 1. Observe Largest Contentful Paint (LCP)
      const lcpObserver = new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        const lastEntry = entries[entries.length - 1];
        if (lastEntry) {
          this.metrics.lcp_ms = Math.round(lastEntry.startTime);
        }
      });
      lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });

      // 2. Observe Cumulative Layout Shift (CLS)
      let clsValue = 0;
      const clsObserver = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries() as any[]) {
          if (!entry.hadRecentInput) {
            clsValue += entry.value;
          }
        }
        this.metrics.cls_score = parseFloat(clsValue.toFixed(4));
      });
      clsObserver.observe({ type: 'layout-shift', buffered: true });

      // 3. Observe First Input Delay (FID)
      const fidObserver = new PerformanceObserver((entryList) => {
        const firstInput = entryList.getEntries()[0] as any;
        if (firstInput) {
          this.metrics.fid_ms = Math.round(firstInput.processingStart - firstInput.startTime);
        }
      });
      fidObserver.observe({ type: 'first-input', buffered: true });

      // Schedule report after page load completes
      if (document.readyState === 'complete') {
        setTimeout(() => this.collectAndReport(), 1000);
      } else {
        window.addEventListener('load', () => {
          setTimeout(() => this.collectAndReport(), 1000);
        });
      }
    } catch {
      // ignore
    }
  }

  private collectAndReport(): void {
    if (this.reported || typeof performance === 'undefined') return;

    try {
      const navTiming = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      if (navTiming) {
        this.metrics.ttfb_ms = Math.round(navTiming.responseStart - navTiming.requestStart);
        this.metrics.dom_interactive_ms = Math.round(navTiming.domInteractive);
        this.metrics.dom_complete_ms = Math.round(navTiming.domComplete);
        this.metrics.load_event_ms = Math.round(navTiming.loadEventEnd);
      }

      // First Contentful Paint
      const paintEntries = performance.getEntriesByType('paint');
      const fcp = paintEntries.find((p) => p.name === 'first-contentful-paint');
      if (fcp) {
        this.metrics.fcp_ms = Math.round(fcp.startTime);
      }

      this.reported = true;
      this.callback(EVENTS.PERFORMANCE_WEB_VITALS, this.metrics);
    } catch {
      // ignore
    }
  }
}
