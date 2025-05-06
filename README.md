# MultiLabel2D - 3D Slicer Extension

A 3D Slicer extension for multi-label 2D segmentation.

## Description

MultiLabel2D is a 3D Slicer extension that provides tools for multi-label 2D segmentation. This extension enhances the segmentation capabilities of 3D Slicer by allowing users to work with multiple labels in 2D views. It includes functionality to save segmentation labels in a custom data format, providing flexibility in data storage and exchange.

## Features

- Multi-label 2D segmentation support
- Integration with 3D Slicer's Segment Editor
- User-friendly interface for label management
- Custom data format support for saving and loading labels

## Requirements

- 3D Slicer (latest version recommended)
- CMake 3.13.4 or higher

## Installation

1. Clone the repository
2. Extract the extension using the provided script:
```bash
./extract_prod.sh
```
3. Follow the 3D Slicer extension installation process:
   - Open 3D Slicer
   - Go to View → Extension Manager
   - Click on "Install Extension from File"
   - Select the extracted extension package
4. Restart 3D Slicer if it's running
5. The extension will be available in the Segment Editor module

## Usage

1. Open 3D Slicer
2. Load your image data
3. Go to the Segment Editor module
4. Use the MultiLabel2D tools for segmentation


## Author

- Szymon Swiatczynski
