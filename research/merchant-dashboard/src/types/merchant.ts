export interface FunnelStep {
  step_index?: number;
  step_number?: number;
  step_name?: string;
  name?: string;
  event: string;
  sessions_count?: number;
  count?: number;
  conversion_from_previous?: number;
  conversion_pct?: number;
  drop_off_percentage?: number;
  drop_off_pct?: number;
  drop_off_count?: number;
  bottleneck?: boolean;
  friction_reason?: string;
  friction_signals?: Record<string, number>;
}

export interface FunnelData {
  funnel_name: string;
  timeframe: string;
  overall_conversion_rate?: number;
  funnel_conversion_rate?: number;
  steps: FunnelStep[];
}

export interface DormantCustomer {
  cohort_id: string;
  customer_id: string;
  customer_name: string;
  email: string;
  phone: string;
  tier: 'Silver' | 'Gold' | 'Platinum';
  loyalty_points: number;
  cart_total: number;
  cart_items: Array<{ name: string; price: number; quantity: number }>;
  dormant_duration_minutes: number;
  abandoned_step: string;
  recommended_action: string;
  action_status: string;
  action_timestamp?: string;
}

export interface DormantCohortResponse {
  cohort_name: string;
  total_at_risk_customers: number;
  total_at_risk_revenue: number;
  customers: DormantCustomer[];
}

export interface ModularEvent {
  event: string;
  category: 'catalog' | 'cart' | 'checkout' | 'conversion' | 'onboarding' | 'engagement' | 'content' | 'booking' | 'paywall' | 'custom';
  enabled: boolean;
  description: string;
}

export interface VerticalTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  default_funnel: string[];
  granular_steps: string[];
  modular_events: ModularEvent[];
}

export interface CustomEventProperty {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object';
  required?: boolean;
}

export interface CustomMerchantEvent {
  event: string;
  description: string;
  vertical: string;
  category: string;
  enabled: boolean;
  properties: CustomEventProperty[];
  created_at: string;
}

// Module 4: Grounded AI Brain Types
export interface Module4MetricResult {
  metric_name: string;
  vertical_template_id: string;
  value: number;
  unit: string;
  sample_size: number;
  prior_sample_size?: number;
  timeframe: string;
  calculated_at: string;
  metadata?: Record<string, any>;
}

export interface Module4DigestFlag {
  flag_id: string;
  metric_name: string;
  vertical_template_id: string;
  current_value: number;
  prior_value: number;
  delta_pct: number;
  current_sample_size: number;
  prior_sample_size: number;
  unit: string;
  severity: 'low' | 'medium' | 'high';
  period: string;
  flagged_at: string;
  status: 'active' | 'acknowledged' | 'resolved';
  metadata?: Record<string, any>;
}

export interface Module4DigestReport {
  report_id: string;
  vertical_template_id: string;
  period: string;
  threshold_pct: number;
  generated_at: string;
  total_metrics_evaluated: number;
  flags_count: number;
  flags: Module4DigestFlag[];
  baseline_metrics?: Record<string, Module4MetricResult>;
}
