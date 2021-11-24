from collections import OrderedDict
from typing import List

import numpy as np
import slicer
from MRMLCorePython import vtkMRMLSegmentationNode
from vtkSegmentationCorePython import vtkSegmentation

from utils import node_utils, generate_colors
from mimage_utils.common.zarr_io.segmentation_zarr_io import SegmentationZarrReader, SegmentationZarrWriter


class SlicerSegmentZarrReader(SegmentationZarrReader):

    def read_to_segmentation_node(
            self,
            seg_node: vtkMRMLSegmentationNode,
            segment_labels: List[str]
    ):
        colors = generate_colors(len(segment_labels), 0)
        label_colors = OrderedDict(list(zip(segment_labels, colors)))

        for i, es in enumerate(sorted(self._segment_group)):
            if es not in label_colors:
                label_colors[es] = generate_colors(1, i)[0]

        for segment_name in sorted(self._segment_group):
            mask_arr, attrs = self.read_segmentation(segment_name)

            node_utils.create_new_segment(
                segment_name,
                seg_node,
                mask_arr if np.count_nonzero(mask_arr) else None,
                color=label_colors[segment_name]
            )


class SlicerSegmentZarrWriter(SegmentationZarrWriter):

    def write_segmentation_node(
            self,
            seg_node: vtkMRMLSegmentationNode
    ) -> List[str]:
        seg: vtkSegmentation = seg_node.GetSegmentation()

        written_segment_ids = []

        for segment in [seg.GetNthSegment(i) for i in range(seg.GetNumberOfSegments())]:
            segment_id = seg.GetSegmentIdBySegmentName(segment.GetName())

            segment_mask: np.ndarray = slicer.util.arrayFromSegmentBinaryLabelmap(seg_node, segment_id)

            self.write_segmentation(segment.GetName(), segment_mask.astype(np.uint8))
            written_segment_ids.append(segment_id)

        return written_segment_ids
