#include "control_listener_pkg/control_listener_node.hpp"

ControlListenerNode::ControlListenerNode()
: Node("control_listener_node")
{
  subscription_ = this->create_subscription<control_interfaces::msg::ControlMsg>(
    "control_cmd", 10,
    std::bind(&ControlListenerNode::topic_callback, this, std::placeholders::_1));
}

void ControlListenerNode::topic_callback(const control_interfaces::msg::ControlMsg::SharedPtr msg)
{
  RCLCPP_INFO(this->get_logger(),
    "Received: curvature=%.2f speed=%.2f listen_steering=%d listen_speed=%d",
    msg->desired_curvature, msg->desired_speed,
    msg->listen_to_steering, msg->listen_to_speed);
}
