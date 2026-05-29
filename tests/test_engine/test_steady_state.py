import pytest
import numpy as np
from matlab_mcp_server.engine.steady_state import SteadyStateDetector


def test_no_convergence_initially():
    det = SteadyStateDetector(window_size=5, mean_tol=1e-3, std_tol=1e-3)
    for i in range(3):
        det.update(np.sin(i * 0.1) + np.random.randn() * 0.5)
    assert not det.is_converged


def test_convergence_after_stable_input():
    det = SteadyStateDetector(window_size=5, mean_tol=1e-2, std_tol=1e-2)
    for _ in range(10):
        det.update(3.300 + np.random.randn() * 1e-5)
    assert det.is_converged
    assert det.convergence_index is not None


def test_no_convergence_with_oscillation():
    det = SteadyStateDetector(window_size=5, mean_tol=1e-3, std_tol=1e-3)
    for i in range(20):
        det.update(np.sin(i))
    assert not det.is_converged


def test_reset_clears_state():
    det = SteadyStateDetector(window_size=3, mean_tol=1e-2, std_tol=1e-2)
    for _ in range(5):
        det.update(5.0)
    assert det.is_converged
    det.reset()
    assert not det.is_converged
    assert det.convergence_index is None
