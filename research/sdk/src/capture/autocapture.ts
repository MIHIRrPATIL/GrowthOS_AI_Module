import { EVENTS } from '../constants';
import { Validator } from '../validator';

export type AutocaptureCallback = (eventName: string, properties: Record<string, any>) => void;

export class AutocaptureModule {
  private callback: AutocaptureCallback;
  private isListening: boolean = false;

  constructor(callback: AutocaptureCallback) {
    this.callback = callback;
  }

  public start(): void {
    if (typeof document === 'undefined' || this.isListening) return;

    document.addEventListener('click', this.handleClick.bind(this), true);
    this.isListening = true;
  }

  private handleClick(event: MouseEvent): void {
    try {
      const target = (event.target as HTMLElement) || null;
      if (!target) return;

      // Find interactive ancestor if click is on inner icon/span
      const interactiveEl = this.findInteractiveElement(target);
      if (!interactiveEl) return;

      if (Validator.isElementSensitive(interactiveEl)) {
        return;
      }

      const properties = this.extractElementProperties(interactiveEl, event);
      this.callback(EVENTS.ELEMENT_CLICKED, properties);
    } catch (e) {
      // Fail silently to never break the host app
    }
  }

  private findInteractiveElement(el: HTMLElement): HTMLElement | null {
    let current: HTMLElement | null = el;
    let depth = 0;
    while (current && depth < 5) {
      const tag = current.tagName.toLowerCase();
      if (
        tag === 'button' ||
        tag === 'a' ||
        tag === 'input' ||
        tag === 'select' ||
        tag === 'textarea' ||
        current.getAttribute('role') === 'button' ||
        current.hasAttribute('data-growthos-track') ||
        current.onclick !== null
      ) {
        return current;
      }
      current = current.parentElement;
      depth++;
    }
    return el; // Return original target if no interactive parent found
  }

  private extractElementProperties(el: HTMLElement, event: MouseEvent): Record<string, any> {
    const tagName = el.tagName.toLowerCase();
    const elementId = el.id || null;
    const className = typeof el.className === 'string' ? el.className.trim() : null;
    const textContent = (el.textContent || '').trim().substring(0, 100);
    const href = el instanceof HTMLAnchorElement ? el.href : null;
    const cssPath = this.getCssPath(el);

    // Extract data-growthos-* attributes
    const dataAttributes: Record<string, string> = {};
    if (el.attributes) {
      for (let i = 0; i < el.attributes.length; i++) {
        const attr = el.attributes[i];
        if (attr.name.startsWith('data-growthos-') || attr.name.startsWith('data-track-')) {
          dataAttributes[attr.name] = attr.value;
        }
      }
    }

    return {
      tag_name: tagName,
      element_id: elementId,
      class_name: className,
      text_content: Validator.maskSensitiveText(textContent),
      href: href,
      css_path: cssPath,
      client_x: event.clientX,
      client_y: event.clientY,
      page_x: event.pageX,
      page_y: event.pageY,
      data_attributes: dataAttributes
    };
  }

  private getCssPath(el: HTMLElement): string {
    if (!(el instanceof Element)) return '';
    const path: string[] = [];
    let current: Element | null = el;
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      let selector = current.nodeName.toLowerCase();
      if (current.id) {
        selector += '#' + current.id;
        path.unshift(selector);
        break;
      } else {
        let sibling: Element | null = current;
        let nth = 1;
        while ((sibling = sibling.previousElementSibling)) {
          if (sibling.nodeName.toLowerCase() === selector) nth++;
        }
        if (nth !== 1) selector += `:nth-of-type(${nth})`;
      }
      path.unshift(selector);
      current = current.parentElement;
      if (path.length > 5) break; // Limit hierarchy depth
    }
    return path.join(' > ');
  }
}
