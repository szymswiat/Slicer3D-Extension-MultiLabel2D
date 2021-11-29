#!/bin/bash

mkdir ./tmp
mkdir ./tmp/CxrAISlicer

cp -r ./CxrAISlicer/SegmentEditorMultiLabel2D ./tmp/CxrAISlicer

rm ./tmp/CxrAISlicer/SegmentEditorMultiLabel2D/mimage_utils

mv ./tmp/CxrAISlicer/SegmentEditorMultiLabel2D/submodules/mimage_utils/mimage_utils \
   ./tmp/CxrAISlicer/SegmentEditorMultiLabel2D/mimage_utils

rm -rf ./tmp/CxrAISlicer/SegmentEditorMultiLabel2D/submodules

(cd ./tmp; zip -rq CxrAISlicer.zip ./CxrAISlicer)

rm -rf ./tmp/CxrAISlicer
