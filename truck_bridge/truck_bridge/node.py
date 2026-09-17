"""Observe ROS commands and publish diagnostics; no physical output exists."""

from dataclasses import asdict
import json
import time

from control_interfaces.msg import ControlMsg
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from .policy import BridgePolicy


class BridgeNode(Node):
    def __init__(self, *, decision_sink=None, **kwargs):
        if decision_sink is not None and not callable(decision_sink):
            raise TypeError('decision_sink must be callable or None')
        super().__init__('truck_bridge_shadow', **kwargs)
        self.decision_sink = decision_sink
        defaults = dict(full_lock_curvature=1.0 / 0.70,
                        max_curvature=1.0 / 0.70, max_speed=0.5, timeout=0.5)
        self.limits = {name: self.declare_parameter(name, value).value
                       for name, value in defaults.items()}
        self.policy = BridgePolicy(**self.limits)
        self.publisher_gid = None
        self.publisher_generation = 0
        self.messages_received = 0
        self.publisher_count = 0
        self.publisher_present = False
        qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1,
                         reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.VOLATILE)
        self.command_subscription = self.create_subscription(
            ControlMsg, 'control_cmd', self.on_command, qos)
        self.status_publisher = self.create_publisher(String, 'bridge_status', qos)
        self.create_timer(0.05, self.publish_status)
        self.get_logger().info(
            'Outputs disabled; receipt-only freshness, no source-image age verification. '
            'Limits are proposed smoke-test settings, not vehicle acceptance.')

    def deliver(self, decision, now):
        """Expose every event to an outputs-disabled simulator, without batching."""
        if self.decision_sink is not None:
            self.decision_sink(decision, now)
        return decision

    def on_command(self, message):
        now = time.monotonic()
        self.messages_received += 1
        # Humble supplies message-only callbacks. Jazzy's message-info mapping
        # also lacks a publisher GID in the supported runtime. The graph gives
        # endpoint identity, not proof that this queued message came from it.
        endpoints = self.get_publishers_info_by_topic(self.command_subscription.topic_name)
        self.publisher_count = len(endpoints)
        if self.publisher_count != 1:
            self.deliver(self.policy.clear('publisher_count_not_one'), now)
            return
        gid_bytes = bytes(endpoints[0].endpoint_gid)
        gid = gid_bytes.hex() if any(gid_bytes) else None
        if gid is None:
            self.deliver(self.policy.clear('publisher_identity_unknown'), now)
            return
        if self.publisher_gid is not None and (gid != self.publisher_gid or not self.publisher_present):
            self.publisher_gid = gid
            self.publisher_generation += 1
            self.publisher_present = True
            # The first sample from a replacement/reappearance announces it.
            # A following fresh sample may be evaluated for diagnostics.
            self.deliver(self.policy.clear('publisher_changed'), now)
            return
        if self.publisher_gid is None:
            self.publisher_generation += 1
        self.publisher_gid = gid
        self.publisher_present = True
        self.deliver(self.policy.accept(message, now), now)

    def publish_status(self):
        now = time.monotonic()
        self.publisher_count = self.count_publishers(self.command_subscription.topic_name)
        if self.publisher_count > 1:
            self.deliver(self.policy.clear('multiple_publishers'), now)
        elif self.publisher_count == 0 and self.publisher_present:
            self.publisher_present = False
            self.deliver(self.policy.clear('publisher_lost'), now)
        decision = self.deliver(self.policy.snapshot(now), now)
        value = asdict(decision)
        value.update(
            state='command_ready' if decision.stop_reason is None else 'stopped',
            output_enabled=False,
            source_age_verified=False,
            freshness='receipt_only',
            command_age_s=(None if decision.received_at is None else
                           now - decision.received_at),
            publisher_gid=self.publisher_gid,
            publisher_generation=self.publisher_generation,
            publisher_count=self.publisher_count,
            publisher_identity_basis='ros_graph_snapshot',
            command_publisher_verified=False,
            messages_received=self.messages_received,
            limits=self.limits,
        )
        message = String()
        message.data = json.dumps(value, allow_nan=False)
        self.status_publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = BridgeNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
