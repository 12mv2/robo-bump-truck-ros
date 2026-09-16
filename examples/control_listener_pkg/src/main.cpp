#include <memory>

#include "control_listener_pkg/control_listener_node.hpp"

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ControlListenerNode>());
  rclcpp::shutdown();
  return 0;
}
