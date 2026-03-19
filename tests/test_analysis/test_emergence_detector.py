"""Tests for EmergenceDetector."""
import pytest
from tecs.config import EmergenceConfig
from tecs.analysis.emergence_detector import EmergenceDetector


def test_no_spike_early_generations():
    cfg = EmergenceConfig(min_generations=3)
    detector = EmergenceDetector(cfg)
    event = detector.check(generation=1, metrics={"betti_0": 5, "betti_1": 2})
    assert event is None


def test_detects_betti_spike():
    cfg = EmergenceConfig(min_generations=3, sigma_threshold=2.0, window_size=10)
    detector = EmergenceDetector(cfg)
    for i in range(10):
        detector.check(generation=i, metrics={"betti_1": 2.0})
    event = detector.check(generation=10, metrics={"betti_1": 10.0})
    assert event is not None
    assert event["metric"] == "betti_1"


def test_detects_lyapunov_sign_change():
    cfg = EmergenceConfig(min_generations=3)
    detector = EmergenceDetector(cfg)
    for i in range(5):
        detector.check(generation=i, metrics={"lyapunov_exponent": -0.5})
    event = detector.check(generation=5, metrics={"lyapunov_exponent": 0.3})
    assert event is not None


def test_sliding_window():
    cfg = EmergenceConfig(window_size=10)
    detector = EmergenceDetector(cfg)
    assert detector._window_size == 10


def test_no_spike_when_metrics_are_stable():
    cfg = EmergenceConfig(min_generations=3, sigma_threshold=2.0, window_size=10)
    detector = EmergenceDetector(cfg)
    for i in range(15):
        event = detector.check(generation=i, metrics={"betti_1": 2.0 + i * 0.001})
    # Stable increments should not trigger a spike
    assert event is None


def test_order_parameter_r_rate_spike():
    cfg = EmergenceConfig(min_generations=3, r_threshold=0.2)
    detector = EmergenceDetector(cfg)
    for i in range(5):
        detector.check(generation=i, metrics={"order_parameter_r": 0.5})
    event = detector.check(generation=5, metrics={"order_parameter_r": 0.9})
    assert event is not None
    assert event["metric"] == "order_parameter_r"
    assert event["type"] == "rate_spike"


def test_phi_threshold_exceeded():
    cfg = EmergenceConfig(min_generations=3, phi_critical=1.0)
    detector = EmergenceDetector(cfg)
    for i in range(5):
        detector.check(generation=i, metrics={"phi": 0.5})
    event = detector.check(generation=5, metrics={"phi": 1.5})
    assert event is not None
    assert event["metric"] == "phi"
    assert event["type"] == "threshold_exceeded"


def test_integrated_information_threshold():
    cfg = EmergenceConfig(min_generations=3, phi_critical=1.0)
    detector = EmergenceDetector(cfg)
    for i in range(5):
        detector.check(generation=i, metrics={"integrated_information": 0.3})
    event = detector.check(generation=5, metrics={"integrated_information": 2.0})
    assert event is not None
    assert event["type"] == "threshold_exceeded"


def test_lyapunov_no_spike_both_negative():
    cfg = EmergenceConfig(min_generations=3)
    detector = EmergenceDetector(cfg)
    for i in range(5):
        detector.check(generation=i, metrics={"lyapunov_exponent": -0.5})
    event = detector.check(generation=5, metrics={"lyapunov_exponent": -0.1})
    assert event is None


def test_no_spike_below_min_generations():
    cfg = EmergenceConfig(min_generations=10)
    detector = EmergenceDetector(cfg)
    for i in range(5):
        event = detector.check(generation=i, metrics={"betti_1": float(i * 100)})
    # All below min_generations=10, none should trigger
    assert event is None


def test_check_returns_none_with_no_history_for_metric():
    cfg = EmergenceConfig(min_generations=3)
    detector = EmergenceDetector(cfg)
    # First check at generation=3, only one point, no previous — no spike
    event = detector.check(generation=3, metrics={"betti_0": 5.0})
    assert event is None


def test_sigma_spike_event_has_expected_fields():
    cfg = EmergenceConfig(min_generations=3, sigma_threshold=2.0, window_size=10)
    detector = EmergenceDetector(cfg)
    for i in range(10):
        detector.check(generation=i, metrics={"euler": 1.0})
    event = detector.check(generation=10, metrics={"euler": 100.0})
    assert event is not None
    assert event["type"] == "sigma_spike"
    assert "sigma" in event
    assert event["generation"] == 10
