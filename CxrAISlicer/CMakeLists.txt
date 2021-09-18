cmake_minimum_required(VERSION 3.13.4)

project(CxrAISlicer)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/CxrAISlicer")
set(EXTENSION_CATEGORY "CxrAISlicer")
set(EXTENSION_CONTRIBUTORS "Szymon Swiatczynski (CxrAI)")
set(EXTENSION_DESCRIPTION "CxrAISlicer")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/CxrAISlicer.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/CxrAISlicer/Screenshots/1.png")
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
