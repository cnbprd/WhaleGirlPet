# Install script for directory: F:/WhaleGirlPet/3d/third_party/ozz-animation-master/src/base

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
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY FILES "F:/WhaleGirlPet/3d/third_party/ozz-build/src/base/libozz_base_r.a")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ozz/base" TYPE FILE FILES
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/export.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/endianness.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/gtest_helper.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/platform.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/span.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/log.h"
    )
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ozz/base/containers" TYPE FILE FILES
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/intrusive_list.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/deque.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/list.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/map.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/queue.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/set.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/stack.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/string.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/string_archive.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/unordered_map.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/unordered_set.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/vector.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/vector_archive.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/containers/std_allocator.h"
    )
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ozz/base/encode" TYPE FILE FILES "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/encode/group_varint.h")
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ozz/base/io" TYPE FILE FILES
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/io/archive.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/io/archive_traits.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/io/stream.h"
    )
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ozz/base/maths" TYPE FILE FILES
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/box.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/gtest_math_helper.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/math_ex.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/math_constant.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/quaternion.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/rect.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/simd_math.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/simd_quaternion.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/soa_float.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/soa_quaternion.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/soa_transform.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/soa_float4x4.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/transform.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/vec_float.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/math_archive.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/soa_math_archive.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/simd_math_archive.h"
    )
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ozz/base/maths/internal" TYPE FILE FILES
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/internal/simd_math_config.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/internal/simd_math_ref-inl.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/maths/internal/simd_math_sse-inl.h"
    )
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/ozz/base/memory" TYPE FILE FILES
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/memory/allocator.h"
    "F:/WhaleGirlPet/3d/third_party/ozz-animation-master/include/ozz/base/memory/unique_ptr.h"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("F:/WhaleGirlPet/3d/third_party/ozz-build/src/base/CMakeFiles/ozz_base.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "F:/WhaleGirlPet/3d/third_party/ozz-build/src/base/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
