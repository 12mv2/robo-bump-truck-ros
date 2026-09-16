cmake_minimum_required(VERSION 3.8)
project(control_listener_pkg)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(control_interfaces REQUIRED)

add_executable(control_listener_node src/main.cpp src/control_listener_node.cpp)
target_compile_features(control_listener_node PUBLIC cxx_std_17)
target_include_directories(control_listener_node PRIVATE include)
ament_target_dependencies(control_listener_node rclcpp control_interfaces)
install(TARGETS control_listener_node DESTINATION lib/${PROJECT_NAME})

ament_package()
