"""
Vertical Template Catalog and Metric Specifications
Conforms to:
- research/docs/GrowthOS_Module_4_AI_Growth_Brain_Architecture_and_Plan.md (Component 1)

Defines vertical funnel architectures, metric definitions, polarities, event mappings,
and entity-level cohort rules across:
1. E-Commerce & Digital Retail (`ecommerce`)
2. Quick Service Restaurants & Food Delivery (`qsr_delivery`)
3. B2B / Product-Led Growth SaaS (`saas_subscription`)
4. Travel, Flights & Hospitality Bookings (`travel_hospitality`)
5. Fintech, Digital Credit & Lending (`fintech_lending`)
6. D2C Subscription Boxes & Memberships (`subscription_box`)
"""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from domain.metrics import Unit, Polarity

Entity = Literal["session", "customer", "application"]


class MetricDefinition(BaseModel):
    """
    Contract for a deterministic metric formula within a vertical template.
    Supports session-level, customer-level, and application-level funnels with cohort windows.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    metric_name: str
    definition_version: str = "v1.1.0"
    polarity: Polarity
    unit: Unit = "ratio"
    entity: Entity = "session"
    cohort_window_days: Optional[int] = None
    maturity_window_minutes: Optional[int] = 30
    min_sample_threshold: int = Field(default=30, ge=1)
    step_from: Optional[str] = None
    step_to: Optional[str] = None
    numerator_label: str = Field(default="events", description="Plain English description of numerator, e.g. purchases, abandoned carts")
    denominator_label: str = Field(default="sessions", description="Plain English description of denominator, e.g. sessions, checkouts started")
    description: str


class VerticalTemplate(BaseModel):
    """
    Vertical domain template governing funnel taxonomy, event mapping, and metric catalogs.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    template_id: str
    name: str
    description: str
    default_min_sample_threshold: int = 30
    funnel_steps: List[str]
    event_mapping: Dict[str, str] = Field(default_factory=dict)
    metrics: Dict[str, MetricDefinition]

    def resolve_event_name(self, raw_event_name: str) -> str:
        """
        Translates raw inbound / SDK event names into canonical template taxonomy.
        If already canonical or unmapped, returns raw_event_name.
        """
        return self.event_mapping.get(raw_event_name, raw_event_name)

    def get_metric_def(self, metric_name: str) -> MetricDefinition:
        if metric_name not in self.metrics:
            raise KeyError(
                f"Metric '{metric_name}' not defined in vertical template '{self.template_id}'. "
                f"Available metrics: {list(self.metrics.keys())}"
            )
        return self.metrics[metric_name]


# -------------------------------------------------------------------------
# 1. Ecommerce / Digital Retail Template
# -------------------------------------------------------------------------
ECOMMERCE_TEMPLATE = VerticalTemplate(
    template_id="ecommerce",
    name="E-Commerce & Digital Retail",
    description="Standard funnel for digital commerce, multi-brand retail, and storefronts",
    default_min_sample_threshold=30,
    funnel_steps=[
        "browse",             # page.viewed / product.viewed
        "cart_add",           # cart.item_added
        "checkout_start",     # checkout.started
        "step_1_address",     # checkout.step_completed (step=1)
        "step_2_charges",     # checkout.step_completed (step=2)
        "purchase_complete",  # purchase.completed
    ],
    event_mapping={
        "cart_add": "cart.item_added",
        "add_to_cart": "cart.item_added",
        "cart_item_added": "cart.item_added",
        "checkout_start": "checkout.started",
        "begin_checkout": "checkout.started",
        "order_complete": "purchase.completed",
        "order_completed": "purchase.completed",
    },
    metrics={
        "cart_abandonment_rate": MetricDefinition(
            metric_name="cart_abandonment_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            maturity_window_minutes=30,
            step_from="cart.item_added",
            step_to="purchase.completed",
            min_sample_threshold=20,
            numerator_label="abandoned carts",
            denominator_label="carts added",
            description="Ratio of cart-added sessions that did not complete purchase within the session"
        ),
        "checkout_drop_off_rate": MetricDefinition(
            metric_name="checkout_drop_off_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            maturity_window_minutes=30,
            step_from="checkout.started",
            step_to="purchase.completed",
            min_sample_threshold=15,
            numerator_label="checkout drop-offs",
            denominator_label="checkouts started",
            description="Ratio of checkout-started sessions that failed to complete purchase"
        ),
        "checkout_step_1_drop_off_rate": MetricDefinition(
            metric_name="checkout_step_1_drop_off_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            step_from="checkout.started",
            step_to="checkout.step_completed",
            min_sample_threshold=10,
            numerator_label="step 1 drop-offs",
            denominator_label="checkouts started",
            description="Drop-off rate between checkout start and Step 1 address completion"
        ),
        "checkout_step_2_drop_off_rate": MetricDefinition(
            metric_name="checkout_step_2_drop_off_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            step_from="checkout.step_completed",
            step_to="checkout.step_completed",
            min_sample_threshold=10,
            numerator_label="step 2 drop-offs",
            denominator_label="step 1 completed sessions",
            description="Drop-off rate between Step 1 (address) and Step 2 (payment gateway)"
        ),
        "checkout_step_3_drop_off_rate": MetricDefinition(
            metric_name="checkout_step_3_drop_off_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            step_from="checkout.step_completed",
            step_to="purchase.completed",
            min_sample_threshold=10,
            numerator_label="step 3 drop-offs",
            denominator_label="step 2 completed sessions",
            description="Drop-off rate between Step 2 (payment) and purchase completion"
        ),
        "checkout_conversion_rate": MetricDefinition(
            metric_name="checkout_conversion_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            step_from="checkout.started",
            step_to="purchase.completed",
            min_sample_threshold=15,
            numerator_label="purchases",
            denominator_label="checkouts started",
            description="Ratio of checkout-started sessions that completed a purchase (checkout-to-purchase)"
        ),
        "overall_conversion_rate": MetricDefinition(
            metric_name="overall_conversion_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            step_from="page.viewed",
            step_to="purchase.completed",
            min_sample_threshold=30,
            numerator_label="purchases",
            denominator_label="visiting sessions",
            description="Ratio of visiting sessions that completed a purchase (visit-to-purchase)"
        ),
        "add_to_cart_rate": MetricDefinition(
            metric_name="add_to_cart_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            step_from="product.viewed",
            step_to="cart.item_added",
            min_sample_threshold=30,
            description="Ratio of product viewing sessions that added items to cart"
        ),
        "cart_to_checkout_rate": MetricDefinition(
            metric_name="cart_to_checkout_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            step_from="cart.item_added",
            step_to="checkout.started",
            min_sample_threshold=20,
            description="Ratio of cart sessions that progressed into checkout"
        ),
        "rage_click_session_rate": MetricDefinition(
            metric_name="rage_click_session_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            min_sample_threshold=25,
            description="Ratio of total sessions experiencing UX rage clicks"
        ),
        "exit_intent_rate": MetricDefinition(
            metric_name="exit_intent_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            min_sample_threshold=20,
            description="Ratio of visiting sessions triggering mouse cursor exit intent gestures"
        ),
        "blended_roas": MetricDefinition(
            metric_name="blended_roas",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            min_sample_threshold=1,
            numerator_label="attributed ad revenue",
            denominator_label="ad spend",
            description="Blended return on advertising spend (attributed revenue / total ad spend)"
        ),
        "blended_cac": MetricDefinition(
            metric_name="blended_cac",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="currency_inr",
            entity="session",
            min_sample_threshold=1,
            numerator_label="total ad spend",
            denominator_label="new acquired customers",
            description="Blended customer acquisition cost (ad spend in INR per new customer acquired)"
        ),
        "ad_spend": MetricDefinition(
            metric_name="ad_spend",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="currency_inr",
            entity="session",
            min_sample_threshold=1,
            numerator_label="ad spend in INR",
            denominator_label="campaigns",
            description="Total daily paid advertising budget and spend in INR across all channels"
        ),
        "loyalty_waiver_cost": MetricDefinition(
            metric_name="loyalty_waiver_cost",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="currency_inr",
            entity="session",
            min_sample_threshold=1,
            numerator_label="delivery fee waived in INR",
            denominator_label="waivers granted",
            description="Delivery fee waiver cost in INR granted to retain or convert shoppers"
        ),
        "daily_waiver_budget": MetricDefinition(
            metric_name="daily_waiver_budget",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="currency_inr",
            entity="session",
            min_sample_threshold=1,
            numerator_label="waiver budget cap in INR",
            denominator_label="daily budget",
            description="Daily budget cap in INR allocated for loyalty delivery fee waivers"
        ),
        "marketing_budget_arbitration": MetricDefinition(
            metric_name="marketing_budget_arbitration",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            min_sample_threshold=1,
            numerator_label="ad acquisition CAC",
            denominator_label="loyalty waiver retention cost",
            description="Capital efficiency ratio comparing Paid Ad Acquisition CAC against Loyalty Delivery Fee Waiver retention cost"
        ),
    }
)


# -------------------------------------------------------------------------
# 2. QSR / Food Delivery Template
# -------------------------------------------------------------------------
QSR_DELIVERY_TEMPLATE = VerticalTemplate(
    template_id="qsr_delivery",
    name="Quick Service Restaurant & Food Delivery",
    description="Optimized for rapid ordering funnels, step progression, and friction diagnostics",
    default_min_sample_threshold=25,
    funnel_steps=[
        "menu_view",          # page.viewed / menu
        "product_customize",  # product.customized
        "cart_add",           # cart.item_added
        "checkout_start",     # checkout.started
        "delivery_charges",   # checkout.step_completed (step=2)
        "purchase_complete",  # purchase.completed
    ],
    event_mapping={
        "cart_add": "cart.item_added",
        "add_to_cart": "cart.item_added",
        "cart_item_added": "cart.item_added",
        "checkout_start": "checkout.started",
        "begin_checkout": "checkout.started",
        "order_complete": "purchase.completed",
        "order_completed": "purchase.completed",
    },
    metrics={
        "cart_abandonment_rate": MetricDefinition(
            metric_name="cart_abandonment_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            maturity_window_minutes=30,
            step_from="cart.item_added",
            step_to="purchase.completed",
            min_sample_threshold=20,
            description="Ratio of food cart sessions abandoned before checkout"
        ),
        "checkout_drop_off_rate": MetricDefinition(
            metric_name="checkout_drop_off_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            maturity_window_minutes=30,
            step_from="checkout.started",
            step_to="purchase.completed",
            min_sample_threshold=15,
            description="Food checkout drop-off rate"
        ),
        "checkout_step_2_drop_off_rate": MetricDefinition(
            metric_name="checkout_step_2_drop_off_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            step_from="checkout.step_completed",
            step_to="checkout.step_completed",
            min_sample_threshold=10,
            description="Drop-off rate specifically at the delivery fee review step"
        ),
        "customization_drop_off_rate": MetricDefinition(
            metric_name="customization_drop_off_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            step_from="product.customized",
            step_to="cart.item_added",
            min_sample_threshold=15,
            description="Sessions customizing an item that abandoned without adding to cart"
        ),
        "overall_conversion_rate": MetricDefinition(
            metric_name="overall_conversion_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            step_from="page.viewed",
            step_to="purchase.completed",
            min_sample_threshold=25,
            description="End-to-end food ordering conversion rate"
        ),
        "add_to_cart_rate": MetricDefinition(
            metric_name="add_to_cart_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            step_from="product.viewed",
            step_to="cart.item_added",
            min_sample_threshold=25,
            description="Product menu view to cart addition rate"
        ),
        "cart_to_checkout_rate": MetricDefinition(
            metric_name="cart_to_checkout_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            step_from="cart.item_added",
            step_to="checkout.started",
            min_sample_threshold=20,
            description="Cart additions that progressed into checkout"
        ),
        "rage_click_session_rate": MetricDefinition(
            metric_name="rage_click_session_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            min_sample_threshold=20,
            description="Sessions with rage clicks on ordering or payment elements"
        ),
        "exit_intent_rate": MetricDefinition(
            metric_name="exit_intent_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            min_sample_threshold=20,
            description="Sessions where desktop cursor left viewport boundaries"
        ),
    }
)


# -------------------------------------------------------------------------
# 3. B2B / Product-Led Growth SaaS Template
# -------------------------------------------------------------------------
SAAS_SUBSCRIPTION_TEMPLATE = VerticalTemplate(
    template_id="saas_subscription",
    name="B2B & Product-Led Growth SaaS",
    description="Lifecycle metrics for software subscriptions, self-serve signups, and trial activations",
    default_min_sample_threshold=20,
    funnel_steps=[
        "landing_visit",       # page.viewed
        "signup_start",        # user.signup_started
        "signup_complete",     # user.signed_up
        "workspace_created",   # workspace.created
        "onboarding_complete", # onboarding.completed
        "trial_started",       # trial.started
        "paid_subscribed",     # subscription.activated
    ],
    event_mapping={
        "signup_started": "user.signup_started",
        "signup_completed": "user.signed_up",
        "user_signed_up": "user.signed_up",
        "workspace_create": "workspace.created",
        "onboarding_done": "onboarding.completed",
        "trial_start": "trial.started",
        "subscription_active": "subscription.activated",
    },
    metrics={
        "signup_completion_rate": MetricDefinition(
            metric_name="signup_completion_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            step_from="user.signup_started",
            step_to="user.signed_up",
            min_sample_threshold=15,
            description="Ratio of signup attempts resulting in successful account registration"
        ),
        "onboarding_drop_off_rate": MetricDefinition(
            metric_name="onboarding_drop_off_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="customer",
            cohort_window_days=7,
            step_from="workspace.created",
            step_to="onboarding.completed",
            min_sample_threshold=10,
            description="Ratio of new customer accounts that failed to complete onboarding within 7 days"
        ),
        "trial_to_paid_conversion_rate": MetricDefinition(
            metric_name="trial_to_paid_conversion_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="customer",
            cohort_window_days=14,
            step_from="trial.started",
            step_to="subscription.activated",
            min_sample_threshold=10,
            description="Cohort conversion rate: percentage of trial customers converting to paid within 14 days"
        ),
        "visitor_to_signup_rate": MetricDefinition(
            metric_name="visitor_to_signup_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            step_from="page.viewed",
            step_to="user.signed_up",
            min_sample_threshold=30,
            description="Ratio of top-of-funnel website visitors who signed up"
        ),
        "rage_click_session_rate": MetricDefinition(
            metric_name="rage_click_session_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            min_sample_threshold=20,
            description="Rage click rate on dashboard tools or complex configuration settings"
        ),
    }
)


# -------------------------------------------------------------------------
# 4. Travel, Flights & Hospitality Bookings Template
# -------------------------------------------------------------------------
TRAVEL_HOSPITALITY_TEMPLATE = VerticalTemplate(
    template_id="travel_hospitality",
    name="Travel, Flights & Hotel Bookings",
    description="Search-to-booking funnel for airlines, hotel aggregators, and vacation rental platforms",
    default_min_sample_threshold=25,
    funnel_steps=[
        "search_performed",       # search.performed
        "listing_viewed",         # listing.viewed
        "dates_selected",         # dates.selected
        "guest_details_entered",  # guest.details_entered
        "payment_initiated",      # payment.initiated
        "booking_confirmed",      # booking.confirmed
    ],
    event_mapping={
        "search": "search.performed",
        "view_listing": "listing.viewed",
        "select_dates": "dates.selected",
        "booking_confirm": "booking.confirmed",
    },
    metrics={
        "search_to_detail_rate": MetricDefinition(
            metric_name="search_to_detail_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            step_from="search.performed",
            step_to="listing.viewed",
            min_sample_threshold=25,
            description="Ratio of flight/hotel searches that led to at least one detail page view"
        ),
        "booking_drop_off_rate": MetricDefinition(
            metric_name="booking_drop_off_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            step_from="dates.selected",
            step_to="booking.confirmed",
            min_sample_threshold=15,
            description="Ratio of sessions with selected dates that abandoned before confirmed booking"
        ),
        "payment_failure_rate": MetricDefinition(
            metric_name="payment_failure_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            step_from="payment.initiated",
            step_to="payment.failed",
            min_sample_threshold=10,
            description="Ratio of booking payment attempts resulting in gateway or fraud declines"
        ),
        "overall_booking_conversion_rate": MetricDefinition(
            metric_name="overall_booking_conversion_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            step_from="search.performed",
            step_to="booking.confirmed",
            min_sample_threshold=30,
            description="Searches converted into confirmed passenger or hotel bookings"
        ),
        "rage_click_session_rate": MetricDefinition(
            metric_name="rage_click_session_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            min_sample_threshold=20,
            description="Rage clicks on seat selection maps or filter dropdowns"
        ),
    }
)


# -------------------------------------------------------------------------
# 5. Fintech & Digital Lending Template
# -------------------------------------------------------------------------
FINTECH_LENDING_TEMPLATE = VerticalTemplate(
    template_id="fintech_lending",
    name="Fintech, Credit & Digital Lending",
    description="Application, KYC verification, and disbursement funnel for credit cards and instant loans",
    default_min_sample_threshold=20,
    funnel_steps=[
        "offer_view",         # loan.offer_viewed
        "application_start",  # loan.application_started
        "kyc_submitted",      # kyc.submitted
        "bank_linked",        # bank.account_linked
        "agreement_signed",   # agreement.signed
        "loan_disbursed",     # loan.disbursed
    ],
    event_mapping={
        "apply_start": "loan.application_started",
        "kyc_done": "kyc.submitted",
        "bank_verified": "bank.account_linked",
        "sign_agreement": "agreement.signed",
        "disbursed": "loan.disbursed",
    },
    metrics={
        "application_completion_rate": MetricDefinition(
            metric_name="application_completion_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="application",
            cohort_window_days=3,
            step_from="loan.application_started",
            step_to="agreement.signed",
            min_sample_threshold=15,
            description="Ratio of started applications reaching signed agreement within 3 days"
        ),
        "kyc_drop_off_rate": MetricDefinition(
            metric_name="kyc_drop_off_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="application",
            cohort_window_days=1,
            step_from="loan.application_started",
            step_to="kyc.submitted",
            min_sample_threshold=10,
            description="Drop-off rate during identity document verification within 24 hours"
        ),
        "bank_linking_drop_off_rate": MetricDefinition(
            metric_name="bank_linking_drop_off_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="application",
            cohort_window_days=2,
            step_from="kyc.submitted",
            step_to="bank.account_linked",
            min_sample_threshold=10,
            description="Drop-off rate during bank account verification within 48 hours"
        ),
        "disbursement_conversion_rate": MetricDefinition(
            metric_name="disbursement_conversion_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="application",
            cohort_window_days=7,
            step_from="loan.application_started",
            step_to="loan.disbursed",
            min_sample_threshold=15,
            description="Cohort conversion rate: percentage of loan applications disbursed within 7 days"
        ),
        "rage_click_session_rate": MetricDefinition(
            metric_name="rage_click_session_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            min_sample_threshold=20,
            description="Rage clicks on OTP verification or identity document upload forms"
        ),
    }
)


# -------------------------------------------------------------------------
# 6. D2C Subscription Box & Memberships Template
# -------------------------------------------------------------------------
SUBSCRIPTION_BOX_TEMPLATE = VerticalTemplate(
    template_id="subscription_box",
    name="Subscription Box & Memberships",
    description="Recurring subscription, billing cadence, and plan tier selection funnels",
    default_min_sample_threshold=20,
    funnel_steps=[
        "browse",             # page.viewed / product.viewed
        "plan_select",        # plan.selected
        "customization",      # box.customized
        "checkout_start",     # checkout.started
        "subscription_active",# subscription.activated
        "renewal_success",    # subscription.renewed
    ],
    event_mapping={
        "select_plan": "plan.selected",
        "customize_box": "box.customized",
        "subscribe": "subscription.activated",
        "renew": "subscription.renewed",
    },
    metrics={
        "plan_selection_rate": MetricDefinition(
            metric_name="plan_selection_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="session",
            step_from="page.viewed",
            step_to="plan.selected",
            min_sample_threshold=20,
            description="Ratio of visiting sessions selecting a recurring plan"
        ),
        "subscription_conversion_rate": MetricDefinition(
            metric_name="subscription_conversion_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="customer",
            cohort_window_days=7,
            step_from="page.viewed",
            step_to="subscription.activated",
            min_sample_threshold=20,
            description="Cohort conversion: visitors who active a paid recurring plan within 7 days"
        ),
        "cart_abandonment_rate": MetricDefinition(
            metric_name="cart_abandonment_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            maturity_window_minutes=30,
            step_from="plan.selected",
            step_to="subscription.activated",
            min_sample_threshold=15,
            description="Ratio of plan selection sessions abandoned before payment completion"
        ),
        "renewal_success_rate": MetricDefinition(
            metric_name="renewal_success_rate",
            definition_version="v1.1.0",
            polarity="higher_is_better",
            unit="ratio",
            entity="customer",
            cohort_window_days=30,
            step_from="subscription.activated",
            step_to="subscription.renewed",
            min_sample_threshold=15,
            description="Ratio of active subscribers successfully renewing at billing cadence"
        ),
        "rage_click_session_rate": MetricDefinition(
            metric_name="rage_click_session_rate",
            definition_version="v1.1.0",
            polarity="lower_is_better",
            unit="ratio",
            entity="session",
            min_sample_threshold=20,
            description="Rage clicks on plan tier selection cards or payment triggers"
        ),
    }
)


# Master registry mapping template_id -> VerticalTemplate
TEMPLATE_REGISTRY: Dict[str, VerticalTemplate] = {
    ECOMMERCE_TEMPLATE.template_id: ECOMMERCE_TEMPLATE,
    QSR_DELIVERY_TEMPLATE.template_id: QSR_DELIVERY_TEMPLATE,
    SAAS_SUBSCRIPTION_TEMPLATE.template_id: SAAS_SUBSCRIPTION_TEMPLATE,
    TRAVEL_HOSPITALITY_TEMPLATE.template_id: TRAVEL_HOSPITALITY_TEMPLATE,
    FINTECH_LENDING_TEMPLATE.template_id: FINTECH_LENDING_TEMPLATE,
    SUBSCRIPTION_BOX_TEMPLATE.template_id: SUBSCRIPTION_BOX_TEMPLATE,
}


def get_vertical_template(template_id: str) -> VerticalTemplate:
    """
    Retrieves vertical domain template. Fails loudly on unknown templates.
    """
    if template_id not in TEMPLATE_REGISTRY:
        raise KeyError(
            f"Unknown vertical_template_id: '{template_id}'. "
            f"Available templates: {list(TEMPLATE_REGISTRY.keys())}"
        )
    return TEMPLATE_REGISTRY[template_id]
