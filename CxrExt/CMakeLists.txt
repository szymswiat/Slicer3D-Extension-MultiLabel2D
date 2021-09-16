cmake_minimum_required(VERSION 3.13.4)

project(CxrExt)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/CxrExt")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Szymswiat (-)")
set(EXTENSION_DESCRIPTION "-")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/CxrExt.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/CxrExt/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SlicerTest)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
