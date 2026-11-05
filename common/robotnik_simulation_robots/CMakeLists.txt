cmake_minimum_required(VERSION 3.8)
project(robotnik_simulation_robots)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})

install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/ DESTINATION share/${PROJECT_NAME}
  PATTERN "CMakeLists.txt" EXCLUDE
  PATTERN "package.xml" EXCLUDE
  PATTERN "README.md" EXCLUDE
  REGEX "/robotnik_simulation_robots/robotnik_simulation_robots(/|$)" EXCLUDE
  PATTERN "test" EXCLUDE
  PATTERN "__pycache__" EXCLUDE)

ament_package()
