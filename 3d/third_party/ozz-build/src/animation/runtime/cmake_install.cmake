# Install script for directory: F:/WhaleGirlPet/3d/third_party/ozz-animation-master/src/animation/runtime

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "C:/Program Files (x86)/ozz")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set path to fallback-tool for dependency-resolution.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "F:/WhaleGirlPet/.toolchains/w64devkit/w64devkit/bin/objdump.exe")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY FILES "F:/WhaleGirlPet/3d/third_party/ozz-build/src/animation/runtime/libozz_animation_r.a")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ozz/animation/runtime" TYPE FILE FILES
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/export.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/animation.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/animation_utils.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/blending_job.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/ik_aim_job.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/ik_two_bone_job.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/local_to_model_job.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/motion_blending_job.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/sampling_job.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/skeleton.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/skeleton_utils.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/track.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/track_sampling_job.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/track_triggering_job.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/animation/runtime/track_triggering_job_trait.h"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("F:/WhaleGirlPet/3d/third_party/ozz-build/src/animation/runtime/CMakeFiles/ozz_animation.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "F:/WhaleGirlPet/3d/third_party/ozz-build/src/animation/runtime/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
