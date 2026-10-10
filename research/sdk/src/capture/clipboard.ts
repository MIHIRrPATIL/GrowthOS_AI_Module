import { EVENTS } from '../constants';
import { Validator } from '../validator';

export type ClipboardCallback = (eventName: string, properties: Record<string, any>) => void;

export class ClipboardCaptureModule {
  private callback: ClipboardCallback;
  private isListening: boolean = false;

  constructor(callback: ClipboardCallback) {
    this.callback = callback;
  }

  public start(): void {
    if (typeof document === 'undefined' || this.isListening) return;

    document.addEventListener('copy', this.handleCopy.bind(this), true);
    document.addEventListener('paste', this.handlePaste.bind(this), true);

    this.isListening = true;
  }

  private handleCopy(event: ClipboardEvent): void {
    try {
      const selection = window.getSelection()?.toString() || '';
      if (!selection) return;

      const target = event.target as HTMLElement;
      const isSensitive = target ? Validator.isElementSensitive(target) : false;

      this.callback(EVENTS.CLIPBOARD_COPIED, {
        selected_length: selection.length,
        tag_name: target?.tagName?.toLowerCase() || null,
        is_masked: isSensitive,
        preview: isSensitive ? '[REDACTED]' : Validator.maskSensitiveText(selection.substring(0, 40))
      });
    } catch {
      // ignore
    }
  }

  private handlePaste(event: ClipboardEvent): void {
    try {
      const target = event.target as HTMLElement;
      const isSensitive = target ? Validator.isElementSensitive(target) : false;
      const input = target as HTMLInputElement;

      this.callback(EVENTS.CLIPBOARD_PASTED, {
        input_id: target?.id || null,
        input_name: input?.name || null,
        tag_name: target?.tagName?.toLowerCase() || null,
        is_masked: isSensitive
      });
    } catch {
      // ignore
    }
  }
}
