# pyrefly: ignore [missing-import]
import pytest
from fastapi.testclient import TestClient
from main import app
from metrics_engine import MetricsEngine, EcommerceMetricsProvider, SaaSMetricsProvider, BookingsMetricsProvider, MediaMetricsProvider
from digest_engine import DigestEngine

client = TestClient(app)


class TestMetricsEngine:
    """Tests for Component 1: Metrics Engine"""

    def test_ecommerce_metrics_deterministic_and_grounded(self):
        engine = MetricsEngine()
        metrics = engine.query_all_metrics("ecommerce", timeframe="7d", prior=False)

        assert "checkout_drop_off_rate" in metrics
        assert "cart_abandonment_rate" in metrics
        assert "dormant_cart_cohort" in metrics
        assert "per_step_funnel_conversion" in metrics

        checkout_drop = metrics["checkout_drop_off_rate"]
        assert checkout_drop.value == 44.27
        assert checkout_drop.unit == "percentage"
        assert checkout_drop.sample_size == 1240
        assert checkout_drop.vertical_template_id == "ecommerce"
        assert "T" in checkout_drop.calculated_at  # Valid ISO timestamp

    def test_vertical_parameterization_isolation(self):
        engine = MetricsEngine()

        # SaaS should have SaaS terms, zero ecommerce terms
        saas_metrics = engine.query_all_metrics("saas", timeframe="7d")
        assert "trial_to_activation_drop_off_rate" in saas_metrics
        assert "trial_conversion_rate" in saas_metrics
        assert "checkout_drop_off_rate" not in saas_metrics

        # Bookings should have booking terms
        bookings_metrics = engine.query_all_metrics("bookings", timeframe="7d")
        assert "booking_slot_drop_off_rate" in bookings_metrics
        assert "booking_conversion_rate" in bookings_metrics
        assert "cart_abandonment_rate" not in bookings_metrics

        # Media should have paywall terms
        media_metrics = engine.query_all_metrics("media", timeframe="7d")
        assert "paywall_bounce_rate" in media_metrics
        assert "paywall_conversion_rate" in media_metrics

    def test_prior_period_comparison_support(self):
        engine = MetricsEngine()
        curr = engine.query_metric("ecommerce", "checkout_drop_off_rate", prior=False)
        prior = engine.query_metric("ecommerce", "checkout_drop_off_rate", prior=True)

        assert curr is not None and prior is not None
        assert curr.value == 44.27
        assert prior.value == 38.10
        assert curr.sample_size != prior.sample_size


class TestDigestEngine:
    """Tests for Component 2: Digest Engine"""

    def test_calculate_delta_formula_and_edge_cases(self):
        # Normal positive and negative deltas
        assert DigestEngine.calculate_delta(110.0, 100.0) == 10.0
        assert DigestEngine.calculate_delta(85.0, 100.0) == -15.0

        # Zero division edge cases
        assert DigestEngine.calculate_delta(0.0, 0.0) == 0.0
        assert DigestEngine.calculate_delta(50.0, 0.0) == 100.0
        assert DigestEngine.calculate_delta(-50.0, 0.0) == -100.0

    def test_severity_classification(self):
        assert DigestEngine.determine_severity(12.5) == "low"
        assert DigestEngine.determine_severity(24.0) == "medium"
        assert DigestEngine.determine_severity(38.5) == "high"

    def test_digest_threshold_filtering(self):
        engine = DigestEngine()

        # Run with standard 10% threshold
        report_10 = engine.run_digest(vertical_template_id="ecommerce", threshold_pct=10.0)
        assert report_10.total_metrics_evaluated == 4
        assert report_10.flags_count > 0

        for flag in report_10.flags:
            assert abs(flag.delta_pct) >= 10.0
            assert flag.current_sample_size > 0
            assert flag.prior_sample_size > 0
            assert flag.severity in ["low", "medium", "high"]

        # Run with strict 40% threshold: only large moves should be flagged
        report_40 = engine.run_digest(vertical_template_id="ecommerce", threshold_pct=40.0)
        for flag in report_40.flags:
            assert abs(flag.delta_pct) >= 40.0

        # Flags count at 40% must be <= flags count at 10%
        assert report_40.flags_count <= report_10.flags_count


class TestModule4ApiEndpoints:
    """Tests for FastAPI endpoints in main.py"""

    def test_get_metrics_endpoint(self):
        res = client.get("/api/v1/module4/metrics?vertical=ecommerce&timeframe=7d")
        assert res.status_code == 200
        data = res.json()
        assert data["vertical_template_id"] == "ecommerce"
        assert data["count"] == 4
        assert "checkout_drop_off_rate" in data["metrics"]

    def test_get_single_metric_endpoint(self):
        res = client.get("/api/v1/module4/metrics/checkout_drop_off_rate?vertical=ecommerce")
        assert res.status_code == 200
        data = res.json()
        assert data["metric_name"] == "checkout_drop_off_rate"
        assert data["value"] == 44.27
        assert data["sample_size"] == 1240

    def test_single_metric_not_found(self):
        res = client.get("/api/v1/module4/metrics/non_existent_metric?vertical=ecommerce")
        assert res.status_code == 404

    def test_get_digest_endpoint(self):
        res = client.get("/api/v1/module4/digest?vertical=ecommerce&threshold_pct=10.0")
        assert res.status_code == 200
        data = res.json()
        assert data["vertical_template_id"] == "ecommerce"
        assert data["threshold_pct"] == 10.0
        assert "flags" in data
        assert isinstance(data["flags"], list)
        assert data["flags_count"] == len(data["flags"])
