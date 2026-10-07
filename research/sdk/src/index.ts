import { GrowthOS, GrowthOSClient } from './growthos';
export * from './types';
export * from './constants';
export { Validator } from './validator';
export { GrowthOSClient, GrowthOS };

// Automatically bind to global window object in browser environments
if (typeof window !== 'undefined') {
  (window as any).GrowthOS = GrowthOS;
}

export default GrowthOS;
