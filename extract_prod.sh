#!/bin/bash

mkdir ./tmp
mkdir ./tmp/MultiLabel2D

cp -r ./MultiLabel2D/SegmentEditorMultiLabel2D ./tmp/MultiLabel2D

(cd ./tmp; zip -rq MultiLabel2D.zip ./MultiLabel2D)

rm -rf ./tmp/MultiLabel2D
