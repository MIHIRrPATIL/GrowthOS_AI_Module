import { SENSITIVE_PATTERNS } from './constants';

export class Validator {
  /**
   * Generates a deterministic or random idempotency key.
   */
  public static generateIdempotencyKey(eventName: string, timestamp: string, anonId: string): string {
    const raw = `${eventName}:${timestamp}:${anonId}:${Math.random().toString(36).substring(2, 9)}`;
    return 'idemp_' + btoa(raw).replace(/[/+=]/g, '').substring(0, 24);
  }

  /**
   * Sanitizes and masks sensitive PII from properties objects.
   */
  public static sanitizeProperties<T extends Record<string, any>>(props: T, maskAll: boolean = false): T {
    if (!props || typeof props !== 'object') {
      return props;
    }

    const clean: Record<string, any> = {};

    for (const [key, value] of Object.entries(props)) {
      // Check if key looks like a password or sensitive secret
      if (SENSITIVE_PATTERNS.PASSWORD_FIELD_REGEX.test(key)) {
        clean[key] = '[REDACTED]';
        continue;
      }

      if (typeof value === 'string') {
        if (maskAll) {
          clean[key] = '[MASKED]';
        } else {
          clean[key] = this.maskSensitiveText(value);
        }
      } else if (typeof value === 'object' && value !== null) {
        if (Array.isArray(value)) {
          clean[key] = value.map((item) =>
            typeof item === 'object' && item !== null ? this.sanitizeProperties(item, maskAll) : item
          );
        } else {
          clean[key] = this.sanitizeProperties(value, maskAll);
        }
      } else {
        clean[key] = value;
      }
    }

    return clean as T;
  }

  /**
   * Masks credit card numbers, CVVs, and SSNs in plain strings.
   */
  public static maskSensitiveText(text: string): string {
    if (!text || typeof text !== 'string') return text;

    let sanitized = text;

    // Mask Potential Credit Cards
    sanitized = sanitized.replace(SENSITIVE_PATTERNS.CREDIT_CARD, (match) => {
      const cleanDigits = match.replace(/[-\s]/g, '');
      if (Validator.passesLuhnCheck(cleanDigits)) {
        return `[CARD_ENDED_${cleanDigits.slice(-4)}]`;
      }
      return match;
    });

    // Mask SSN
    sanitized = sanitized.replace(SENSITIVE_PATTERNS.SSN, '[SSN_REDACTED]');

    return sanitized;
  }

  /**
   * Validates number using standard Luhn formula.
   */
  public static passesLuhnCheck(val: string): boolean {
    const sanitized = val.replace(/\D/g, '');
    if (sanitized.length < 13 || sanitized.length > 19) return false;

    let sum = 0;
    let shouldDouble = false;
    for (let i = sanitized.length - 1; i >= 0; i--) {
      let digit = parseInt(sanitized.charAt(i), 10);
      if (shouldDouble) {
        digit *= 2;
        if (digit > 9) digit -= 9;
      }
      sum += digit;
      shouldDouble = !shouldDouble;
    }
    return sum % 10 === 0;
  }

  /**
   * Checks if an input element is sensitive and should be excluded from capture.
   */
  public static isElementSensitive(el: HTMLElement): boolean {
    if (!el) return false;

    // 1. Explicit data attributes & classes on element or parents
    if (
      el.hasAttribute('data-growthos-mask') ||
      el.hasAttribute('data-private') ||
      el.hasAttribute('data-mask') ||
      el.closest('[data-growthos-mask], [data-private], [data-mask], .growthos-mask, .growthos-no-track, .sensitive, .masked')
    ) {
      return true;
    }

    if (el.classList && (el.classList.contains('growthos-mask') || el.classList.contains('sensitive') || el.classList.contains('masked'))) {
      return true;
    }

    // 2. Form Input inspections
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement) {
      const type = (el as HTMLInputElement).type ? (el as HTMLInputElement).type.toLowerCase() : '';
      if (['password', 'hidden'].includes(type)) {
        return true;
      }

      // Check autocomplete attribute
      const autocomplete = (el.getAttribute('autocomplete') || '').toLowerCase();
      if (autocomplete && SENSITIVE_PATTERNS.AUTOCOMPLETE_SENSITIVE.test(autocomplete)) {
        return true;
      }

      // Check name, id, placeholder, aria-label, title
      const identifiers = [
        el.getAttribute('name'),
        el.id,
        el.getAttribute('placeholder'),
        el.getAttribute('aria-label'),
        el.getAttribute('title'),
        el.getAttribute('data-testid')
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      if (SENSITIVE_PATTERNS.PASSWORD_FIELD_REGEX.test(identifiers)) {
        return true;
      }
    }

    return false;
  }
}
