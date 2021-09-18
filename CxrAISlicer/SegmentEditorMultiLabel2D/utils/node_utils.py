from pathlib import Path
from typing import List, Dict, Union, Optional

import MRMLCorePython as mp
import numpy as np
import slicer
from MRMLCorePython import vtkMRMLDisplayNode
from slicer.util import updateVolumeFromArray
from vtkSegmentationCorePython import vtkSegmentation, vtkSegment
import random

try:
    import h5py
    import pandas
except ModuleNotFoundError:
    pass


def create_segment_node_for_volume(
        volume_node: mp.vtkMRMLScalarVolumeNode
) -> mp.vtkMRMLSegmentationNode:
    seg_node: mp.vtkMRMLSegmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    seg_node.SetName(volume_node.GetName())
    seg_node.SetReferenceImageGeometryParameterFromVolumeNode(volume_node)
    seg_node.SetMasterRepresentationToBinaryLabelmap()
    return seg_node


def create_empty_segments(
        seg_node: mp.vtkMRMLSegmentationNode,
        segment_labels: List[str]
):
    np.random.seed(0)

    for seg_name in segment_labels:
        segment_id = create_new_segment(seg_name, seg_node)
        segmentation: vtkSegmentation = seg_node.GetSegmentation()
        segment = segmentation.GetSegment(segment_id)
        segment.SetColor(list(np.random.rand(3).astype(float)))


def create_new_segment(
        name: str,
        seg_node: mp.vtkMRMLSegmentationNode,
        initial_value: np.ndarray = None,
        color: List[float] = None
) -> str:
    segment_id = seg_node.GetSegmentation().AddEmptySegment('', name, color)
    if initial_value is not None:
        updateSegmentBinaryLabelmapFromArray(initial_value, seg_node, segment_id)

    return segment_id


def get_mask_segments_for_volume(
        volume_node: mp.vtkMRMLScalarVolumeNode
) -> Optional[Dict[str, np.ndarray]]:
    seg_node: mp.vtkMRMLSegmentationNode = get_nodes_by_class('vtkMRMLSegmentationNode', volume_node.GetName())

    if seg_node is None:
        slicer.util.errorDisplay(f'There is no segmentation node for current volume node.')
        return None

    seg: vtkSegmentation = seg_node.GetSegmentation()

    all_segments = {}

    segments = [seg.GetNthSegment(i) for i in range(seg.GetNumberOfSegments())]
    for segment in segments:
        segment_id = seg_node.GetSegmentation().GetSegmentIdBySegmentName(segment.GetName())

        segment_array = np.zeros(shape=slicer.util.arrayFromVolume(volume_node).shape, dtype=np.uint8)

        segment_mask: np.ndarray = slicer.util.arrayFromSegmentBinaryLabelmap(seg_node, segment_id)
        mask_coords = seg_node.GetBinaryLabelmapInternalRepresentation(segment_id).GetExtent()
        mc = mask_coords

        if -1 not in mask_coords:
            segment_array[mc[4]:mc[5] + 1, mc[2]:mc[3] + 1, mc[0]:mc[1] + 1] = segment_mask
        all_segments[segment.GetName()] = segment_array

    return all_segments


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
) -> Union[mp.vtkMRMLNode, Dict[str, mp.vtkMRMLNode]]:
    nodes = slicer.util.getNodesByClass(cls)
    nodes = {n.GetName(): n for n in nodes}
    if by_name:
        return nodes.get(by_name, None)
    return nodes


# TODO: this function is available in newer version of Slicer API (4.13) under slicer.utils
def updateSegmentBinaryLabelmapFromArray(narray, segmentationNode, segmentId, referenceVolumeNode=None):
    """Sets binary labelmap representation of a segment from a numpy array.

    :param segmentationNode: segmentation node that will be updated.
    :param segmentId: ID of the segment that will be updated.
      Can be determined from segment name by calling ``segmentationNode.GetSegmentation().GetSegmentIdBySegmentName(segmentName)``.
    :param referenceVolumeNode: a volume node that determines geometry (origin, spacing, axis directions, extents) of the array.
      If not specified then the volume that was used for setting the segmentation's geometry is used as reference volume.

    :raises RuntimeError: in case of failure

    Voxels values are deep-copied, therefore if the numpy array is modified after calling this method, segmentation node will not change.
    """

    # Export segment as vtkImageData (via temporary labelmap volume node)
    import slicer
    import vtk

    # Get reference volume
    if not referenceVolumeNode:
        referenceVolumeNode = segmentationNode.GetNodeReference(
            slicer.vtkMRMLSegmentationNode.GetReferenceImageGeometryReferenceRole())
        if not referenceVolumeNode:
            raise RuntimeError(
                "No reference volume is found in the input segmentationNode, therefore a valid referenceVolumeNode input is required.")

    # Update segment in segmentation
    labelmapVolumeNode = slicer.modules.volumes.logic().CreateAndAddLabelVolume(referenceVolumeNode, "__temp__")
    try:
        updateVolumeFromArray(labelmapVolumeNode, narray)
        segmentIds = vtk.vtkStringArray()
        segmentIds.InsertNextValue(segmentId)
        if not slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode,
                                                                                     segmentationNode, segmentIds):
            raise RuntimeError("Importing of segment failed.")
    finally:
        slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
