# tests/test_engine/test_scale_controller.py
from tecs.config import ScalingConfig
from tecs.engine.scale_controller import ScaleController


def test_starts_at_phase1():
    cfg = ScalingConfig(phase1_nodes=100, phase2_nodes=1000, phase5_nodes=10000)
    sc = ScaleController(cfg)
    assert sc.current_nodes == 100


def test_scales_up_on_phase_2():
    cfg = ScalingConfig(phase1_nodes=100, phase2_nodes=1000, phase5_nodes=10000)
    sc = ScaleController(cfg)
    sc.on_phase_change(2)
    assert sc.current_nodes == 1000


def test_scales_up_on_phase_3():
    cfg = ScalingConfig(phase1_nodes=100, phase2_nodes=1000, phase5_nodes=10000)
    sc = ScaleController(cfg)
    sc.on_phase_change(3)
    assert sc.current_nodes == 1000


def test_scales_up_on_phase_4():
    cfg = ScalingConfig(phase1_nodes=100, phase2_nodes=1000, phase5_nodes=10000)
    sc = ScaleController(cfg)
    sc.on_phase_change(4)
    assert sc.current_nodes == 1000


def test_scales_up_on_phase_5():
    cfg = ScalingConfig()
    sc = ScaleController(cfg)
    sc.on_phase_change(5)
    assert sc.current_nodes == 10000


def test_phase_1_resets():
    cfg = ScalingConfig(phase1_nodes=100, phase2_nodes=1000, phase5_nodes=10000)
    sc = ScaleController(cfg)
    sc.on_phase_change(2)
    assert sc.current_nodes == 1000
    sc.on_phase_change(1)
    assert sc.current_nodes == 100


def test_max_generations():
    cfg = ScalingConfig(phase1_max_gen=30, phase2_max_gen=50)
    sc = ScaleController(cfg)
    assert sc.max_generations(1) == 30
    assert sc.max_generations(2) == 50


def test_max_generations_phase3_uses_phase2():
    cfg = ScalingConfig(phase1_max_gen=30, phase2_max_gen=50)
    sc = ScaleController(cfg)
    assert sc.max_generations(3) == 50


def test_memory_check():
    cfg = ScalingConfig()
    sc = ScaleController(cfg)
    result = sc.check_memory_ok(max_pct=99)
    assert isinstance(result, bool)


def test_memory_check_returns_bool_for_strict():
    cfg = ScalingConfig()
    sc = ScaleController(cfg)
    # With 0% threshold the result depends on psutil availability, but must be bool
    result = sc.check_memory_ok(max_pct=0)
    assert isinstance(result, bool)
