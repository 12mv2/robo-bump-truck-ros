#pragma once

#include <functional>

#include "control_interfaces/msg/control_msg.hpp"
#include "rclcpp/rclcpp.hpp"

// Repository-authored declarations for the supplied, unchanged implementation.
class ControlListenerNode : public rclcpp::Node
{
public:
  ControlListenerNode();

private:
  void topic_callback(const control_interfaces::msg::ControlMsg::SharedPtr msg);
  rclcpp::Subscription<control_interfaces::msg::ControlMsg>::SharedPtr subscription_;
};
