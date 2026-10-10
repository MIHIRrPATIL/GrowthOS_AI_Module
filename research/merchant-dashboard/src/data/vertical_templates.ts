import { VerticalTemplate } from '../types/merchant';

export const VERTICAL_TEMPLATES: VerticalTemplate[] = [
  {
    id: 'ecommerce',
    name: 'E-Commerce & Food Delivery',
    description: 'Standard product catalog, cart operations, multi-step checkout funnel, and delivery tracking.',
    icon: 'ShoppingCart',
    default_funnel: [
      'product.viewed',
      'cart.item_added',
      'checkout.started',
      'purchase.completed'
    ],
    granular_steps: [
      'checkout.started',
      'checkout.shipping_entered',
      'checkout.delivery_slot_selected',
      'checkout.payment_entered',
      'purchase.completed'
    ],
    modular_events: [
      { event: 'product.viewed', category: 'catalog', enabled: true, description: 'User views product detail card' },
      { event: 'product.customized', category: 'catalog', enabled: true, description: 'User customizes crust, size, or toppings' },
      { event: 'cart.item_added', category: 'cart', enabled: true, description: 'Item added to shopping cart' },
      { event: 'cart.item_removed', category: 'cart', enabled: true, description: 'Item removed from cart' },
      { event: 'cart.coupon_applied', category: 'cart', enabled: true, description: 'Promotional discount coupon applied' },
      { event: 'checkout.started', category: 'checkout', enabled: true, description: 'User initiates checkout flow' },
      { event: 'checkout.step_completed', category: 'checkout', enabled: true, description: 'Sub-step completed in checkout funnel' },
      { event: 'checkout.abandoned', category: 'checkout', enabled: true, description: 'Checkout abandoned at friction point' },
      { event: 'purchase.completed', category: 'conversion', enabled: true, description: 'Order confirmed and paid' }
    ]
  },
  {
    id: 'saas',
    name: 'B2B / B2C SaaS Platform',
    description: 'User registrations, free trial activations, core feature milestones, and paid plan upgrades.',
    icon: 'Laptop',
    default_funnel: [
      'user.signup',
      'trial.started',
      'feature.activated',
      'subscription.upgraded'
    ],
    granular_steps: [
      'user.signup',
      'workspace.created',
      'invite.sent',
      'core_feature.used',
      'subscription.upgraded'
    ],
    modular_events: [
      { event: 'user.signup', category: 'onboarding', enabled: true, description: 'User completes registration' },
      { event: 'trial.started', category: 'onboarding', enabled: true, description: '14-day free trial started' },
      { event: 'feature.activated', category: 'engagement', enabled: true, description: 'Core product feature first usage' },
      { event: 'subscription.upgraded', category: 'conversion', enabled: true, description: 'User converts to paid tier' }
    ]
  },
  {
    id: 'bookings',
    name: 'Services & Appointments',
    description: 'Service discovery, calendar date selection, client intake form, and deposit confirmations.',
    icon: 'Calendar',
    default_funnel: [
      'service.viewed',
      'slot.selected',
      'booking.started',
      'booking.confirmed'
    ],
    granular_steps: [
      'service.viewed',
      'calendar.slot_selected',
      'client_details.entered',
      'deposit.paid',
      'booking.confirmed'
    ],
    modular_events: [
      { event: 'service.viewed', category: 'catalog', enabled: true, description: 'Consultation or treatment viewed' },
      { event: 'slot.selected', category: 'booking', enabled: true, description: 'Date & time slot chosen' },
      { event: 'booking.started', category: 'booking', enabled: true, description: 'Intake details form opened' },
      { event: 'booking.confirmed', category: 'conversion', enabled: true, description: 'Appointment confirmed and paid' }
    ]
  },
  {
    id: 'media',
    name: 'Media & Digital Content',
    description: 'Article browsing, video stream tracking, metered paywall prompts, and subscription starts.',
    icon: 'BookOpen',
    default_funnel: [
      'article.read',
      'paywall.prompted',
      'checkout.started',
      'subscription.started'
    ],
    granular_steps: [
      'article.read',
      'scroll.50_percent',
      'paywall.viewed',
      'plan.selected',
      'subscription.started'
    ],
    modular_events: [
      { event: 'article.read', category: 'content', enabled: true, description: 'Article or video opened' },
      { event: 'paywall.prompted', category: 'paywall', enabled: true, description: 'Monthly free reading limit reached' },
      { event: 'subscription.started', category: 'conversion', enabled: true, description: 'Premium subscription started' }
    ]
  }
];
