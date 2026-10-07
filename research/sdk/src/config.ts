import { GrowthOSConfig, ConsentConfig } from './types';
import { DEFAULT_CONFIG } from './constants';

export class ConfigManager {
  private config: GrowthOSConfig;

  constructor(userConfig: GrowthOSConfig) {
    if (!userConfig.projectId) {
      throw new Error('[GrowthOS] Initialized without a required projectId.');
    }

    const mergedConsent: ConsentConfig = {
      ...DEFAULT_CONFIG.consent,
      ...(userConfig.consent || {})
    };

    this.config = {
      ...DEFAULT_CONFIG,
      ...userConfig,
      consent: mergedConsent
    };
  }

  public get(): GrowthOSConfig {
    return this.config;
  }

  public update(partial: Partial<GrowthOSConfig>): void {
    this.config = {
      ...this.config,
      ...partial,
      consent: partial.consent ? { ...this.config.consent, ...partial.consent } : this.config.consent
    };
  }

  public isTrackingAllowed(): boolean {
    if (this.config.consent && this.config.consent.analytics === false) {
      return false;
    }
    if (this.config.consent?.required) {
      return Boolean(this.config.consent?.analytics);
    }
    return true;
  }

  public isReplayAllowed(): boolean {
    if (!this.config.consent?.required) return true;
    return Boolean(this.config.consent?.sessionReplay);
  }

  public isDebug(): boolean {
    return Boolean(this.config.debug);
  }
}
