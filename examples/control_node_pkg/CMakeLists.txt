cmake_minimum_required(VERSION 3.8)
project(control_node_pkg)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(control_interfaces REQUIRED)

add_executable(control_publisher_node src/main.cpp src/control_publisher_node.cpp)
target_compile_features(control_publisher_node PUBLIC cxx_std_17)
target_include_directories(control_publisher_node PRIVATE include)
ament_target_dependencies(control_publisher_node rclcpp control_interfaces)
install(TARGETS control_publisher_node DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(example_delivery test/test_example_delivery.py TIMEOUT 35)
endif()

ament_package()
