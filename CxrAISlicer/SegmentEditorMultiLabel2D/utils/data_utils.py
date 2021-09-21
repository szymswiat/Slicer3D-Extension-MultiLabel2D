from collections import OrderedDict
from typing import Dict, Optional, List, Tuple

import MRMLCorePython as mp
import numpy as np
import slicer
from vtkSegmentationCorePython import vtkSegmentation, vtkOrientedImageData
import zarr
from numcodecs import Blosc

from utils import node_utils


def generate_colors(count: int, seed: int) -> List[Tuple[float, ...]]:
    np.random.seed(seed)
    return [tuple(np.random.rand(3).astype(float)) for _ in range(count)]


def load_segments_from_h5(
        volume_node: mp.vtkMRMLScalarVolumeNode,
        seg_file_path: str,
        segment_labels: List[str]
) -> mp.vtkMRMLSegmentationNode:
    seg_node: mp.vtkMRMLSegmentationNode = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode',
                                                                         by_name=volume_node.GetName())
    if seg_node is not None:
        slicer.mrmlScene.RemoveNode(seg_node)

    seg_node = node_utils.create_segment_node_for_volume(volume_node)

    store = zarr.ZipStore(seg_file_path, mode='r')
    seg_file = zarr.open(store=store)
    seg_data = seg_file['segmentations']

    colors = generate_colors(len(segment_labels), 0)
    label_colors = OrderedDict(list(zip(segment_labels, colors)))

    for i, es in enumerate(sorted(seg_data)):
        if es not in label_colors:
            label_colors[es] = generate_colors(1, i)[0]

    for segment_name in sorted(seg_data):
        ds = seg_data[segment_name]
        mask_shape = ds.attrs['mask_shape']
        mask_arr = np.unpackbits(ds[:], count=int(np.prod(mask_shape))).reshape(mask_shape)

        node_utils.create_new_segment(
            segment_name,
            seg_node,
            mask_arr if np.count_nonzero(mask_arr) else None,
            color=label_colors[segment_name]
        )

    store.close()
    return seg_node


def write_segments_to_h5(
        file_name: str,
        segment_data: Dict
):
    with zarr.ZipStore(file_name, mode='w') as store:
        compressor = Blosc(cname='zstd', clevel=3, shuffle=Blosc.BITSHUFFLE)
        seg_file = zarr.open(store=store)

        seg_group = seg_file.create_group('segmentations')
        for segment_name, data in segment_data.items():
            ds = seg_group.create_dataset(segment_name,
                                          data=np.packbits(data['mask'].astype(np.uint8)),
                                          compressor=compressor)
            ds.attrs['mask_shape'] = list(data['mask'].shape)
            # ds.attrs.create('color', data=np.array(data['segment'].GetColor(), dtype=float))
            ds.attrs['volume_shape'] = list(data['volume_shape'])


def get_segments_data_for_volume(
        volume_node: mp.vtkMRMLScalarVolumeNode
) -> Optional[Dict]:
    seg_node: mp.vtkMRMLSegmentationNode = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode',
                                                                         volume_node.GetName())

    if seg_node is None:
        slicer.util.errorDisplay(f'There is no segmentation node for current volume node.')
        return None

    seg: vtkSegmentation = seg_node.GetSegmentation()

    all_segment_data = {}

    for segment in [seg.GetNthSegment(i) for i in range(seg.GetNumberOfSegments())]:
        segment_id = seg_node.GetSegmentation().GetSegmentIdBySegmentName(segment.GetName())

        segment_mask: np.ndarray = slicer.util.arrayFromSegmentBinaryLabelmap(seg_node, segment_id)

        all_segment_data[segment.GetName()] = dict(
            segment=segment,
            mask=segment_mask,
            volume_shape=slicer.util.arrayFromVolume(volume_node).shape
        )

    return all_segment_data
