from collections import OrderedDict
from typing import Dict, Optional, List, Tuple

import MRMLCorePython as mp
import numpy as np
import slicer
from vtkSegmentationCorePython import vtkSegmentation, vtkOrientedImageData

from utils import node_utils

try:
    import h5py
except ModuleNotFoundError:
    pass


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

    seg_file = h5py.File(seg_file_path, mode='r')
    seg_data = seg_file['segmentations']

    colors = generate_colors(len(segment_labels), 0)
    label_colors = OrderedDict(list(zip(segment_labels, colors)))

    for i, es in enumerate(sorted(seg_data)):
        if es not in label_colors:
            label_colors[es] = generate_colors(1, i)[0]

    for segment_name in sorted(seg_data):
        ds = seg_data[segment_name]
        mask_shape = ds.attrs['mask_shape']
        mask_coords = ds.attrs['mask_coords']
        mask_arr = np.unpackbits(ds[:], count=int(np.prod(mask_shape))).reshape(mask_shape)

        mask = np.zeros(shape=ds.attrs['volume_shape'], dtype=np.uint8)

        # slice_start
        ss = mask_coords
        # slice_end
        se = [c + s for c, s in zip(mask_coords, mask_shape)]

        mask[ss[0]: se[0], ss[1]: se[1], ss[2]: se[2]] = mask_arr

        node_utils.create_new_segment(
            segment_name,
            seg_node,
            mask if np.count_nonzero(mask) else None,
            color=label_colors[segment_name]
        )

    return seg_node


def write_segments_to_h5(
        file_name: str,
        segment_data: Dict
):
    seg_file = h5py.File(file_name, mode='w')
    seg_group = seg_file.create_group('segmentations')

    for segment_name, data in segment_data.items():
        ds = seg_group.create_dataset(segment_name, data=np.packbits(data['mask']), compression='gzip')
        ds.attrs.create('mask_shape', data=data['mask'].shape)
        # ds.attrs.create('color', data=np.array(data['segment'].GetColor(), dtype=float))
        ds.attrs.create('volume_shape', data=data['volume_shape'])
        ds.attrs.create('mask_coords', data=data['coords'])

    seg_file.close()


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
        segment_data: vtkOrientedImageData = seg_node.GetBinaryLabelmapInternalRepresentation(segment_id)
        extent = segment_data.GetExtent()

        coords = [extent[4], extent[2], extent[0]]

        all_segment_data[segment.GetName()] = dict(
            segment=segment,
            mask=segment_mask,
            coords=coords,
            volume_shape=slicer.util.arrayFromVolume(volume_node).shape
        )

    return all_segment_data
