import slicer
import vtk

try:
    import zarr
except ModuleNotFoundError:
    slicer.util.pip_install('zarr')

import logging
import qt
import threading

from typing import List, Dict, Optional
from slicer.util import VTKObservationMixin
from slicer.ScriptedLoadableModule import *
from utils import node_utils, VolumeNotSelected, LabelManager
from zarr_io import SlicerSegmentZarrWriter, SlicerSegmentZarrReader
from MRMLCorePython import vtkMRMLSegmentationNode, vtkMRMLScalarVolumeNode, vtkMRMLScene
from pathlib import Path


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

class SegmentEditorMultiLabel2DWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)

        self.logic: SegmentEditorMultiLabel2DLogic = None

        self._self_ui = None
        self._vol_ui = None
        self._se_ui = None

        self._scene: vtkMRMLScene = None

        self._label_manager = LabelManager()
        self._periodic_label_downloader: threading.Timer = None

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        self._scene: vtkMRMLScene = slicer.mrmlScene

        self.setup_ui_defaults()

        ui_widget = slicer.util.loadUI(self.resourcePath('UI/SegmentEditorMultiLabel2D.ui'))
        volumes_ui_widget = slicer.modules.volumes.createNewWidgetRepresentation()
        segment_editor_ui_widget = slicer.modules.segmenteditor.createNewWidgetRepresentation()

        self.layout.addWidget(ui_widget)
        self.layout.addWidget(segment_editor_ui_widget)
        self.layout.addWidget(volumes_ui_widget)

        self._self_ui = slicer.util.childWidgetVariables(ui_widget)
        self._vol_ui = slicer.util.childWidgetVariables(volumes_ui_widget)
        self._se_ui = slicer.util.childWidgetVariables(segment_editor_ui_widget)

        ui_widget.setMRMLScene(self._scene)

        self.setup_self_ui()

        self.setup_shortcuts()

        self.logic = SegmentEditorMultiLabel2DLogic()

        volumes_ui_widget.setMaximumSize(5000, 500)
        volumes_ui_widget.setSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Minimum)
        segment_editor_ui_widget.setSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Minimum)

        # fetch labels with 3 minutes interval
        qt.QTimer.singleShot(1, lambda: self.fetch_labels(show_warning=True))
        self._periodic_label_downloader = qt.QTimer()
        self._periodic_label_downloader.timeout.connect(self.fetch_labels)
        self._periodic_label_downloader.setInterval(30000)
        self._periodic_label_downloader.start()

    def setup_self_ui(self):
        # Buttons
        self._self_ui.saveSegmentsButton.connect('clicked(bool)', self.on_save_segments_button)
        self._self_ui.loadSegmentsButton.connect('clicked(bool)', self.on_load_segments_button)
        self._self_ui.loadAllSegmentsButton.connect('clicked(bool)', self.on_load_all_segments_button)
        self._self_ui.fillSegmentsButton.connect('clicked(bool)', self.on_fill_segments_button)
        self._self_ui.syncLabelListButton.connect('clicked(bool)', self.on_sync_labels_button)

        self._self_ui.prevVolumeButton.connect('clicked(bool)', lambda: self.on_change_volume('prev'))
        self._self_ui.nextVolumeButton.connect('clicked(bool)', lambda: self.on_change_volume('next'))
        self._self_ui.closeVolumeButton.connect('clicked(bool)', self.on_close_current_volume)

        self._self_ui.volumeSelector.setMRMLScene(self._scene)
        self._self_ui.volumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.on_volume_node_changed)

    def setup_ui_defaults(self):
        default_segment_editor_node = slicer.vtkMRMLSegmentEditorNode()
        default_segment_editor_node.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)
        self._scene.AddDefaultNode(default_segment_editor_node)

    def get_labels(self) -> Optional[List[str]]:
        try:
            return self._label_manager.segment_labels
        except ValueError:
            slicer.util.errorDisplay('Invalid label list. Cannot initialize segmentation list.')
            return None
        except FileNotFoundError:
            slicer.util.errorDisplay('Cannot find label list file.')
            return None

    def fetch_labels(self, show_warning=False):
        fetched = self._label_manager.fetch_labels()

        if fetched:
            logging.info('Label list downloaded and saved.')
        else:
            msg = 'Unable to fetch label list. Please check your internet connection.'
            if show_warning:
                slicer.util.warningDisplay(msg)
            else:
                logging.warning(msg)

    def on_save_segments_button(self):
        try:
            volume_node = self.get_current_volume()
        except VolumeNotSelected:
            return

        save_dir = qt.QFileDialog().getExistingDirectory()
        if save_dir == '':
            return

        mask_file_name = Path(save_dir, f'{Path(volume_node.GetName()).stem}.seg')
        if mask_file_name.exists():
            if not slicer.util.confirmOkCancelDisplay(
                    windowTitle='File already exists.',
                    text=f'File {mask_file_name.name} found under selected directory {mask_file_name.parent}. '
                         f'Do you want to override it?',
            ):
                return

        # noinspection PyTypeChecker
        seg_node: vtkMRMLSegmentationNode = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode',
                                                                          volume_node.GetName())
        if seg_node is None:
            slicer.util.errorDisplay(f'There is no segmentation node for current volume node.')
            return

        with SlicerSegmentZarrWriter(mask_file_name) as writer:
            writer.write_segmentation_node(seg_node)

    def on_load_segments_button(self):
        try:
            volume_node = self.get_current_volume()
        except VolumeNotSelected:
            return

        file_path = qt.QFileDialog().getOpenFileName()
        if file_path == '':
            return

        self.load_segments_for_volume(volume_node, Path(file_path))

    def on_load_all_segments_button(self):
        load_dir = qt.QFileDialog().getExistingDirectory()
        if load_dir == '':
            return
        progress_dialog = slicer.util.createProgressDialog()
        progress_dialog.setLabelText("Loading segments ...")

        progress_dialog.show()
        progress_dialog.activateWindow()
        progress_dialog.setValue(0)
        slicer.app.processEvents()

        named_volumes = node_utils.get_nodes_by_class('vtkMRMLScalarVolumeNode').items()
        for i, (name, volume_node) in enumerate(named_volumes):
            segment_file_path = Path(load_dir, f'{Path(name).stem}.seg')
            if not segment_file_path.exists():
                continue

            # noinspection PyTypeChecker
            self.load_segments_for_volume(volume_node, segment_file_path)

            progress_dialog.setValue(int(i / len(named_volumes) * 100))
            slicer.app.processEvents()

        progress_dialog.close()

        try:
            self.on_volume_node_changed(self.get_current_volume())
        except VolumeNotSelected:
            pass

    def on_fill_segments_button(self):
        self.fill_segments_for_current_node()

    def on_sync_labels_button(self):
        def sync():
            fetched = self._label_manager.fetch_labels()

            if fetched:
                slicer.util.infoDisplay('Label list downloaded and saved.')
            else:
                slicer.util.warningDisplay('Unable to fetch label list. Please check your internet connection.')

        qt.QTimer.singleShot(1, sync)

    def fill_segments_for_current_node(self):
        try:
            volume_node = self.get_current_volume()
        except VolumeNotSelected:
            return

        labels = self.get_labels()
        if labels is None:
            return

        seg_node = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode', volume_node.GetName())

        if seg_node is None:
            seg_node = node_utils.create_segment_node_for_volume(volume_node)

        self._se_ui.SegmentationNodeComboBox.setCurrentNode(seg_node)

        node_utils.create_empty_segments(seg_node, labels)

    def on_volume_node_changed(self, volume_node: vtkMRMLScalarVolumeNode):
        if volume_node is None:
            logging.error(f'No scalar volume selected.')
            return
        # logging.info(f'Selected scalar volume: {volume_node.GetName()}.')
        self._vol_ui.ActiveVolumeNodeSelector.setCurrentNode(volume_node)
        self._self_ui.volumeSelector.setCurrentNode(volume_node)

        self.fill_segments_for_current_node()

        slicer.util.setSliceViewerLayers(background=volume_node)

        # noinspection PyTypeChecker
        seg_nodes: Dict[str, vtkMRMLSegmentationNode] = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode')
        seg_node_visible: vtkMRMLSegmentationNode = seg_nodes.pop(volume_node.GetName(), None)

        if seg_node_visible is None:
            self._se_ui.SegmentationNodeComboBox.setCurrentNode(None)
            for _, seg_node in seg_nodes.items():
                seg_node.SetDisplayVisibility(False)
            return

        seg_node_visible.SetDisplayVisibility(True)
        for _, seg_node in seg_nodes.items():
            seg_node.SetDisplayVisibility(False)

        self._se_ui.SegmentationNodeComboBox.setCurrentNode(seg_node_visible)

    def on_close_current_volume(self):
        try:
            volume_node = self.get_current_volume(display_info=False)
        except VolumeNotSelected:
            return

        seg_node = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode', volume_node.GetName())

        if seg_node is not None:
            if slicer.util.confirmOkCancelDisplay(
                    windowTitle=f'Removing volume {volume_node.GetName()}.',
                    text=f'Do you want to discard existing segments?',
            ):
                self._scene.RemoveNode(volume_node)
                self._scene.RemoveNode(seg_node)
        else:
            self._scene.RemoveNode(volume_node)

    def on_change_volume(self, direction: str):
        nodes = slicer.util.getNodesByClass('vtkMRMLScalarVolumeNode')

        if len(nodes) == 0:
            return

        volume_node_id = self._self_ui.volumeSelector.currentNodeID
        if volume_node_id == '':
            self.on_volume_node_changed(nodes[0])
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

        self.on_volume_node_changed(nodes[current_idx])

    def load_segments_for_volume(
            self,
            volume_node: vtkMRMLScalarVolumeNode,
            file_path: Path
    ):
        # noinspection PyTypeChecker
        seg_node: vtkMRMLSegmentationNode = node_utils.get_nodes_by_class('vtkMRMLSegmentationNode',
                                                                          by_name=volume_node.GetName())
        if seg_node is not None:
            if not slicer.util.confirmOkCancelDisplay(
                    windowTitle=f'Segmentation data exists for volume: {volume_node.GetName()}.',
                    text=f'Existing segmentation data will be removed. Continue?',
            ):
                return
            else:
                self._scene.RemoveNode(seg_node)

        seg_node = node_utils.create_segment_node_for_volume(volume_node)

        labels = self.get_labels()
        if labels is None:
            return

        with SlicerSegmentZarrReader(file_path) as reader:
            reader.read_to_segmentation_node(seg_node, labels)

        self._se_ui.SegmentationNodeComboBox.setCurrentNode(seg_node)

    def get_current_volume(self, display_info=True) -> vtkMRMLScalarVolumeNode:
        volume_node_id = self._self_ui.volumeSelector.currentNodeID

        if volume_node_id == '':
            if display_info:
                slicer.util.infoDisplay(f'Please select volume.')
            raise VolumeNotSelected()

        return slicer.util.getNode(volume_node_id)

    def setup_shortcuts(self):
        shortcuts = [
            ['Ctrl+Left', lambda: self.on_change_volume('prev')],
            ['Ctrl+Right', lambda: self.on_change_volume('next')]
        ]

        for key, callback in shortcuts:
            shortcut = qt.QShortcut(slicer.util.mainWindow())
            shortcut.setKey(qt.QKeySequence(key))
            shortcut.connect("activated()", callback)

        slice_view_widget = slicer.app.layoutManager().sliceWidget('Red')
        dm = slice_view_widget.sliceView().displayableManagerByClassName('vtkMRMLScalarBarDisplayableManager')
        w = dm.GetWindowLevelWidget()
        w.SetEventTranslationClickAndDrag(w.WidgetStateIdle, vtk.vtkCommand.MiddleButtonPressEvent,
                                          vtk.vtkEvent.AltModifier, w.WidgetStateAdjustWindowLevel,
                                          w.WidgetEventAlwaysOnAdjustWindowLevelStart,
                                          w.WidgetEventAlwaysOnAdjustWindowLevelEnd)


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
