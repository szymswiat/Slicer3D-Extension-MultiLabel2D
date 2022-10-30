cmake_minimum_required(VERSION 3.13.4)

project(MultiLabel2D)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/MultiLabel2D")
set(EXTENSION_CATEGORY "MultiLabel2D")
set(EXTENSION_CONTRIBUTORS "Szymon Swiatczynski")
set(EXTENSION_DESCRIPTION "MultiLabel2D")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/MultiLabel2D.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/MultiLabel2D/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SegmentEditorMultiLabel2D)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
