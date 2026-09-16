#include "control_node_pkg/control_publisher_node.hpp"

ControlPublisherNode::ControlPublisherNode()
: Node("control_publisher_node")
{
  publisher_ = this->create_publisher<control_interfaces::msg::ControlMsg>(
    "control_cmd", 10);
}

void ControlPublisherNode::publish_message()
{
  auto message = control_interfaces::msg::ControlMsg();
  message.desired_curvature = 0.1;
  message.desired_speed = 2.5;
  message.listen_to_steering = true;
  message.listen_to_speed = true;

  RCLCPP_INFO(this->get_logger(),
    "Publishing: curvature=%.2f speed=%.2f listen_steering=%d listen_speed=%d",
    message.desired_curvature, message.desired_speed,
    message.listen_to_steering, message.listen_to_speed);

  publisher_->publish(message);
}
