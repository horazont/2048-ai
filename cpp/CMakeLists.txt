cmake_minimum_required(VERSION 2.6)
set(CMAKE_CXX_FLAGS "-g -Wall -Wextra -Werror -std=c++11 -Wno-mismatched-tags -Wno-unused-parameter -Wno-literal-suffix")

set(_2048_SOURCES
  "2049.cpp"
)


add_executable(2049 ${_2048_SOURCES})
