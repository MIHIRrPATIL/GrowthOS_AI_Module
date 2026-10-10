import { EVENTS, UX_THRESHOLDS } from '../constants';
import { Validator } from '../validator';

export type KeystrokeCallback = (eventName: string, properties: Record<string, any>) => void;

interface FieldTypingSession {
  element: HTMLElement;
  fieldName: string;
  formId: string;
  isSensitive: boolean;
  startTime: number;
  lastKeystrokeTime: number;
  keystrokeCount: number;
  backspaceCount: number;
  deleteCount: number;
  flightTimes: number[];
  hesitationPauses: number;
  wasPasted: boolean;
}

export class KeystrokeCaptureModule {
  private callback: KeystrokeCallback;
  private currentSession: FieldTypingSession | null = null;
  private isListening: boolean = false;

  constructor(callback: KeystrokeCallback) {
    this.callback = callback;
  }

  public start(): void {
    if (typeof document === 'undefined' || this.isListening) return;

    document.addEventListener('focusin', this.handleFocusIn.bind(this), true);
    document.addEventListener('focusout', this.handleFocusOut.bind(this), true);
    document.addEventListener('keydown', this.handleKeyDown.bind(this), true);
    document.addEventListener('paste', this.handlePaste.bind(this), true);

    this.isListening = true;
  }

  private handleFocusIn(event: FocusEvent): void {
    const target = event.target as HTMLElement;
    if (!this.isInputField(target)) return;

    const isSensitive = Validator.isElementSensitive(target);
    const form = target.closest('form');
    const formId = form ? (form.id || form.getAttribute('name') || 'form') : 'no_form';
    const fieldName = (target as HTMLInputElement).name || target.id || target.tagName.toLowerCase();

    this.currentSession = {
      element: target,
      fieldName,
      formId,
      isSensitive,
      startTime: Date.now(),
      lastKeystrokeTime: Date.now(),
      keystrokeCount: 0,
      backspaceCount: 0,
      deleteCount: 0,
      flightTimes: [],
      hesitationPauses: 0,
      wasPasted: false
    };
  }

  private handleKeyDown(event: KeyboardEvent): void {
    if (!this.currentSession) return;

    // Strict Privacy: Never track keystroke timings or dynamics on sensitive fields
    if (this.currentSession.isSensitive) {
      return;
    }

    const now = Date.now();
    const flightTime = now - this.currentSession.lastKeystrokeTime;

    this.currentSession.keystrokeCount++;

    // Track hesitation pauses (>1500ms without typing before resuming)
    if (this.currentSession.keystrokeCount > 1 && flightTime > UX_THRESHOLDS.TYPING_PAUSE_HESITATION_MS) {
      this.currentSession.hesitationPauses++;
    }

    if (flightTime > 0 && flightTime < 5000) {
      this.currentSession.flightTimes.push(flightTime);
    }

    // Track correction keys
    if (event.key === 'Backspace') {
      this.currentSession.backspaceCount++;
    } else if (event.key === 'Delete') {
      this.currentSession.deleteCount++;
    }

    this.currentSession.lastKeystrokeTime = now;
  }

  private handlePaste(event: ClipboardEvent): void {
    if (this.currentSession) {
      this.currentSession.wasPasted = true;
    }
  }

  private handleFocusOut(event: FocusEvent): void {
    if (!this.currentSession) return;

    const session = this.currentSession;
    this.currentSession = null;

    // Do not emit typing dynamics on sensitive fields
    if (session.isSensitive) {
      return;
    }

    if (session.keystrokeCount === 0 && !session.wasPasted) {
      return;
    }

    const durationMs = Date.now() - session.startTime;
    const durationSeconds = Math.max(0.5, durationMs / 1000);

    const avgFlightTime =
      session.flightTimes.length > 0
        ? Math.round(session.flightTimes.reduce((a, b) => a + b, 0) / session.flightTimes.length)
        : 0;

    const typingSpeedCpm = Math.round((session.keystrokeCount / durationSeconds) * 60);

    const payload = {
      form_id: session.formId,
      field_name: session.fieldName,
      keystroke_count: session.keystrokeCount,
      backspace_count: session.backspaceCount,
      delete_count: session.deleteCount,
      avg_flight_time_ms: avgFlightTime,
      hesitation_pauses_count: session.hesitationPauses,
      typing_speed_cpm: typingSpeedCpm,
      duration_seconds: Math.round(durationSeconds),
      was_pasted: session.wasPasted
    };

    // 1. Emit general typing dynamics
    this.callback(EVENTS.USER_TYPING_DYNAMICS, payload);

    // 2. Detect Excessive Corrections Friction (e.g. promo code or credit card formatting confusion)
    if (session.backspaceCount >= 5 || (session.keystrokeCount > 8 && session.backspaceCount / session.keystrokeCount > 0.35)) {
      this.callback(EVENTS.USER_EXCESSIVE_CORRECTIONS, {
        form_id: session.formId,
        field_name: session.fieldName,
        backspace_count: session.backspaceCount,
        correction_ratio: parseFloat((session.backspaceCount / session.keystrokeCount).toFixed(2))
      });
    }

    // 3. Detect Form Hesitation Friction
    if (session.hesitationPauses >= 2 || durationSeconds > 15) {
      this.callback(EVENTS.USER_FORM_HESITATION, {
        form_id: session.formId,
        field_name: session.fieldName,
        hesitation_pauses: session.hesitationPauses,
        time_spent_seconds: Math.round(durationSeconds)
      });
    }
  }

  private isInputField(el: HTMLElement): boolean {
    if (!el || !el.tagName) return false;
    const tag = el.tagName.toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select';
  }
}
