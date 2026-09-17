"""Real ROS command delivery and diagnostics; no actuator interface is imported."""

import json
import time
import uuid

import pytest

rclpy = pytest.importorskip('rclpy')
from control_interfaces.msg import ControlMsg
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String

from truck_bridge.node import BridgeNode


def test_real_ros_commands_expiry_and_publisher_replacement():
    context = Context()
    rclpy.init(context=context)
    namespace = '/bridge_test_' + uuid.uuid4().hex
    decisions = []
    bridge = BridgeNode(context=context, namespace=namespace,
                        decision_sink=lambda decision, now: decisions.append((decision, now)),
                        cli_args=['--ros-args', '-r', 'control_cmd:=control_input'],
                        parameter_overrides=[Parameter('timeout', value=0.3)])
    observer = Node('observer', namespace=namespace, context=context)
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(bridge)
    executor.add_node(observer)
    statuses = []
    observer.create_subscription(String, 'bridge_status',
                                 lambda msg: statuses.append(json.loads(msg.data)), 1)
    publisher = observer.create_publisher(ControlMsg, 'control_input', 1)

    def spin_until(condition, timeout=5):
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=0.01)
        assert condition(), statuses[-3:]

    def next_status_after(publish, predicate):
        start = len(statuses)
        publish()
        spin_until(lambda: any(predicate(s) for s in statuses[start:]))
        return next(s for s in statuses[start:] if predicate(s))

    def message(curvature=0.5, speed=0.3, steer=True, throttle=True):
        msg = ControlMsg()
        msg.desired_curvature, msg.desired_speed = float(curvature), float(speed)
        msg.listen_to_steering, msg.listen_to_speed = steer, throttle
        return msg

    try:
        spin_until(lambda: publisher.get_subscription_count() == 1 and
                   bridge.status_publisher.get_subscription_count() == 1)
        ready = next_status_after(lambda: publisher.publish(message()),
                                  lambda s: s['stop_reason'] is None)
        assert ready['steer'] == pytest.approx(-0.35, abs=1e-6)
        assert ready['speed_mps'] == pytest.approx(0.3, abs=1e-6)
        assert ready['publisher_generation'] == 1

        stopped = next_status_after(lambda: publisher.publish(message(speed=0, steer=False)),
                                    lambda s: s['stop_reason'] == 'zero_speed')
        assert stopped['manual_steering'] and stopped['steer'] is None
        assert stopped['speed_mps'] == 0

        refused = next_status_after(lambda: publisher.publish(message(steer=False)),
                                    lambda s: s['stop_reason'] == 'no_steering_authority')
        assert refused['manual_steering'] and refused['speed_mps'] == 0
        steering_only = next_status_after(lambda: publisher.publish(message(throttle=False)),
                                          lambda s: s['stop_reason'] == 'no_speed_authority')
        assert steering_only['steer'] == pytest.approx(-0.35, abs=1e-6)
        assert steering_only['speed_mps'] is None

        ready = next_status_after(lambda: publisher.publish(message()),
                                  lambda s: s['stop_reason'] is None)
        spin_until(lambda: statuses[-1]['stop_reason'] == 'command_timeout')
        assert statuses[-1]['received_at'] == ready['received_at']
        assert statuses[-1]['steer'] is None and statuses[-1]['speed_mps'] is None

        # More than one producer cannot confer authority or alternate commands.
        rival = observer.create_publisher(ControlMsg, 'control_input', 1)
        spin_until(lambda: statuses[-1]['publisher_count'] == 2)
        assert statuses[-1]['stop_reason'] == 'multiple_publishers'
        observer.destroy_publisher(rival)
        observer.destroy_publisher(publisher)
        spin_until(lambda: statuses[-1]['stop_reason'] == 'publisher_lost')

        publisher = observer.create_publisher(ControlMsg, 'control_input', 1)
        spin_until(lambda: publisher.get_subscription_count() == 1 and
                   bridge.count_publishers('control_input') == 1)
        changed = next_status_after(lambda: publisher.publish(message()),
                                    lambda s: s['stop_reason'] == 'publisher_changed')
        assert changed['publisher_generation'] == 2 and changed['steer'] is None
        ready_again = next_status_after(lambda: publisher.publish(message()),
                                        lambda s: s['stop_reason'] is None)
        assert ready_again['publisher_generation'] == 2

        # Two callbacks before the timer must both reach the simulated owner.
        # A normal request must not hide an intervening no-lane stop event.
        start = len(decisions)
        bridge.on_command(message(speed=0, steer=False))
        bridge.on_command(message())
        delivered = decisions[start:]
        assert len(delivered) == 2
        assert delivered[0][0].stop_reason == 'zero_speed'
        assert delivered[0][0].manual_steering
        assert delivered[1][0].stop_reason is None
        assert all(decision.received_at == now for decision, now in delivered)

        assert statuses
        assert all(s['output_enabled'] is False and s['source_age_verified'] is False
                   and s['freshness'] == 'receipt_only'
                   and s['publisher_identity_basis'] == 'ros_graph_snapshot'
                   and s['command_publisher_verified'] is False for s in statuses)

        def broken_sink(decision, now):
            raise RuntimeError('simulated owner failed')
        bridge.decision_sink = broken_sink
        with pytest.raises(RuntimeError, match='simulated owner failed'):
            bridge.on_command(message(speed=0, steer=False))
    finally:
        executor.shutdown()
        observer.destroy_node()
        bridge.destroy_node()
        rclpy.shutdown(context=context)
