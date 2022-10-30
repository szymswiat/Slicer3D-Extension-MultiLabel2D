#!/bin/bash

mkdir ./tmp
mkdir ./tmp/CxrAISlicer

cp -r ./CxrAISlicer/SegmentEditorMultiLabel2D ./tmp/CxrAISlicer

(cd ./tmp; zip -rq CxrAISlicer.zip ./CxrAISlicer)

rm -rf ./tmp/CxrAISlicer
