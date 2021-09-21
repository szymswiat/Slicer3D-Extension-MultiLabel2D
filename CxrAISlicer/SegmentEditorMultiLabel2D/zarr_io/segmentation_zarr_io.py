from pathlib import Path
from typing import Tuple, Dict, List

import numpy as np
import zarr

from zarr_io.bin_array_zarr_io import BinArrayZarrReader, BinArrayZarrWriter


class SegmentationZarrReader(BinArrayZarrReader):

    def __init__(self, dest_path: Path):
        super().__init__(dest_path)

        self._segment_group: zarr.Group = None

    def __enter__(self):
        super().__enter__()
        self._segment_group = self.root['segmentations']
        return self

    def read_segmentation(
            self,
            name: str
    ) -> Tuple[np.ndarray, Dict]:
        return self.read_bin_array(name, self._segment_group)

    def get_segmentation_list(self) -> List[str]:
        return list(self._segment_group)


class SegmentationZarrWriter(BinArrayZarrWriter):

    def __init__(self, src_path: Path):
        super().__init__(src_path)

        self._segment_group: zarr.Group = None

    def __enter__(self):
        super().__enter__()
        self._segment_group = self.root.create_group('segmentations')
        return self

    def write_segmentation(
            self,
            name: str,
            segmentation: np.ndarray
    ) -> zarr.Array:
        return self.write_bin_array(name, segmentation, self._segment_group)
