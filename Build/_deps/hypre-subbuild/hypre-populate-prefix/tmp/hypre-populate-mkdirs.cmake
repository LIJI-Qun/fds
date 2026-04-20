# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file LICENSE.rst or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION ${CMAKE_VERSION}) # this file comes with cmake

# If CMAKE_DISABLE_SOURCE_CHANGES is set to true and the source directory is an
# existing directory in our source tree, calling file(MAKE_DIRECTORY) on it
# would cause a fatal error, even though it would be a no-op.
if(NOT EXISTS "E:/CODE/FDS/fds/Build/_deps/hypre-src")
  file(MAKE_DIRECTORY "E:/CODE/FDS/fds/Build/_deps/hypre-src")
endif()
file(MAKE_DIRECTORY
  "E:/CODE/FDS/fds/Build/_deps/hypre-build"
  "E:/CODE/FDS/fds/Build/_deps/hypre-subbuild/hypre-populate-prefix"
  "E:/CODE/FDS/fds/Build/_deps/hypre-subbuild/hypre-populate-prefix/tmp"
  "E:/CODE/FDS/fds/Build/_deps/hypre-subbuild/hypre-populate-prefix/src/hypre-populate-stamp"
  "E:/CODE/FDS/fds/Build/_deps/hypre-subbuild/hypre-populate-prefix/src"
  "E:/CODE/FDS/fds/Build/_deps/hypre-subbuild/hypre-populate-prefix/src/hypre-populate-stamp"
)

set(configSubDirs Debug)
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "E:/CODE/FDS/fds/Build/_deps/hypre-subbuild/hypre-populate-prefix/src/hypre-populate-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "E:/CODE/FDS/fds/Build/_deps/hypre-subbuild/hypre-populate-prefix/src/hypre-populate-stamp${cfgdir}") # cfgdir has leading slash
endif()
