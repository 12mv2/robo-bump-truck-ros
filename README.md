# robo-bump-truck-ros

**A ROS 2 control interface for the [Robo Bump Truck](https://vaguebutexciting.dev/posts/kitchen-robot-eyes-log1/).**
A perception model publishes a curvature and speed request using the message in this repository. The planned truck bridge
will pass that request into the truck's existing controller. The model stays in its own repository.

The truck is an RC Traxxas Stampede 2WD with a Jetson Orin Nano, a Pixhawk 6C Mini running ArduPilot Rover, and an iPhone
running [Robot Eyes](https://github.com/12mv2/robot-eyes) as its camera. The existing non-ROS controller has driven on trails.
That does not establish that this ROS interface has driven the truck.

## Status

The supplied message package and publisher/listener source files are included unchanged. Repository-authored headers,
executable entry points, a 10 Hz publisher timer, build files and an integration test make the examples runnable.
See [source provenance](docs/source-provenance.md) for the exact supplied files and their SHA-256 checksums.

All three packages built and the publisher/listener delivery test passed locally on **ROS 2 Humble and Jazzy** in arm64
Linux containers on September 15, 2026. See [validation details](docs/validation-2026-09-15.md). CI repeats those checks;
check Actions for the hosted result for the commit you use. This delivery has not been validated on the truck.
`truck_bridge/` is an implementation specification, not an executable package yet.

## The contract

The relative topic is **`control_cmd`** (normally `/control_cmd` without a namespace). The message is
**`control_interfaces/msg/ControlMsg`**, with these four fields in this order:

```text
float32 desired_curvature
float32 desired_speed
bool listen_to_steering
bool listen_to_speed
```

| Field | Meaning | Convention |
|---|---|---|
| `desired_curvature` | Requested path curvature, 1/m | **positive = LEFT** in a vehicle frame with X forward, Y left, Z up |
| `desired_speed` | Requested forward speed, m/s | Subject to the truck's speed limits and human controls |
| `listen_to_steering` | Whether the curvature is valid | When false, do not apply the retained curvature |
| `listen_to_speed` | Whether the speed request is valid | Evaluated independently from steering validity |

The model-side pure-pursuit expression is `κ = 2·Y/L²`, with the vehicle-frame origin on the ground under the rear axle.
See the [sign convention](docs/seam-sign-convention.md).

**There is no header, timestamp or frame ID.** A bridge must track receipt time and reject timed-out commands. Receipt time
alone cannot detect an old image waiting in an upstream queue. Source-image age and producer health need a separate,
compatible mechanism; this delivery does not silently add fields to the shared message.

The example publishes at 10 Hz. A model's actual cadence, deadline and queue limits must be agreed and measured for its
runtime; 10 Hz is not established merely by connecting to the topic.

### Validity and no-lane behavior

| Situation | `desired_curvature` | `desired_speed` | `listen_to_steering` | `listen_to_speed` |
|---|---|---|---|---|
| Valid lane and curvature | Computed curvature | Configured speed | `true` | `true` |
| No lane, after the producer's grace period | Last valid curvature, retained for reference | `0` | `false` | `true` |

For the no-lane message the required bridge response is a stop request and steering handback to the human. The retained
curvature must not continue steering the vehicle. Invalid curvature can also occur independently of lane loss, including
with a nonzero speed request; the bridge must evaluate both validity flags rather than treating the table as exhaustive.
Silence, non-finite values and timeout are separate fault cases with explicit tests. These bridge behaviors are requirements
until implemented and demonstrated.

## Build and test

Use an Ubuntu ROS 2 Humble or Jazzy environment with `rosdep` and `colcon` installed. From the repository root:

```bash
source /opt/ros/humble/setup.bash
# For Jazzy, source /opt/ros/jazzy/setup.bash instead.
rosdep update
rosdep install --from-paths control_interfaces examples --ignore-src -y --rosdistro "$ROS_DISTRO"
python3 tools/check_interface.py
colcon build --base-paths control_interfaces examples --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
ROS_LOCALHOST_ONLY=1 colcon test --base-paths control_interfaces examples --return-code-on-test-failure --event-handlers console_direct+
colcon test-result --verbose
```

`tools/check_interface.py` verifies the supplied file hashes, exact field order and required packages without ROS. The ROS
integration test starts both C++ examples on a unique namespace, checks repeated message delivery and all four values,
and confirms that the C++ listener reports receiving them. Neither test actuates a vehicle.

### Run the examples

The supplied publisher emits a fixed curvature of **0.1 1/m** and speed of **2.5 m/s**, with both validity flags true.
Use the demo namespace below so those sample requests do not enter the truck's `/control_cmd` topic.

In each terminal, source the ROS installation and this workspace's `install/setup.bash` first.

```bash
# Terminal 1
ros2 run control_listener_pkg control_listener_node --ros-args -r __ns:=/interface_demo
```

```bash
# Terminal 2
ros2 run control_node_pkg control_publisher_node --ros-args -r __ns:=/interface_demo
```

The listener should repeatedly log:

```text
Received: curvature=0.10 speed=2.50 listen_steering=1 listen_speed=1
```

Stop the examples with Ctrl-C. They are interface demonstrations; they do not implement perception, lane-loss detection,
vehicle arbitration or speed control.

## Bridge architecture

```text
Perception model → control_cmd → ROS bridge → existing truck controller → existing output owner → Pixhawk
```

The bridge is an input adapter. It must not open a second MAVLink/serial writer or bypass the existing output owner.
Convert wire curvature to the truck's convention exactly once: `κ_truck = −κ_wire`.
The current truck controller uses an empirical curvature-to-normalized-steering calibration before PWM output;
`atan(wheelbase × curvature)` is not its current actuator mapping. Speed requests in m/s need deliberate integration with
the existing bounded speed controller and human controls.

Manual override, command expiry, no-lane stopping and steering handback must be tested through the integrated path.
Existing radio/flight-controller settings and previous non-ROS tests do not prove the new bridge's behavior.
See [bridge requirements](truck_bridge/README.md).

## Camera and calibration

The control interface does not publish camera images. A separate Robot Eyes camera adapter is needed to publish the
actual image stream as `sensor_msgs/msg/Image`, with consistent camera calibration information. Intrinsic calibration
uses a measured checkerboard; extrinsic calibration establishes the camera pose relative to the truck and ground.
Calibrate the image configuration used for inference and agree where distortion correction happens. A ground-plane
projection assumes locally flat terrain; it is not a measurement of arbitrary 3D terrain.

## Layout

```text
control_interfaces/               supplied message package, verbatim
examples/control_node_pkg/        supplied publisher plus runnable scaffolding and integration test
examples/control_listener_pkg/    supplied listener plus runnable scaffolding
truck_bridge/                     planned bridge behavior and validation requirements
tools/check_interface.py          source-integrity and contract checks, no ROS required
docs/                            provenance, publication scope and sign convention
```

The reported Orin host is Ubuntu 22.04 with ROS 2 Humble. Humble and Jazzy are build targets in CI; the model container's
ROS distribution, arm64 support and JetPack compatibility must be confirmed against the delivered runtime.
The perception runtime and model weights are not part of this repository. There is no additional repository manifest
or `vcstool` setup required to build these three interface/example packages.

---
Colin Rooney · [ROONEY Tech](https://rooneytech.com) · © 2026 Rooney Industries LLC · MIT.
Build log: [vaguebutexciting.dev](https://vaguebutexciting.dev) · [YouTube](https://www.youtube.com/@cprooney).
