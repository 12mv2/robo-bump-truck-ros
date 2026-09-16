# truck_bridge: command policy and outputs-disabled diagnostics

This package subscribes to `control_cmd` (`control_interfaces/msg/ControlMsg`),
converts requests into the truck's steering convention, and publishes JSON on
`bridge_status` (`std_msgs/msg/String`). It has **no actuator output path**,
vehicle connection, or setting to enable physical output. It does not start or
stop phone recording. The supplied message definition is unchanged.

The executable checks the command boundary with synthetic or model messages.
It does not establish that a model can safely drive the truck.

## Build and run

From the repository root in a sourced ROS 2 Humble or Jazzy environment:

```bash
rosdep install --from-paths control_interfaces truck_bridge --ignore-src -r -y
colcon build --base-paths control_interfaces truck_bridge
source install/setup.bash
ros2 run truck_bridge shadow --ros-args -r __ns:=/bridge_demo
```

In another sourced terminal, send a fake request on the isolated demonstration
namespace:

```bash
ros2 topic pub --rate 10 /bridge_demo/control_cmd control_interfaces/msg/ControlMsg \
  '{desired_curvature: 0.5, desired_speed: 0.3, listen_to_steering: true, listen_to_speed: true}'
```

Inspect `ros2 topic echo /bridge_demo/bridge_status` in a third sourced terminal.
A positive wire curvature produces negative normalized truck steering: with the
defaults, `0.5` becomes `-0.35`. Stopping the publisher removes the request.
Keeping the publisher alive but stopping messages exercises receipt expiry.

The repository's original C++ example requests **2.5 m/s**, which deliberately
exceeds this package's default smoke-test limit and will be rejected.

## Policy

Wire curvature is in **1/m, positive left**. Truck steering is normalized,
**positive right**. The conversion is exactly
`steer = -desired_curvature / full_lock_curvature`. Values beyond the configured
input bound are rejected, not silently rescaled. There is no additional
perception gain, EMA, goal projection, or bicycle-model angle calculation.

| Steering validity | Speed validity/request | Result |
|---|---|---|
| True | True, positive | Normalized steering and bounded speed request |
| True | True, zero | Explicit `zero_speed` stop; valid steering retained as a separate fact |
| False | True, zero | Stop, no model steering, explicit manual steering handback |
| False | True, positive | Forward request refused; speed zero and manual steering handback |
| True | False | Keep valid steering; no speed request; `no_speed_authority` decision reason |
| False | False | No autonomous requests; manual steering handback |

Each flagged-off numeric field is ignored, including a retained non-finite
reference value. A flagged-on non-finite or out-of-range value rejects the whole
command and clears both requests. Negative speed is rejected; the producer gets
no reverse authority. Startup, receipt timeout, and invalid/regressing local
clocks also clear requests. Zero speed is a stop request, not measured rest.

These startup parameters are **proposed smoke-test limits**, not a vehicle-tested
deployment profile. Restart the node to change them.

| Parameter | Default | Constraint |
|---|---|---|
| `full_lock_curvature` | `1/0.70` 1/m | Finite, positive empirical plant scale |
| `max_curvature` | `1/0.70` 1/m | Finite, positive, no greater than full-lock scale |
| `max_speed` | `0.5` m/s | Finite and positive; zero requests still allowed |
| `timeout` | `0.5` s | Finite, positive receipt deadline |

## Receipt time and producer identity

The subscriber is reliable, volatile, keep-last depth 1. Diagnostics publish at
20 Hz. `received_at` is local monotonic receipt time; polling never renews it.
The node reports publisher endpoint GID, generation and publisher count from
ROS graph snapshots. Multiple
publishers clear requests. Publisher disappearance clears requests when seen
in the ROS graph. A changed publisher GID, or reappearance after an observed loss,
discards its first sample and increments the generation; a subsequent sample can
again be evaluated for diagnostics.
This does not rearm a controller or grant output authority.

Humble's Python callback provides only the message, and the supported Jazzy
message-info mapping does not provide a publisher GID. Therefore a graph snapshot
cannot prove that an individual queued message came from the currently visible
endpoint, or reveal a restart that occurred between observations. Status labels
this `publisher_identity_basis="ros_graph_snapshot"` and
`command_publisher_verified=false`; it is diagnostic identity tracking, not a
command-authentication or acquisition-timing guarantee.

**Receipt age is not source-image age.** `ControlMsg` has no source timestamp or
sequence, so even a newly received command may describe an old queued image.
Every status has `freshness="receipt_only"`, `source_age_verified=false` and
`output_enabled=false`. `state="command_ready"` means only that the command
passes this local policy. It is not permission to drive.

Status also contains the decision fields below, `command_age_s`,
`messages_received`, and the configured `limits`. On expiry the original receipt
timestamp remains visible while steer and speed become null. An absent command
or publisher transition can have a null receipt timestamp.

## Pure integration API

```python
from truck_bridge.policy import BridgePolicy, Decision

policy = BridgePolicy()
decision = policy.accept(message, received_at=monotonic_receipt)
decision = policy.snapshot(now=monotonic_now)
```

`Decision` is frozen and contains `received_at`, `steer`, `speed_mps`,
`stop_reason`, `manual_steering`, and `source_age_verified` (always false here).
`clear(reason, received_at=None)` explicitly withdraws requests.

An optional `BridgeNode(decision_sink=callable)` hook supports controlled,
outputs-disabled simulation with an existing controller. It invokes
`callable(decision, monotonic_now)` immediately for every accepted or cleared
decision, and on each timer snapshot. The hook does not collapse intermediate
stop events, and sink exceptions propagate. The integrating factory must refuse
an owner configured to send physical outputs. The command-line executable uses
no sink and has no actuator path.

An integrating controller must consume each received decision and latch stop
requests; a later command must not erase a stop before the output owner observes
it. Policy recovery after a fresh message is diagnostic recovery, not permission
to restart. Do not put receipt time into a frame-start field and claim that
inference or upstream queues have been included in source-age checks.

The existing truck output owner must remain the only actuator writer. Its
integration needs explicit manual steering handback: a zero model steering
value blended at full model weight centers the wheels instead. A zero speed
request must bypass forward feed-forward/PI throttle and request a stop. Human
radio, mode, brake, startup/rearm, expiry and speed limits remain authoritative.
ROS lane loss must not silently acquire the existing reverse-recovery behavior.

## Tests and remaining acceptance

```bash
colcon test --packages-select truck_bridge --event-handlers console_direct+
colcon test-result --verbose
```

Without ROS, run the pure policy tests from the repository root:

```bash
PYTHONPATH=truck_bridge python3 -m pytest -q truck_bridge/test
```

The ROS test is explicitly skipped outside a ROS environment. In ROS it sends
real messages through a fake publisher, checks diagnostic delivery, signs,
validity/zero-speed handling, expiry, competing publishers and producer
replacement. No actuator or private model code is imported.

In the private truck research checkout, `make_shadow_ros_node` connects this hook
to the existing output owner with sends prohibited. Real DDS-to-owner tests passed
on Humble and Jazzy, including steering signs, independent flags, zero speed,
no-lane handback, timeout, producer replacement and manual controls. This controller
integration is not shipped inside the public package. Missing speed authority
withdraws autonomous throttle while preserving independently valid steering; its
decision reason is not necessarily a terminal owner request.

Remaining acceptance: associate each command with source-image timing, run the
integrated path on the intended host with the delivered model and physical output
disabled, verify all human vetoes, replay model output, then perform controlled
bench and field checks. Physical steering direction, stopping distance, speed
calibration, producer rate and source-age limits are not established by these tests.
