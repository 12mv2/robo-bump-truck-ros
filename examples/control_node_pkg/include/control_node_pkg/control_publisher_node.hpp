#pragma once

#include "control_interfaces/msg/control_msg.hpp"
#include "rclcpp/rclcpp.hpp"

// Repository-authored declarations for the supplied, unchanged implementation.
class ControlPublisherNode : public rclcpp::Node
{
public:
  ControlPublisherNode();
  void publish_message();

private:
  rclcpp::Publisher<control_interfaces::msg::ControlMsg>::SharedPtr publisher_;
};
