from pathlib import Path
from typing import Dict, Any, Tuple

import numpy as np
import zarr
from numcodecs import Blosc


class BinArrayZarrReader:

    def __init__(self, dest_path: Path):
        self._dest_path = dest_path

        self._store = zarr.ZipStore(dest_path.as_posix(), mode='r')

        self.root: zarr.Group = None

    def __enter__(self):
        self.root = zarr.open(self._store)
        return self

    def __exit__(self, *args):
        self._store.close()
        self.root = None

    @staticmethod
    def read_bin_array(
            name: str,
            group: zarr.Group
    ) -> Tuple[np.ndarray, Dict]:
        arr: zarr.Array = group[name]
        arr_shape = arr.attrs['packed_shape']

        if arr.attrs['empty']:
            bin_array = np.zeros(arr_shape, dtype=np.uint8)
        else:
            bin_array = np.unpackbits(arr[:], count=int(np.prod(arr_shape))).reshape(arr_shape)

        attrs = arr.attrs.asdict()
        attrs.pop('empty')
        attrs.pop('packed_shape')

        return bin_array, attrs


class BinArrayZarrWriter:

    def __init__(self, src_path: Path):
        self._src_path = src_path

        self._store = zarr.ZipStore(src_path.as_posix(), mode='w')
        self._compressor = Blosc(cname='zstd', clevel=3, shuffle=Blosc.BITSHUFFLE)

        self.root: zarr.Group = None

    def __enter__(self):
        self.root = zarr.open(self._store)
        return self

    def __exit__(self, *args):
        self._store.close()
        self.root = None

    def write_bin_array(
            self,
            name: str,
            bin_array: np.ndarray,
            group: zarr.Group,
            attrs: Dict[str, Any] = None
    ) -> zarr.Array:
        assert bin_array.dtype != np.uint8
        assert bin_array.dtype != np.bool

        if np.count_nonzero(bin_array) == 0:
            empty = True
            ds = group.create_dataset(name, data=np.array([], dtype=np.uint8))
        else:
            empty = False
            ds = group.create_dataset(name, data=np.packbits(bin_array), compressor=self._compressor)

        ds.attrs['empty'] = empty
        ds.attrs['packed_shape'] = bin_array.shape

        if attrs is not None:
            for n, v in attrs.items():
                ds.attrs[n] = v

        return ds
