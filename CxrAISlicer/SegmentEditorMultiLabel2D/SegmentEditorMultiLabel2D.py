import slicer

try:
    import zarr
except ModuleNotFoundError:
    slicer.util.pip_install('zarr')

import logging
import shutil
from pathlib import Path
from typing import List, Dict, Optional

import MRMLCorePython as mp
import qt

from SegmentEditor import SegmentEditorWidget
from slicer.ScriptedLoadableModule import *

from utils import node_utils, data_utils, VolumeNotSelected

logger = logging.getLogger('SegmentEditorMultiLabel2D')


#
# SegmentEditorMultiLabel2D
#

class SegmentEditorMultiLabel2D(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Segment Editor Multi-Label 2D"
        self.parent.categories = ['', 'CxrAI']
        self.parent.dependencies = ['SegmentEditor', 'Segmentations']
        self.parent.contributors = ["szymswiat"]
        self.parent.helpText = 'SegmentEditorMultiLabel2D'
        self.parent.acknowledgementText = 'SegmentEditorMultiLabel2D'


#
# SegmentEditorMultiLabel2DWidget
#

class SegmentEditorMultiLabel2DWidget(SegmentEditorWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        SegmentEditorWidget.__init__(self, parent)

        self.logic: SegmentEditorMultiLabel2DLogic = None
        self._ui = None
        self._editor_ui = None
        self._segment_labels: List[str] = None

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """

        ui_widget = slicer.util.loadUI(self.resourcePath('UI/SegmentEditorMultiLabel2D.ui'))
        self.layout.addWidget(ui_widget)
        self._ui = slicer.util.childWidgetVariables(ui_widget)

        ui_widget.setMRMLScene(slicer.mrmlScene)

        # Buttons
        self._ui.saveSegmentsButton.connect('clicked(bool)', self.on_save_segments_button)
        self._ui.loadSegmentsButton.connect('clicked(bool)', self.on_load_segments_button)
        self._ui.fillSegmentsButton.connect('clicked(bool)', self.on_fill_segments_button)
        self._ui.loadLabelListButton.connect('clicked(bool)', self.on_load_label_list_button)

        self._ui.volumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self._ui.volumeSelector.selectNodeUponCreation = True
        self._ui.volumeSelector.addEnabled = False
        self._ui.volumeSelector.removeEnabled = True
        self._ui.volumeSelector.showHidden = False
        self._ui.volumeSelector.setMRMLScene(slicer.mrmlScene)
        self._ui.volumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.on_volume_node_changed)

        self.logic = SegmentEditorMultiLabel2DLogic()

        default_segment_editor_node = slicer.vtkMRMLSegmentEditorNode()
        default_segment_editor_node.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)
        slicer.mrmlScene.AddDefaultNode(default_segment_editor_node)

        SegmentEditorWidget.setup(self)
        self._editor_ui = slicer.util.childWidgetVariables(self.editor)

        # self._editor_ui.SegmentationNodeComboBox.enabled = False
        # self._editor_ui.MasterVolumeNodeComboBox.enabled = False
        self._setup_shortcuts()

    def cleanup(self):
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()
        SegmentEditorWidget.cleanup(self)

    def enter(self):
        SegmentEditorWidget.enter(self)

    @property
    def segment_labels(self) -> Optional[List[str]]:
        if self._segment_labels is not None:
            return self._segment_labels

        labels_file_path = self._config_dir() / 'labels.txt'
        try:
            with open(labels_file_path, 'r') as f:
                lines = [line.strip() for line in f.readlines()]
                for line in lines:
                    if len(line) > 100:
                        raise ValueError()
                self._segment_labels = list(sorted(lines))

            return self._segment_labels
        except ValueError:
            slicer.util.errorDisplay('Invalid label list. Cannot initialize segmentation list.')
            return None
        except FileNotFoundError:
            slicer.util.errorDisplay('Cannot fint label list file.')
            return None

    def on_load_label_list_button(self):
        file_path = qt.QFileDialog().getOpenFileName()
        if file_path == '':
            return

        shutil.copy(file_path, self._config_dir() / 'labels.txt')

        slicer.util.infoDisplay('Label list copied to internal storage.')
        self._segment_labels = None

    def on_save_segments_button(self):
        try:
            volume_node = self._get_current_volume()
        except VolumeNotSelected:
            return

        save_dir = qt.QFileDialog().getExistingDirectory()
        if save_dir == '':
            return

        segment_data = data_utils.get_segments_data_for_volume(volume_node)

        mask_file_name = Path(save_dir, f'{Path(volume_node.GetName()).stem}.seg')
        if mask_file_name.exists():
            if not slicer.util.confirmOkCancelDisplay(
                    windowTitle='File already exists.',
                    text=f'File {mask_file_name.name} found under selected directory {mask_file_name.parent}. '
                         f'Do you want to override it?',
            ):
                return

        data_utils.write_segments_to_h5(mask_file_name.as_posix(), segment_data)

    def on_load_segments_button(self):
        try:
            volume_node = self._get_current_volume()
        except VolumeNotSelected:
            return

        file_path = qt.QFileDialog().getOpenFileName()
        if file_path == '':
            return

        seg_node: mp.vtkMRMLSegmentationNode = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode',
                                                                             by_name=volume_node.GetName())

        if seg_node is not None:
            if not slicer.util.confirmOkCancelDisplay(
                    windowTitle='Segmentations exist.',
                    text=f'Existing segmentations will be removed. Continue?',
            ):
                return

        labels = self.segment_labels
        if labels is None:
            return
        seg_node = data_utils.load_segments_from_h5(volume_node, file_path, labels)
        self._editor_ui.SegmentationNodeComboBox.setCurrentNode(seg_node)

    def on_load_segments_all_button(self):
        load_dir = qt.QFileDialog().getExistingDirectory()
        if load_dir == '':
            return

        for name, volume_node in node_utils.get_nodes_by_class('vtkMRMLScalarVolumeNode').items():
            segment_file_path = Path(load_dir, f'{Path(name).stem}.seg')
            if not segment_file_path.exists():
                continue
            seg_node = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode', by_name=name)
            if seg_node is not None:
                if not slicer.util.confirmOkCancelDisplay(
                        windowTitle='Discard changes.',
                        text=f'Do you want to override segmentations of {name} volume?.',
                ):
                    continue
            labels = self.segment_labels
            if labels is None:
                return
            data_utils.load_segments_from_h5(volume_node, segment_file_path.as_posix(), labels)

    def on_fill_segments_button(self):
        try:
            volume_node = self._get_current_volume()
        except VolumeNotSelected:
            return

        labels = self.segment_labels
        if labels is None:
            return

        seg_node = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode', volume_node.GetName())

        if seg_node is None:
            seg_node = node_utils.create_segment_node_for_volume(volume_node)

        self._editor_ui.SegmentationNodeComboBox.setCurrentNode(seg_node)

        node_utils.create_empty_segments(seg_node, labels)

    def on_volume_node_changed(self, volume_node: mp.vtkMRMLScalarVolumeNode):
        if volume_node is None:
            logger.error(f'No scalar volume selected.')
            return
        logger.info(f'Selected scalar volume: {volume_node.GetName()}.')

        slicer.util.setSliceViewerLayers(background=volume_node)

        seg_nodes: Dict[str, mp.vtkMRMLSegmentationNode] = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode')
        seg_node_visible: mp.vtkMRMLSegmentationNode = seg_nodes.pop(volume_node.GetName(), None)

        if seg_node_visible is None:
            self._editor_ui.SegmentationNodeComboBox.setCurrentNode(None)
            for _, seg_node in seg_nodes.items():
                seg_node.SetDisplayVisibility(False)
            return

        seg_node_visible.SetDisplayVisibility(True)
        for _, seg_node in seg_nodes.items():
            seg_node.SetDisplayVisibility(False)

        self._editor_ui.SegmentationNodeComboBox.setCurrentNode(seg_node_visible)

    def change_volume(self, direction: str):
        nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')

        if len(nodes) == 0:
            return

        volume_node_id = self._ui.volumeSelector.currentNodeID
        if volume_node_id == '':
            self._ui.volumeSelector.setCurrentNode(nodes[0])
            return

        current_idx = nodes.index(slicer.util.getNode(volume_node_id))

        if direction == 'prev':
            current_idx -= 1
        elif direction == 'next':
            current_idx += 1
        else:
            raise ValueError()

        if current_idx == -1:
            current_idx += len(nodes)
        if current_idx == len(nodes):
            current_idx = 0

        self._ui.volumeSelector.setCurrentNode(nodes[current_idx])

    def _get_current_volume(self) -> mp.vtkMRMLScalarVolumeNode:
        volume_node_id = self._ui.volumeSelector.currentNodeID

        if volume_node_id == '':
            slicer.util.infoDisplay(f'Please select volume.')
            raise VolumeNotSelected()

        return slicer.util.getNode(volume_node_id)

    def _config_dir(self) -> Path:
        return Path(slicer.app.slicerUserSettingsFilePath).parent

    def _setup_shortcuts(self):
        shortcuts = [
            ['Ctrl+,', lambda: self.change_volume('prev')],
            ['Ctrl+.', lambda: self.change_volume('next')]
        ]

        for key, callback in shortcuts:
            shortcut = qt.QShortcut(slicer.util.mainWindow())
            shortcut.setKey(qt.QKeySequence(key))
            shortcut.connect("activated()", callback)


#
# SegmentEditorMultiLabel2DLogic
#

class SegmentEditorMultiLabel2DLogic(ScriptedLoadableModuleLogic):
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


# SegmentEditorMultiLabel2DTest
#

class SegmentEditorMultiLabel2DTest(ScriptedLoadableModuleTest):
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
        self.test_SegmentEditorMultiLabel2D1()

    def test_SegmentEditorMultiLabel2D1(self):
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
