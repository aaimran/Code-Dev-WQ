# CMake generated Testfile for 
# Source directory: /scratch/aimran/Code-Dev-WQ/Gemini/WQ/src
# Build directory: /scratch/aimran/Code-Dev-WQ/Gemini/WQ/build
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(mpi_test1 "/opt/ohpc/pub/utils/cmake/3.24.2/bin/cmake" "-D" "in=test_rup_cart_fric.in" "-D" "prefix=test_rup_cart_fric" "-D" "t=1" "-D" "n=4" "-P" "/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/../cmake/run_mpi_test.cmake")
set_tests_properties(mpi_test1 PROPERTIES  _BACKTRACE_TRIPLES "/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/CMakeLists.txt;118;add_test;/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/CMakeLists.txt;0;")
add_test(mpi_test2 "/opt/ohpc/pub/utils/cmake/3.24.2/bin/cmake" "-D" "in=test_rup_curv_fric.in" "-D" "prefix=test_rup_curv_fric" "-D" "t=2" "-D" "n=4" "-P" "/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/../cmake/run_mpi_test.cmake")
set_tests_properties(mpi_test2 PROPERTIES  _BACKTRACE_TRIPLES "/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/CMakeLists.txt;126;add_test;/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/CMakeLists.txt;0;")
add_test(premesh_test1 "/opt/ohpc/pub/utils/cmake/3.24.2/bin/cmake" "-D" "in=test_rup_cart_fric_premesh.in" "-D" "prefix=test_rup_cart_fric" "-D" "t=1" "-D" "n=4" "-P" "/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/../cmake/run_test.cmake")
set_tests_properties(premesh_test1 PROPERTIES  _BACKTRACE_TRIPLES "/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/CMakeLists.txt;134;add_test;/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/CMakeLists.txt;0;")
add_test(premesh_test2 "/opt/ohpc/pub/utils/cmake/3.24.2/bin/cmake" "-D" "in=test_rup_curv_fric_premesh.in" "-D" "prefix=test_rup_curv_fric" "-D" "t=2" "-D" "n=4" "-P" "/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/../cmake/run_test.cmake")
set_tests_properties(premesh_test2 PROPERTIES  _BACKTRACE_TRIPLES "/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/CMakeLists.txt;142;add_test;/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/CMakeLists.txt;0;")
add_test(serial_test1 "/opt/ohpc/pub/utils/cmake/3.24.2/bin/cmake" "-D" "in=test_rup_cart_fric.in" "-D" "prefix=test_rup_cart_fric" "-D" "t=1" "-D" "n=1" "-P" "/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/../cmake/run_mpi_test.cmake")
set_tests_properties(serial_test1 PROPERTIES  _BACKTRACE_TRIPLES "/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/CMakeLists.txt;150;add_test;/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/CMakeLists.txt;0;")
add_test(serial_test2 "/opt/ohpc/pub/utils/cmake/3.24.2/bin/cmake" "-D" "in=test_rup_curv_fric.in" "-D" "prefix=test_rup_curv_fric" "-D" "t=2" "-D" "n=1" "-P" "/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/../cmake/run_mpi_test.cmake")
set_tests_properties(serial_test2 PROPERTIES  _BACKTRACE_TRIPLES "/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/CMakeLists.txt;158;add_test;/scratch/aimran/Code-Dev-WQ/Gemini/WQ/src/CMakeLists.txt;0;")
