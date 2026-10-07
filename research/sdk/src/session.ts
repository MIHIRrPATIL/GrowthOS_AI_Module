import { StorageManager } from './storage';
import { STORAGE_KEYS } from './constants';
import { DeviceMetadata, NetworkMetadata, PageMetadata, UTMMetadata } from './types';

export class SessionManager {
  private storage: StorageManager;
  private inactivityMinutes: number;
  private currentSessionId: string | null = null;
  private isNewSession: boolean = false;

  constructor(storage: StorageManager, inactivityMinutes: number = 30) {
    this.storage = storage;
    this.inactivityMinutes = inactivityMinutes;
    this.refreshSession();
  }

  public refreshSession(): string {
    const now = Date.now();
    const lastActiveStr = this.storage.get(STORAGE_KEYS.SESSION_LAST_ACTIVE);
    const existingSessionId = this.storage.get(STORAGE_KEYS.SESSION_ID);
    const timeoutMs = this.inactivityMinutes * 60 * 1000;

    if (existingSessionId && lastActiveStr) {
      const lastActive = parseInt(lastActiveStr, 10);
      if (now - lastActive < timeoutMs) {
        this.storage.set(STORAGE_KEYS.SESSION_LAST_ACTIVE, now.toString());
        this.currentSessionId = existingSessionId;
        this.isNewSession = false;
        return this.currentSessionId;
      }
    }

    // Start a fresh session
    this.currentSessionId = 'sess_' + this.storage.generateUUID().substring(0, 18);
    this.storage.set(STORAGE_KEYS.SESSION_ID, this.currentSessionId);
    this.storage.set(STORAGE_KEYS.SESSION_LAST_ACTIVE, now.toString());

    if (typeof window !== 'undefined') {
      this.storage.set(STORAGE_KEYS.SESSION_ENTRY_URL, window.location.href);
      this.storage.set(STORAGE_KEYS.SESSION_ENTRY_REFERRER, document.referrer || '');
    }

    this.isNewSession = true;
    return this.currentSessionId;
  }

  public getSessionId(): string {
    if (!this.currentSessionId) {
      return this.refreshSession();
    }
    this.touch();
    return this.currentSessionId;
  }

  public touch(): void {
    this.storage.set(STORAGE_KEYS.SESSION_LAST_ACTIVE, Date.now().toString());
  }

  public isSessionStart(): boolean {
    return this.isNewSession;
  }

  public getPageMetadata(): PageMetadata {
    if (typeof window === 'undefined') {
      return { url: '', path: '', title: '', referrer: '', search: '' };
    }
    return {
      url: window.location.href,
      path: window.location.pathname,
      title: document.title,
      referrer: document.referrer || '',
      search: window.location.search
    };
  }

  public getUTMMetadata(): UTMMetadata {
    if (typeof window === 'undefined') {
      return { source: null, medium: null, campaign: null, term: null, content: null };
    }
    const params = new URLSearchParams(window.location.search);
    return {
      source: params.get('utm_source'),
      medium: params.get('utm_medium'),
      campaign: params.get('utm_campaign'),
      term: params.get('utm_term'),
      content: params.get('utm_content')
    };
  }

  public getDeviceMetadata(): DeviceMetadata {
    if (typeof window === 'undefined' || typeof navigator === 'undefined') {
      return {
        screen_width: 0,
        screen_height: 0,
        viewport_width: 0,
        viewport_height: 0,
        pixel_ratio: 1,
        orientation: 'unknown',
        user_agent: '',
        browser: 'unknown',
        browser_version: '',
        os: 'unknown',
        os_version: '',
        device_type: 'desktop',
        language: 'en',
        timezone: 'UTC',
        timezone_offset: 0
      };
    }

    const width = window.screen.width;
    const height = window.screen.height;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const ua = navigator.userAgent;

    let deviceType: 'mobile' | 'tablet' | 'desktop' = 'desktop';
    if (/tablet|ipad|playbook|silk/i.test(ua) || (viewportWidth >= 600 && viewportWidth <= 1024)) {
      deviceType = 'tablet';
    } else if (/mobile|iphone|ipod|android|blackberry|opera mini|iemobile/i.test(ua) || viewportWidth < 600) {
      deviceType = 'mobile';
    }

    // Determine OS & Browser
    let os = 'unknown';
    if (/windows/i.test(ua)) os = 'Windows';
    else if (/macintosh|mac os x/i.test(ua)) os = 'macOS';
    else if (/android/i.test(ua)) os = 'Android';
    else if (/iphone|ipad|ipod/i.test(ua)) os = 'iOS';
    else if (/linux/i.test(ua)) os = 'Linux';

    let browser = 'unknown';
    let browserVersion = '';
    if (/chrome|crios/i.test(ua) && !/edg|opr/i.test(ua)) {
      browser = 'Chrome';
      const match = ua.match(/chrome\/([0-9.]+)/i);
      if (match) browserVersion = match[1];
    } else if (/safari/i.test(ua) && !/chrome|crios/i.test(ua)) {
      browser = 'Safari';
      const match = ua.match(/version\/([0-9.]+)/i);
      if (match) browserVersion = match[1];
    } else if (/firefox|fxios/i.test(ua)) {
      browser = 'Firefox';
      const match = ua.match(/firefox\/([0-9.]+)/i);
      if (match) browserVersion = match[1];
    } else if (/edg/i.test(ua)) {
      browser = 'Edge';
      const match = ua.match(/edg\/([0-9.]+)/i);
      if (match) browserVersion = match[1];
    }

    return {
      screen_width: width,
      screen_height: height,
      viewport_width: viewportWidth,
      viewport_height: viewportHeight,
      pixel_ratio: window.devicePixelRatio || 1,
      orientation: width > height ? 'landscape' : 'portrait',
      user_agent: ua,
      browser,
      browser_version: browserVersion,
      os,
      os_version: '',
      device_type: deviceType,
      language: navigator.language || 'en',
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
      timezone_offset: new Date().getTimezoneOffset()
    };
  }

  public getNetworkMetadata(): NetworkMetadata | undefined {
    if (typeof navigator === 'undefined' || !(navigator as any).connection) {
      return undefined;
    }
    const conn = (navigator as any).connection;
    return {
      effective_type: conn.effectiveType,
      downlink: conn.downlink,
      rtt: conn.rtt,
      save_data: conn.saveData
    };
  }
}
