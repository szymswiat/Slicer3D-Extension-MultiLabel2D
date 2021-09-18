import logging
from pathlib import Path
from typing import List, Dict

import MRMLCorePython as mp
import qt
import slicer
from SegmentEditor import SegmentEditorWidget
from slicer.ScriptedLoadableModule import *
from vtkSegmentationCorePython import vtkSegmentation

from utils import node_utils, data_utils

try:
    import h5py
    import pandas
except ModuleNotFoundError:
    pass

logger = logging.getLogger('MultiLabel2D')


class VolumeNotSelected(Exception):
    pass


#
# MultiLabel2D
#

class MultiLabel2D(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "MultiLabel2D"
        self.parent.categories = ['', 'CxrAI']
        self.parent.dependencies = ['SegmentEditor', 'Segmentations']
        self.parent.contributors = ["szymswiat"]
        self.parent.helpText = 'MultiLabel2D'
        self.parent.acknowledgementText = 'MultiLabel2D'


#
# MultiLabel2DWidget
#

class MultiLabel2DWidget(SegmentEditorWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        SegmentEditorWidget.__init__(self, parent)

        self.logic: MultiLabel2DLogic = None
        self._ui = None
        self._editor_ui = None
        self._segment_labels: List[str] = None

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """

        try:
            import h5py
            import pandas
        except ModuleNotFoundError:
            if slicer.util.confirmOkCancelDisplay(
                    "This module requires following Python packages: "
                    "'h5py', 'pandas'. Click OK to install now."
            ):
                slicer.util.pip_install('h5py')
                slicer.util.pip_install('pandas')
            import h5py
            import pandas

        # seg_editor_widget: SegmentEditorWidget = slicer.modules.segmenteditor.createNewWidgetRepresentation()
        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        ui_widget = slicer.util.loadUI(self.resourcePath('UI/MultiLabel2D.ui'))
        self.layout.addWidget(ui_widget)
        # self.layout.addWidget(seg_editor_widget)
        self._ui = slicer.util.childWidgetVariables(ui_widget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        ui_widget.setMRMLScene(slicer.mrmlScene)

        # Buttons
        self._ui.saveSegmentsButton.connect('clicked(bool)', self.on_save_segments_button)
        self._ui.loadSegmentsButton.connect('clicked(bool)', self.on_load_segments_button)
        self._ui.initializeSegmentsButton.connect('clicked(bool)', self.on_initialize_segments_for_current_volume)

        self._ui.volumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self._ui.volumeSelector.selectNodeUponCreation = True
        self._ui.volumeSelector.addEnabled = False
        self._ui.volumeSelector.removeEnabled = True
        self._ui.volumeSelector.showHidden = False
        self._ui.volumeSelector.setMRMLScene(slicer.mrmlScene)
        self._ui.volumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.on_volume_node_changed)

        self.logic = MultiLabel2DLogic()

        defaultSegmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
        defaultSegmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)
        slicer.mrmlScene.AddDefaultNode(defaultSegmentEditorNode)

        SegmentEditorWidget.setup(self)
        self._editor_ui = slicer.util.childWidgetVariables(self.editor)

        # self._editor_ui.SegmentationNodeComboBox.enabled = False
        # self._editor_ui.MasterVolumeNodeComboBox.enabled = False

    def cleanup(self):
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()
        SegmentEditorWidget.cleanup(self)

    def enter(self):
        SegmentEditorWidget.enter(self)

    @property
    def segment_labels(self) -> List[str]:
        if self._segment_labels is not None:
            return self._segment_labels

        with open('/home/szymswiat/dev/CxrAI/illnesses.txt', 'r') as f:
            self._segment_labels = f.readlines()

        return self._segment_labels

    def on_save_segments_button(self):
        try:
            volume_node = self._get_current_volume()
        except VolumeNotSelected:
            return

        save_dir = qt.QFileDialog().getExistingDirectory()
        if save_dir == '':
            return

        masks = node_utils.get_mask_segments_for_volume(volume_node)

        mask_file_name = Path(save_dir, f'{Path(volume_node.GetName()).stem}.h5.seg')
        if mask_file_name.exists():
            if slicer.util.confirmOkCancelDisplay(
                    windowTitle='File already exists.',
                    text=f'File {mask_file_name.name} found under selected directory {mask_file_name.parent}.',
            ):
                return

        data_utils.write_segments_to_h5(mask_file_name.as_posix(), masks)

    def on_load_segments_button(self):
        file_path = qt.QFileDialog().getOpenFileName()
        if file_path == '':
            return

        try:
            volume_node = self._get_current_volume()
        except VolumeNotSelected:
            return

        seg_node = data_utils.load_segments_from_h5(volume_node, file_path)
        self._editor_ui.SegmentationNodeComboBox.setCurrentNode(seg_node)

    def on_load_segments_all_button(self):
        load_dir = qt.QFileDialog().getExistingDirectory()
        if load_dir == '':
            return

        for name, volume_node in node_utils.get_nodes_by_class('vtkMRMLScalarVolumeNode').items():
            segment_file_path = Path(load_dir, f'{Path(name).stem}.h5.seg')
            if not segment_file_path.exists():
                continue
            seg_node = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode', by_name=name)
            if seg_node is not None:
                if not slicer.util.confirmOkCancelDisplay(
                        windowTitle='Discard changes.',
                        text=f'Do you want to override segments of {name} volume?.',
                ):
                    continue
            data_utils.load_segments_from_h5(volume_node, segment_file_path.as_posix())

    def on_initialize_segments_for_current_volume(self):
        try:
            volume_node = self._get_current_volume()
        except VolumeNotSelected:
            return

        seg_node = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode', volume_node.GetName())

        if seg_node is None:
            seg_node = node_utils.create_segment_node_for_volume(volume_node)
            self._editor_ui.SegmentationNodeComboBox.setCurrentNode(seg_node)
            node_utils.create_empty_segments(seg_node, self.segment_labels)

    def on_volume_node_changed(self, volume_node: mp.vtkMRMLScalarVolumeNode):
        if volume_node is None:
            logger.error(f'No scalar volume selected.')
            return
        logger.info(f'Selected scalar volume: {volume_node.GetName()}.')

        slicer.util.setSliceViewerLayers(background=volume_node)

        seg_nodes: Dict[str, mp.vtkMRMLSegmentationNode] = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode')
        seg_node_visible: mp.vtkMRMLSegmentationNode = seg_nodes.pop(volume_node.GetName(), None)

        if seg_node_visible is None:
            return

        # for _, seg_node in seg_nodes.items():
        #     self.set_visibility_of_segments_for_segment_node(seg_node, False)
        #
        # self.set_visibility_of_segments_for_segment_node(seg_node_visible, True)
        self._editor_ui.SegmentationNodeComboBox.setCurrentNode(seg_node_visible)

    def set_visibility_of_segments_for_segment_node(self, seg_node: mp.vtkMRMLSegmentationNode, visible: bool):
        segmentation: vtkSegmentation = seg_node.GetSegmentation()
        segment_ids = [segmentation.GetNthSegmentID(i) for i in range(segmentation.GetNumberOfSegments())]

        if visible:
            self._editor_ui.SegmentsTableView.setSelectedSegmentIDs(segment_ids)
            self._editor_ui.SegmentsTableView.showOnlySelectedSegments()
            self._editor_ui.SegmentsTableView.clearSelection()

        else:
            self._editor_ui.SegmentsTableView.clearSelection()
            self._editor_ui.SegmentsTableView.showOnlySelectedSegments()

    def _get_current_volume(self) -> mp.vtkMRMLScalarVolumeNode:
        volume_node_id = self._ui.volumeSelector.currentNodeID

        if volume_node_id == '':
            slicer.util.infoDisplay(f'Please select volume.')
            raise VolumeNotSelected()

        return slicer.util.getNode(volume_node_id)


#
# MultiLabel2DLogic
#

class MultiLabel2DLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self):
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)

    #


# MultiLabel2DTest
#

class MultiLabel2DTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        pass

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        self.test_MultiLabel2D1()

    def test_MultiLabel2D1(self):
        """ Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """

        self.delayDisplay("Starting the test")
