import numpy as np
from collections import deque
from typing import Optional


class SteadyStateDetector:
    def __init__(self, window_size: int = 10, mean_tol: float = 1e-3,
                 std_tol: float = 1e-3):
        self.window_size = window_size
        self.mean_tol = mean_tol
        self.std_tol = std_tol
        self._window: deque = deque(maxlen=window_size)
        self._converged_count: int = 0
        self._is_converged: bool = False
        self._convergence_index: Optional[int] = None
        self._sample_count: int = 0

    @property
    def is_converged(self) -> bool:
        return self._is_converged

    @property
    def convergence_index(self) -> Optional[int]:
        return self._convergence_index

    def update(self, value: float) -> bool:
        self._sample_count += 1
        self._window.append(value)

        if len(self._window) < self.window_size:
            return False

        arr = np.array(self._window)
        current_mean = np.mean(arr)
        current_std = np.std(arr)

        if len(self._window) >= 2:
            prev = np.array(list(self._window)[:-1])
            prev_mean = np.mean(prev)
            delta_mean = abs(current_mean - prev_mean)
        else:
            delta_mean = float("inf")

        if delta_mean < self.mean_tol and current_std < self.std_tol:
            self._converged_count += 1
        else:
            self._converged_count = 0

        if self._converged_count >= self.window_size:
            self._is_converged = True
            self._convergence_index = self._sample_count
            return True

        return False

    def get_final_stats(self) -> dict:
        if not self._window:
            return {}
        arr = np.array(self._window)
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
        }

    def reset(self):
        self._window.clear()
        self._converged_count = 0
        self._is_converged = False
        self._convergence_index = None
        self._sample_count = 0
