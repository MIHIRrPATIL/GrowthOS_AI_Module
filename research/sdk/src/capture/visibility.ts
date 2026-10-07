import { EVENTS } from '../constants';

export type VisibilityCallback = (eventName: string, properties: Record<string, any>) => void;

export class VisibilityCaptureModule {
  private callback: VisibilityCallback;
  private lastVisibleTime: number = Date.now();
  private lastHiddenTime: number | null = null;
  private totalVisibleDwellMs: number = 0;
  private isListening: boolean = false;

  constructor(callback: VisibilityCallback) {
    this.callback = callback;
  }

  public start(): void {
    if (typeof document === 'undefined' || this.isListening) return;

    this.lastVisibleTime = Date.now();

    document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    window.addEventListener('focus', () => this.handleFocusChange(true));
    window.addEventListener('blur', () => this.handleFocusChange(false));

    this.isListening = true;
  }

  private handleVisibilityChange(): void {
    try {
      const isHidden = document.hidden;
      const now = Date.now();

      if (isHidden) {
        // User switched away to another tab or minimized window
        const activeDwell = now - this.lastVisibleTime;
        this.totalVisibleDwellMs += activeDwell;
        this.lastHiddenTime = now;

        const currentPath = typeof window !== 'undefined' ? window.location.pathname : '';
        const isCartOrCheckout = /cart|checkout|order/i.test(currentPath);

        this.callback(EVENTS.USER_TAB_SWITCHED_AWAY, {
          active_dwell_seconds_before_switch: Math.round(activeDwell / 1000),
          total_active_dwell_seconds: Math.round(this.totalVisibleDwellMs / 1000),
          page_path: currentPath,
          is_conversion_step: isCartOrCheckout,
          switched_at: new Date(now).toISOString()
        });

        this.callback(EVENTS.TAB_VISIBILITY_CHANGED, {
          visibility_state: 'hidden',
          current_dwell_seconds: Math.round(activeDwell / 1000),
          total_active_dwell_seconds: Math.round(this.totalVisibleDwellMs / 1000)
        });

      } else {
        // User returned back to our tab
        let timeAwaySec = 0;
        if (this.lastHiddenTime) {
          timeAwaySec = Math.round((now - this.lastHiddenTime) / 1000);
        }

        const currentPath = typeof window !== 'undefined' ? window.location.pathname : '';
        const isCartOrCheckout = /cart|checkout|order/i.test(currentPath);

        let durationCategory = 'quick_switch_under_10s';
        if (timeAwaySec >= 60) {
          durationCategory = 'dormant_over_1m';
        } else if (timeAwaySec >= 10) {
          durationCategory = 'comparison_10_60s';
        }

        this.callback(EVENTS.USER_TAB_RETURNED, {
          time_away_seconds: timeAwaySec,
          away_duration_category: durationCategory,
          page_path: currentPath,
          is_conversion_step: isCartOrCheckout,
          returned_at: new Date(now).toISOString()
        });

        // Detect potential coupon search / comparison hunting behavior
        if (isCartOrCheckout && timeAwaySec >= 10 && timeAwaySec <= 180) {
          this.callback(EVENTS.USER_COUPON_HUNT_DETECTED, {
            time_away_seconds: timeAwaySec,
            page_path: currentPath,
            likely_intent: 'coupon_code_or_price_comparison_search',
            recommended_intervention: 'auto_apply_available_coupon_or_loyalty_nudge'
          });
        }

        this.callback(EVENTS.TAB_VISIBILITY_CHANGED, {
          visibility_state: 'visible',
          time_away_seconds: timeAwaySec,
          total_active_dwell_seconds: Math.round(this.totalVisibleDwellMs / 1000)
        });

        this.lastVisibleTime = now;
      }
    } catch {
      // ignore
    }
  }

  private handleFocusChange(isFocused: boolean): void {
    try {
      const now = Date.now();
      if (isFocused) {
        this.lastVisibleTime = now;
        this.callback(EVENTS.USER_WINDOW_FOCUSED, {
          focused_at: new Date(now).toISOString()
        });
      } else {
        this.callback(EVENTS.USER_WINDOW_BLURRED, {
          blurred_at: new Date(now).toISOString(),
          active_dwell_seconds: Math.round((now - this.lastVisibleTime) / 1000)
        });
      }
    } catch {
      // ignore
    }
  }

  public getTotalDwellSeconds(): number {
    const now = Date.now();
    const active = document.hidden ? 0 : now - this.lastVisibleTime;
    return Math.round((this.totalVisibleDwellMs + active) / 1000);
  }
}
