from typing import List, Tuple, Callable, Any

import numpy as np
import qt


class VolumeNotSelected(Exception):
    pass


def generate_colors(count: int, seed: int) -> List[Tuple[float, ...]]:
    np.random.seed(seed)
    return [tuple(np.random.rand(3).astype(float)) for _ in range(count)]


def run_with_interval_forever(fn: Callable[[Any], Any], interval: int, **kwargs):
    def task():
        fn(**kwargs)
        qt.QTimer.singleShot(interval * 1000, task)

    qt.QTimer.singleShot(1, task)
