import { EVENTS } from '../constants';
import { Validator } from '../validator';

export type FormCallback = (eventName: string, properties: Record<string, any>) => void;

interface ActiveFormState {
  formId: string;
  formName: string;
  startTime: number;
  fieldsInteracted: Set<string>;
  totalFieldsCount: number;
  lastField: string;
  submitted: boolean;
}

export class FormCaptureModule {
  private callback: FormCallback;
  private activeForms: Map<string, ActiveFormState> = new Map();
  private fieldFocusTimes: Map<string, number> = new Map();
  private isListening: boolean = false;

  constructor(callback: FormCallback) {
    this.callback = callback;
  }

  public start(): void {
    if (typeof document === 'undefined' || this.isListening) return;

    document.addEventListener('focusin', this.handleFocusIn.bind(this), true);
    document.addEventListener('focusout', this.handleFocusOut.bind(this), true);
    document.addEventListener('change', this.handleChange.bind(this), true);
    document.addEventListener('submit', this.handleSubmit.bind(this), true);
    window.addEventListener('beforeunload', this.handleUnload.bind(this));

    this.isListening = true;
  }

  private getFormIdentifier(form: HTMLFormElement | null): { id: string; name: string } {
    if (!form) return { id: 'anonymous_form', name: 'anonymous_form' };
    const id = form.id || form.getAttribute('name') || form.action || 'form_' + Math.random().toString(36).substring(2, 7);
    const name = form.getAttribute('name') || form.id || 'unnamed_form';
    return { id, name };
  }

  private handleFocusIn(event: FocusEvent): void {
    try {
      const target = event.target as HTMLElement;
      if (!this.isFormElement(target)) return;

      const form = target.closest('form');
      const { id: formId, name: formName } = this.getFormIdentifier(form);
      const fieldName = (target as HTMLInputElement).name || target.id || target.tagName.toLowerCase();

      // Check if form interaction just started
      if (!this.activeForms.has(formId)) {
        const totalFields = form ? form.querySelectorAll('input, select, textarea').length : 1;
        this.activeForms.set(formId, {
          formId,
          formName,
          startTime: Date.now(),
          fieldsInteracted: new Set([fieldName]),
          totalFieldsCount: totalFields,
          lastField: fieldName,
          submitted: false
        });

        this.callback(EVENTS.FORM_STARTED, {
          form_id: formId,
          form_name: formName,
          first_field_name: fieldName,
          total_fields: totalFields
        });
      } else {
        const state = this.activeForms.get(formId)!;
        state.fieldsInteracted.add(fieldName);
        state.lastField = fieldName;
      }

      const isSensitive = Validator.isElementSensitive(target);
      this.fieldFocusTimes.set(`${formId}:${fieldName}`, Date.now());

      this.callback(EVENTS.FORM_FIELD_FOCUSED, {
        form_id: formId,
        form_name: formName,
        field_name: isSensitive ? '[SENSITIVE_FIELD]' : fieldName,
        field_type: (target as HTMLInputElement).type || target.tagName.toLowerCase(),
        is_sensitive: isSensitive
      });
    } catch (e) {
      // Fail silently
    }
  }

  private handleFocusOut(event: FocusEvent): void {
    try {
      const target = event.target as HTMLElement;
      if (!this.isFormElement(target)) return;

      const form = target.closest('form');
      const { id: formId, name: formName } = this.getFormIdentifier(form);
      const fieldName = (target as HTMLInputElement).name || target.id || target.tagName.toLowerCase();
      const focusKey = `${formId}:${fieldName}`;

      let dwellTimeMs = 0;
      if (this.fieldFocusTimes.has(focusKey)) {
        dwellTimeMs = Date.now() - this.fieldFocusTimes.get(focusKey)!;
        this.fieldFocusTimes.delete(focusKey);
      }

      const input = target as HTMLInputElement;
      const isSensitive = Validator.isElementSensitive(target);
      const hasValue = Boolean(input.value && input.value.length > 0);

      this.callback(EVENTS.FORM_FIELD_BLURRED, {
        form_id: formId,
        form_name: formName,
        field_name: isSensitive ? '[SENSITIVE_FIELD]' : fieldName,
        dwell_time_ms: dwellTimeMs,
        has_value: isSensitive ? false : hasValue,
        is_sensitive: isSensitive
      });
    } catch (e) {
      // Fail silently
    }
  }

  private handleChange(event: Event): void {
    try {
      const target = event.target as HTMLElement;
      if (!this.isFormElement(target)) return;

      const form = target.closest('form');
      const { id: formId, name: formName } = this.getFormIdentifier(form);
      const fieldName = (target as HTMLInputElement).name || target.id || target.tagName.toLowerCase();
      const input = target as HTMLInputElement;

      const isSensitive = Validator.isElementSensitive(target);
      const valueLength = isSensitive ? 0 : (input.value ? input.value.length : 0);

      this.callback(EVENTS.FORM_FIELD_CHANGED, {
        form_id: formId,
        form_name: formName,
        field_name: isSensitive ? '[SENSITIVE_FIELD]' : fieldName,
        field_type: input.type || target.tagName.toLowerCase(),
        value_length: valueLength,
        is_sensitive: isSensitive
      });
    } catch (e) {
      // Fail silently
    }
  }

  private handleSubmit(event: SubmitEvent): void {
    try {
      const form = event.target as HTMLFormElement;
      if (!form) return;

      const { id: formId, name: formName } = this.getFormIdentifier(form);
      const state = this.activeForms.get(formId);
      const timeSpentSeconds = state ? Math.round((Date.now() - state.startTime) / 1000) : 0;
      const fieldsCompleted = state ? state.fieldsInteracted.size : 0;

      if (state) {
        state.submitted = true;
      }

      this.callback(EVENTS.FORM_SUBMITTED, {
        form_id: formId,
        form_name: formName,
        time_to_complete_seconds: timeSpentSeconds,
        fields_completed_count: fieldsCompleted
      });
    } catch (e) {
      // Fail silently
    }
  }

  private handleUnload(): void {
    for (const [formId, state] of this.activeForms.entries()) {
      if (!state.submitted && state.fieldsInteracted.size > 0) {
        const timeSpent = Math.round((Date.now() - state.startTime) / 1000);
        this.callback(EVENTS.FORM_ABANDONED, {
          form_id: formId,
          form_name: state.formName,
          last_focused_field: state.lastField,
          fields_interacted_count: state.fieldsInteracted.size,
          total_fields_count: state.totalFieldsCount,
          time_spent_seconds: timeSpent
        });
      }
    }
  }

  private isFormElement(el: HTMLElement): boolean {
    if (!el || !el.tagName) return false;
    const tag = el.tagName.toLowerCase();
    return tag === 'input' || tag === 'select' || tag === 'textarea';
  }
}
