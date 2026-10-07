import { EVENTS, UX_THRESHOLDS } from '../constants';

export type ScrollCallback = (eventName: string, properties: Record<string, any>) => void;

export class ScrollCaptureModule {
  private callback: ScrollCallback;
  private triggeredMilestones: Set<number> = new Set();
  private maxScrollDepthPercent: number = 0;
  private lastScrollY: number = 0;
  private startTime: number = Date.now();
  private isListening: boolean = false;
  private throttleTimer: any = null;

  constructor(callback: ScrollCallback) {
    this.callback = callback;
  }

  public start(): void {
    if (typeof window === 'undefined' || this.isListening) return;

    this.startTime = Date.now();
    this.lastScrollY = window.scrollY || window.pageYOffset || 0;

    window.addEventListener('scroll', this.handleScrollThrottled.bind(this), { passive: true });
    this.isListening = true;
  }

  private handleScrollThrottled(): void {
    if (this.throttleTimer) return;
    this.throttleTimer = setTimeout(() => {
      this.throttleTimer = null;
      this.calculateScroll();
    }, 150);
  }

  private calculateScroll(): void {
    if (typeof document === 'undefined' || typeof window === 'undefined') return;

    const scrollTop = window.scrollY || window.pageYOffset || document.documentElement.scrollTop || 0;
    const docHeight = Math.max(
      document.body.scrollHeight,
      document.documentElement.scrollHeight,
      document.body.offsetHeight,
      document.documentElement.offsetHeight,
      document.body.clientHeight,
      document.documentElement.clientHeight
    );
    const windowHeight = window.innerHeight || document.documentElement.clientHeight || 1;

    const totalScrollable = docHeight - windowHeight;
    if (totalScrollable <= 0) return;

    const scrollPercentage = Math.min(100, Math.round((scrollTop / totalScrollable) * 100));
    const direction = scrollTop >= this.lastScrollY ? 'down' : 'up';
    this.lastScrollY = scrollTop;

    if (scrollPercentage > this.maxScrollDepthPercent) {
      this.maxScrollDepthPercent = scrollPercentage;
    }

    for (const milestone of UX_THRESHOLDS.SCROLL_MILESTONES) {
      if (scrollPercentage >= milestone && !this.triggeredMilestones.has(milestone)) {
        this.triggeredMilestones.add(milestone);
        const timeToMilestoneMs = Date.now() - this.startTime;

        this.callback(EVENTS.SCROLL_MILESTONE, {
          milestone_percentage: milestone,
          current_scroll_depth_percent: scrollPercentage,
          max_scroll_depth_percent: this.maxScrollDepthPercent,
          scroll_direction: direction,
          scroll_top_px: Math.round(scrollTop),
          document_height_px: Math.round(docHeight),
          time_to_milestone_ms: timeToMilestoneMs
        });
      }
    }
  }

  public resetForNewPage(): void {
    this.triggeredMilestones.clear();
    this.maxScrollDepthPercent = 0;
    this.startTime = Date.now();
    this.lastScrollY = 0;
  }
}
