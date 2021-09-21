from collections import OrderedDict
from pathlib import Path
from typing import List, Dict, Union, Tuple

import numpy as np
import slicer
from MRMLCorePython import vtkMRMLScalarVolumeNode, vtkMRMLSegmentationNode, vtkMRMLNode
from vtkSegmentationCorePython import vtkSegmentation

from utils import generate_colors


def create_segment_node_for_volume(
        volume_node: vtkMRMLScalarVolumeNode
) -> vtkMRMLSegmentationNode:
    seg_node: vtkMRMLSegmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    seg_node.SetName(volume_node.GetName())
    seg_node.SetReferenceImageGeometryParameterFromVolumeNode(volume_node)
    seg_node.SetMasterRepresentationToBinaryLabelmap()
    return seg_node


def create_empty_segments(
        seg_node: vtkMRMLSegmentationNode,
        segment_labels: List[str]
):
    segmentation: vtkSegmentation = seg_node.GetSegmentation()
    existing_segments = [segmentation.GetNthSegment(i).GetName()
                         for i in range(segmentation.GetNumberOfSegments())]

    colors = generate_colors(len(segment_labels), 0)
    label_colors = OrderedDict(list(zip(segment_labels, colors)))

    for seg_name, color in label_colors.items():
        if seg_name in existing_segments:
            continue
        segment_id = create_new_segment(seg_name, seg_node)
        segment = segmentation.GetSegment(segment_id)
        segment.SetColor(color)


def create_new_segment(
        name: str,
        seg_node: vtkMRMLSegmentationNode,
        initial_value: np.ndarray = None,
        color: Tuple[float, ...] = None
) -> str:
    segment_id = seg_node.GetSegmentation().AddEmptySegment('', name, color)
    if initial_value is not None:
        slicer.util.updateSegmentBinaryLabelmapFromArray(initial_value, seg_node, segment_id)

    return segment_id


def get_path_of_node(node) -> Path:
    storage_node = node.GetStorageNode()
    if storage_node is not None:  # loaded via drag-drop
        filepath = storage_node.GetFullNameFromFileName()
    else:  # Loaded via DICOM browser
        instance_ui_ds = node.GetAttribute("DICOM.instanceUIDs").split()
        filepath = slicer.dicomDatabase.fileForInstance(instance_ui_ds[0])
    return Path(filepath)


def get_nodes_by_class(
        cls: str,
        by_name: str = None
) -> Union[vtkMRMLNode, Dict[str, vtkMRMLNode]]:
    nodes = slicer.util.getNodesByClass(cls)
    nodes = {n.GetName(): n for n in nodes}
    if by_name:
        return nodes.get(by_name, None)
    return nodes
