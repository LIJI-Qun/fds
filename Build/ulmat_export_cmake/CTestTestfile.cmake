# CMake generated Testfile for 
# Source directory: F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds
# Build directory: F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/Build/ulmat_export_cmake
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
if(CTEST_CONFIGURATION_TYPE MATCHES "^([Dd][Ee][Bb][Uu][Gg])$")
  add_test([=[FDS Executes]=] "F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/Build/ulmat_export_cmake/Debug/fds.exe")
  set_tests_properties([=[FDS Executes]=] PROPERTIES  _BACKTRACE_TRIPLES "F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/CMakeLists.txt;232;add_test;F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/CMakeLists.txt;0;")
elseif(CTEST_CONFIGURATION_TYPE MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
  add_test([=[FDS Executes]=] "F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/Build/ulmat_export_cmake/Release/fds.exe")
  set_tests_properties([=[FDS Executes]=] PROPERTIES  _BACKTRACE_TRIPLES "F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/CMakeLists.txt;232;add_test;F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/CMakeLists.txt;0;")
elseif(CTEST_CONFIGURATION_TYPE MATCHES "^([Mm][Ii][Nn][Ss][Ii][Zz][Ee][Rr][Ee][Ll])$")
  add_test([=[FDS Executes]=] "F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/Build/ulmat_export_cmake/MinSizeRel/fds.exe")
  set_tests_properties([=[FDS Executes]=] PROPERTIES  _BACKTRACE_TRIPLES "F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/CMakeLists.txt;232;add_test;F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/CMakeLists.txt;0;")
elseif(CTEST_CONFIGURATION_TYPE MATCHES "^([Rr][Ee][Ll][Ww][Ii][Tt][Hh][Dd][Ee][Bb][Ii][Nn][Ff][Oo])$")
  add_test([=[FDS Executes]=] "F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/Build/ulmat_export_cmake/RelWithDebInfo/fds.exe")
  set_tests_properties([=[FDS Executes]=] PROPERTIES  _BACKTRACE_TRIPLES "F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/CMakeLists.txt;232;add_test;F:/2CcodExap/AaaaaIi/4FireFDS/fireGIT/fds/CMakeLists.txt;0;")
else()
  add_test([=[FDS Executes]=] NOT_AVAILABLE)
endif()
