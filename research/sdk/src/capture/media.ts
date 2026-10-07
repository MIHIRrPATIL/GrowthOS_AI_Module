import { EVENTS } from '../constants';

export type MediaCallback = (eventName: string, properties: Record<string, any>) => void;

export class MediaCaptureModule {
  private callback: MediaCallback;
  private trackedMedia: WeakMap<HTMLMediaElement, Set<number>> = new WeakMap();
  private isListening: boolean = false;

  constructor(callback: MediaCallback) {
    this.callback = callback;
  }

  public start(): void {
    if (typeof document === 'undefined' || this.isListening) return;

    document.addEventListener('play', this.handlePlay.bind(this), true);
    document.addEventListener('pause', this.handlePause.bind(this), true);
    document.addEventListener('timeupdate', this.handleTimeUpdate.bind(this), true);

    this.isListening = true;
  }

  private handlePlay(event: Event): void {
    const el = event.target as HTMLMediaElement;
    if (!this.isMediaElement(el)) return;

    this.callback(EVENTS.MEDIA_PLAYED, {
      media_type: el.tagName.toLowerCase(),
      media_src: el.currentSrc || el.src || null,
      current_time: Math.round(el.currentTime),
      duration: Math.round(el.duration || 0)
    });
  }

  private handlePause(event: Event): void {
    const el = event.target as HTMLMediaElement;
    if (!this.isMediaElement(el)) return;
    if (el.ended) return; // Handled separately if needed

    const duration = el.duration || 1;
    const percentage = Math.min(100, Math.round((el.currentTime / duration) * 100));

    this.callback(EVENTS.MEDIA_PAUSED, {
      media_type: el.tagName.toLowerCase(),
      media_src: el.currentSrc || el.src || null,
      current_time: Math.round(el.currentTime),
      duration: Math.round(el.duration || 0),
      watch_percentage: percentage
    });
  }

  private handleTimeUpdate(event: Event): void {
    const el = event.target as HTMLMediaElement;
    if (!this.isMediaElement(el) || !el.duration) return;

    if (!this.trackedMedia.has(el)) {
      this.trackedMedia.set(el, new Set());
    }

    const milestones = this.trackedMedia.get(el)!;
    const percentage = Math.round((el.currentTime / el.duration) * 100);

    for (const m of [25, 50, 75, 100]) {
      if (percentage >= m && !milestones.has(m)) {
        milestones.add(m);
        this.callback(EVENTS.MEDIA_MILESTONE, {
          media_type: el.tagName.toLowerCase(),
          media_src: el.currentSrc || el.src || null,
          milestone_percentage: m,
          current_time: Math.round(el.currentTime),
          duration: Math.round(el.duration)
        });
      }
    }
  }

  private isMediaElement(el: any): el is HTMLMediaElement {
    return el && (el.tagName === 'VIDEO' || el.tagName === 'AUDIO');
  }
}
