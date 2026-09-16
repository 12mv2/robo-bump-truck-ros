"""Exercise both supplied C++ examples on a unique, non-actuating topic."""

import math
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

from ament_index_python.packages import get_package_prefix
from control_interfaces.msg import ControlMsg
import rclpy
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor


def test_examples_deliver_the_four_field_contract(tmp_path):
    namespace = "/interface_test_" + uuid.uuid4().hex
    processes = []
    log_files = []
    context = Context()
    rclpy.init(context=context)
    observer = rclpy.create_node("observer", namespace=namespace, context=context)
    executor = SingleThreadedExecutor(context=context)
    executor.add_node(observer)
    received = []
    subscription = observer.create_subscription(ControlMsg, "control_cmd", received.append, 10)
    listener_log = tmp_path / "listener.log"
    try:
        for package, executable, log_path in (
            ("control_listener_pkg", "control_listener_node", listener_log),
            ("control_node_pkg", "control_publisher_node", tmp_path / "publisher.log"),
        ):
            program = Path(get_package_prefix(package)) / "lib" / package / executable
            log_file = log_path.open("w")
            log_files.append(log_file)
            processes.append(subprocess.Popen(
                [str(program), "--ros-args", "-r", "__ns:=" + namespace],
                stdout=log_file, stderr=subprocess.STDOUT,
                env={**os.environ, "RCUTILS_COLORIZED_OUTPUT": "0"},
            ))

        expected_log = "Received: curvature=0.10 speed=2.50 listen_steering=1 listen_speed=1"
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            assert all(process.poll() is None for process in processes), "Example exited early"
            executor.spin_once(timeout_sec=0.1)
            if len(received) >= 2 and expected_log in listener_log.read_text():
                break
        assert len(received) >= 2, "Publisher did not repeatedly deliver ControlMsg"
        assert expected_log in listener_log.read_text(), "C++ listener did not receive expected values"
        assert list(ControlMsg.get_fields_and_field_types()) == [
            "desired_curvature", "desired_speed", "listen_to_steering", "listen_to_speed"
        ]
        for message in received:
            assert math.isclose(message.desired_curvature, 0.1, abs_tol=1e-6)
            assert math.isclose(message.desired_speed, 2.5, abs_tol=1e-6)
            assert message.listen_to_steering is True
            assert message.listen_to_speed is True
    finally:
        for process in processes:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
        for process in processes:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        for log_file in log_files:
            log_file.close()
        executor.shutdown()
        observer.destroy_subscription(subscription)
        observer.destroy_node()
        rclpy.shutdown(context=context)
