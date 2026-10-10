import { EVENTS, UX_THRESHOLDS } from '../constants';
import { Validator } from '../validator';

export type UxSignalCallback = (eventName: string, properties: Record<string, any>) => void;

interface ClickRecord {
  x: number;
  y: number;
  time: number;
  target: HTMLElement;
}

export class UxSignalsModule {
  private callback: UxSignalCallback;
  private recentClicks: ClickRecord[] = [];
  private lastClick: ClickRecord | null = null;
  private lastMouseMove: { x: number; y: number; time: number; vy: number } | null = null;
  private exitIntentTriggered: boolean = false;
  private isListening: boolean = false;
  private domMutationObserver: MutationObserver | null = null;
  private recentDomMutations: number = 0;

  constructor(callback: UxSignalCallback) {
    this.callback = callback;
  }

  public start(): void {
    if (typeof document === 'undefined' || this.isListening) return;

    document.addEventListener('click', this.handleClick.bind(this), true);
    document.addEventListener('mousemove', this.handleMouseMove.bind(this), { passive: true });
    window.addEventListener('error', this.handleWindowError.bind(this));

    this.setupMutationObserver();
    this.isListening = true;
  }

  private setupMutationObserver(): void {
    if (typeof MutationObserver === 'undefined') return;
    this.domMutationObserver = new MutationObserver(() => {
      this.recentDomMutations++;
    });

    try {
      this.domMutationObserver.observe(document.body || document.documentElement, {
        childList: true,
        subtree: true,
        attributes: true
      });
    } catch {
      // ignore
    }
  }

  private handleClick(event: MouseEvent): void {
    try {
      const target = (event.target as HTMLElement) || null;
      if (!target || Validator.isElementSensitive(target)) return;

      const now = Date.now();
      const currentClick: ClickRecord = {
        x: event.clientX,
        y: event.clientY,
        time: now,
        target
      };

      this.lastClick = currentClick;

      // 1. Detect Rage Clicks
      this.detectRageClicks(currentClick);

      // 2. Schedule Dead Click Detection
      this.scheduleDeadClickCheck(currentClick);
    } catch {
      // Fail silently
    }
  }

  private detectRageClicks(currentClick: ClickRecord): void {
    this.recentClicks.push(currentClick);

    // Keep only clicks within window
    const cutoff = currentClick.time - UX_THRESHOLDS.RAGE_CLICK_MAX_DELAY_MS;
    this.recentClicks = this.recentClicks.filter((c) => c.time >= cutoff);

    if (this.recentClicks.length >= UX_THRESHOLDS.RAGE_CLICK_MIN_CLICKS) {
      const first = this.recentClicks[0];
      const isClustered = this.recentClicks.every((c) => {
        const dx = Math.abs(c.x - first.x);
        const dy = Math.abs(c.y - first.y);
        return dx <= UX_THRESHOLDS.RAGE_CLICK_RADIUS_PX && dy <= UX_THRESHOLDS.RAGE_CLICK_RADIUS_PX;
      });

      if (isClustered) {
        const clickCount = this.recentClicks.length;
        this.recentClicks = []; // Reset after firing

        this.callback(EVENTS.USER_RAGE_CLICK, {
          click_count: clickCount,
          tag_name: currentClick.target.tagName.toLowerCase(),
          element_id: currentClick.target.id || null,
          class_name: currentClick.target.className || null,
          text_content: Validator.maskSensitiveText((currentClick.target.textContent || '').trim().substring(0, 80)),
          client_x: currentClick.x,
          client_y: currentClick.y
        });
      }
    }
  }

  private scheduleDeadClickCheck(click: ClickRecord): void {
    const mutationsBefore = this.recentDomMutations;
    const initialUrl = window.location.href;

    setTimeout(() => {
      try {
        const mutationsAfter = this.recentDomMutations;
        const currentUrl = window.location.href;

        // If URL changed or DOM mutated, it was not a dead click
        if (currentUrl !== initialUrl || mutationsAfter > mutationsBefore) {
          return;
        }

        const tag = click.target.tagName.toLowerCase();
        // Ignore native form inputs where a click is just focus
        if (['input', 'textarea', 'select'].includes(tag)) {
          return;
        }

        // Element has no standard interactive styling/role but was clicked
        this.callback(EVENTS.USER_DEAD_CLICK, {
          tag_name: tag,
          element_id: click.target.id || null,
          class_name: click.target.className || null,
          text_content: Validator.maskSensitiveText((click.target.textContent || '').trim().substring(0, 80)),
          client_x: click.x,
          client_y: click.y
        });
      } catch {
        // ignore
      }
    }, UX_THRESHOLDS.DEAD_CLICK_MUTATION_TIMEOUT_MS);
  }

  private handleWindowError(event: ErrorEvent): void {
    if (!this.lastClick) return;

    const timeSinceLastClick = Date.now() - this.lastClick.time;
    if (timeSinceLastClick <= UX_THRESHOLDS.ERROR_CLICK_WINDOW_MS) {
      this.callback(EVENTS.USER_ERROR_CLICK, {
        error_message: event.message || 'Unknown script error',
        error_filename: event.filename || null,
        error_lineno: event.lineno || null,
        tag_name: this.lastClick.target.tagName.toLowerCase(),
        element_id: this.lastClick.target.id || null,
        time_since_click_ms: timeSinceLastClick
      });
    }
  }

  private handleMouseMove(event: MouseEvent): void {
    try {
      const now = Date.now();
      const x = event.clientX;
      const y = event.clientY;

      if (this.lastMouseMove) {
        const dt = (now - this.lastMouseMove.time) / 1000;
        if (dt > 0.01 && dt < 0.2) {
          const dy = y - this.lastMouseMove.y;
          const vy = dy / dt; // pixels per second

          // 1. Detect Exit Intent (rapid movement towards top browser toolbar)
          if (vy < UX_THRESHOLDS.EXIT_INTENT_VELOCITY_Y && y < 50 && !this.exitIntentTriggered) {
            this.exitIntentTriggered = true;
            this.callback(EVENTS.USER_EXIT_INTENT, {
              cursor_x: x,
              cursor_y: y,
              velocity_y: Math.round(vy),
              dwell_seconds_before_exit: Math.round((now - (this.lastMouseMove.time || now)) / 1000)
            });
          }

          // 2. Detect Mouse Thrashing
          const dx = x - this.lastMouseMove.x;
          const speed = Math.sqrt(dx * dx + dy * dy) / dt;
          if (speed > UX_THRESHOLDS.MOUSE_THRASHING_ACCELERATION) {
            this.callback(EVENTS.USER_MOUSE_THRASHING, {
              cursor_x: x,
              cursor_y: y,
              speed_px_per_sec: Math.round(speed)
            });
          }
        }
      }

      this.lastMouseMove = { x, y, time: now, vy: 0 };
    } catch {
      // ignore
    }
  }

  public resetExitIntent(): void {
    this.exitIntentTriggered = false;
  }
}
