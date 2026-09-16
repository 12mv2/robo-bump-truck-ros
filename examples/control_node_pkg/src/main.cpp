#include <chrono>
#include <memory>

#include "control_node_pkg/control_publisher_node.hpp"

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<ControlPublisherNode>();
  // The supplied example defines one publish operation; this wrapper schedules it.
  auto timer = node->create_wall_timer(
    std::chrono::milliseconds(100), [&node]() { node->publish_message(); });
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
