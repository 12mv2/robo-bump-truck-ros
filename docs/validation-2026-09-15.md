# Interface validation — 2026-09-15

Validated on a local arm64 Linux VM using the official `ros:humble-ros-base` and
`ros:jazzy-ros-base` container images. These tests had no vehicle connection.

| Check | Humble / Ubuntu 22.04 | Jazzy / Ubuntu 24.04 |
|---|---|---|
| Build `control_interfaces`, `control_listener_pkg`, `control_node_pkg` | Passed | Passed |
| Start both C++ examples and receive repeated messages | Passed | Passed |
| Check all four message fields and values | Passed | Passed |
| Confirm the C++ listener received the example message | Passed | Passed |

`python3 tools/check_interface.py --staged-source .staging-model-side` also passed:
all five supplied files match their delivered bytes, and the message definition
matches the documentation. The private staging directory is not published.

The ROS integration test uses an isolated namespace. The examples emit fixed demo
values, including 2.5 m/s; this test does not validate driving, model inference,
camera calibration, command arbitration, source-image age or physical stopping.

The first Humble test run exposed a test-harness context/executor mismatch. It was
corrected to use an explicit executor for its context; the final Humble and Jazzy
runs passed. No supplied message or example implementation was changed.

GitHub Actions repeats the package, integrity and message-delivery checks for the
published revision. Check Actions for that separate hosted result.
