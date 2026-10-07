/**
 * GrowthOS SDK Constants
 */

export const SDK_VERSION = '1.0.0';
export const SDK_NAME = 'growthos-js';

export const DEFAULT_CONFIG = {
  apiHost: 'https://api.growthos.io',
  posthogHost: 'https://us.i.posthog.com',
  usePosthog: true,
  autocapture: true,
  capturePageviews: true,
  captureForms: true,
  captureScroll: true,
  captureUxSignals: true,
  captureKeystrokes: true,
  captureMedia: true,
  capturePerformance: true,
  captureClipboard: true,
  maskAllInputs: false,
  maskTextSelector: '.growthos-mask, [data-growthos-mask]',
  sessionInactivityMinutes: 30,
  batchSize: 15,
  flushIntervalMs: 3000,
  maxQueueSize: 500,
  debug: false,
  consent: {
    analytics: true,
    marketing: true,
    sessionReplay: true,
    required: false
  }
};

export const STORAGE_KEYS = {
  ANONYMOUS_ID: 'growthos_anon_id',
  CUSTOMER_ID: 'growthos_cust_id',
  SESSION_ID: 'growthos_session_id',
  SESSION_LAST_ACTIVE: 'growthos_session_last_active',
  SESSION_ENTRY_URL: 'growthos_session_entry_url',
  SESSION_ENTRY_REFERRER: 'growthos_session_entry_ref',
  CONSENT_STATE: 'growthos_consent',
  EVENT_QUEUE: 'growthos_event_queue'
};

export const EVENTS = {
  // Navigation & Lifecycle
  PAGE_VIEWED: 'page.viewed',
  SESSION_STARTED: 'session.started',
  SESSION_ENDED: 'session.ended',
  TAB_VISIBILITY_CHANGED: 'tab.visibility_changed',

  // DOM & Interactions
  ELEMENT_CLICKED: 'element.clicked',
  SCROLL_MILESTONE: 'scroll.milestone',
  CLIPBOARD_COPIED: 'clipboard.copied',
  CLIPBOARD_PASTED: 'clipboard.pasted',

  // Form Intelligence
  FORM_STARTED: 'form.started',
  FORM_FIELD_FOCUSED: 'form.field_focused',
  FORM_FIELD_BLURRED: 'form.field_blurred',
  FORM_FIELD_CHANGED: 'form.field_changed',
  FORM_SUBMITTED: 'form.submitted',
  FORM_ABANDONED: 'form.abandoned',

  // Media
  MEDIA_PLAYED: 'media.played',
  MEDIA_PAUSED: 'media.paused',
  MEDIA_MILESTONE: 'media.milestone',

  // Web Vitals
  PERFORMANCE_WEB_VITALS: 'performance.web_vitals',

  // UX Signals & Keystroke Dynamics
  USER_RAGE_CLICK: 'user.rage_click',
  USER_DEAD_CLICK: 'user.dead_click',
  USER_ERROR_CLICK: 'user.error_click',
  USER_MOUSE_THRASHING: 'user.mouse_thrashing',
  USER_EXIT_INTENT: 'user.exit_intent',
  USER_TYPING_DYNAMICS: 'user.typing_dynamics',
  USER_FORM_HESITATION: 'user.form_hesitation',
  USER_EXCESSIVE_CORRECTIONS: 'user.excessive_corrections',
  USER_TAB_SWITCHED_AWAY: 'user.tab_switched_away',
  USER_TAB_RETURNED: 'user.tab_returned',
  USER_WINDOW_BLURRED: 'user.window_blurred',
  USER_WINDOW_FOCUSED: 'user.window_focused',
  USER_COUPON_HUNT_DETECTED: 'user.coupon_hunt_detected',

  // E-commerce & Business
  PRODUCT_VIEWED: 'product.viewed',
  PRODUCT_LIST_VIEWED: 'product.list_viewed',
  PRODUCT_SEARCHED: 'product.searched',
  PRODUCT_FILTERED: 'product.filtered',
  CART_VIEWED: 'cart.viewed',
  CART_ITEM_ADDED: 'cart.item_added',
  CART_ITEM_REMOVED: 'cart.item_removed',
  CART_QUANTITY_UPDATED: 'cart.quantity_updated',
  CART_CLEARED: 'cart.cleared',
  CHECKOUT_STARTED: 'checkout.started',
  CHECKOUT_STEP_COMPLETED: 'checkout.step_completed',
  CHECKOUT_ABANDONED: 'checkout.abandoned',
  PURCHASE_COMPLETED: 'purchase.completed',

  // Loyalty & Identity
  USER_SIGNED_UP: 'user.signed_up',
  USER_LOGGED_IN: 'user.logged_in',
  USER_LOGGED_OUT: 'user.logged_out',
  REWARD_VIEWED: 'reward.viewed',
  REWARD_REDEEMED: 'reward.redeemed'
};

// Sensitive data patterns for automatic masking
export const SENSITIVE_PATTERNS = {
  CREDIT_CARD: /\b(?:\d[ -]?){12,18}\d\b/g,
  CVV: /\b\d{3,4}\b/g,
  SSN: /\b\d{3}-\d{2}-\d{4}\b/g,
  PASSWORD_FIELD_REGEX: /(?:^|[_\W])(pass|passwd|password|pwd|secret|token|auth|cvv|cvc|card|ssn|pin|otp|security|account_number|routing|bank|tax|national_id|aadhaar|pan)(?:[_\W]|$)/i,
  AUTOCOMPLETE_SENSITIVE: /cc-|current-password|new-password|one-time-code|transaction-amount|bday/i
};

// Signal Detection Thresholds
export const UX_THRESHOLDS = {
  RAGE_CLICK_MAX_DELAY_MS: 500,
  RAGE_CLICK_MIN_CLICKS: 3,
  RAGE_CLICK_RADIUS_PX: 30,
  DEAD_CLICK_MUTATION_TIMEOUT_MS: 1000,
  ERROR_CLICK_WINDOW_MS: 1000,
  EXIT_INTENT_VELOCITY_Y: -400,
  MOUSE_THRASHING_ACCELERATION: 1800,
  TYPING_PAUSE_HESITATION_MS: 1500,
  SCROLL_MILESTONES: [25, 50, 75, 90, 100]
};
