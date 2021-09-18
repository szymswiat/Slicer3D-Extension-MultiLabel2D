from typing import Dict

import MRMLCorePython as mp
import numpy as np
import slicer

from utils import node_utils

try:
    import h5py
    import pandas
except ModuleNotFoundError:
    pass


def write_segments_to_h5(
        file_name: str,
        masks: Dict[str, np.ndarray]
):
    seg_file = h5py.File(file_name, mode='x')
    seg_group = seg_file.create_group('segmentations')

    for mask_name, mask in masks.items():
        ds = seg_group.create_dataset(mask_name, data=np.packbits(mask), compression='gzip')
        ds.attrs.create('shape', data=mask.shape)

    seg_file.close()


def load_segments_from_h5(
        volume_node: mp.vtkMRMLScalarVolumeNode,
        seg_file_path: str
) -> mp.vtkMRMLSegmentationNode:
    seg_node: mp.vtkMRMLSegmentationNode = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode',
                                                                         by_name=volume_node.GetName())
    if seg_node is not None:
        slicer.mrmlScene.RemoveNode(seg_node)

    seg_node = node_utils.create_segment_node_for_volume(volume_node)

    seg_file = h5py.File(seg_file_path, mode='r')

    seg_data = seg_file['segmentations']
    for segment_name in seg_data:
        ds = seg_data[segment_name]
        shape = ds.attrs['shape']
        arr = np.unpackbits(ds[:], count=int(np.prod(shape))).reshape(shape)
        node_utils.create_new_segment(segment_name, seg_node, arr)

    return seg_node