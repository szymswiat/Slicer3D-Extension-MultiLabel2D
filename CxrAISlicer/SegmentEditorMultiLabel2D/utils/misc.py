from typing import List, Tuple

import numpy as np


class VolumeNotSelected(Exception):
    pass


def generate_colors(count: int, seed: int) -> List[Tuple[float, ...]]:
    np.random.seed(seed)
    return [tuple(np.random.rand(3).astype(float)) for _ in range(count)]
