# truck_bridge

**Implementation specification; no ROS bridge executable is delivered yet.**

Subscribe to `control_cmd` using `control_interfaces/msg/ControlMsg` and translate valid, fresh requests into the existing
truck controller. The existing output owner remains the only steering/throttle writer to the Pixhawk. Do not add a
separate MAVLink or serial writer in this package.

## Required behavior

- Convert curvature once: wire positive-left → truck positive-right, `κ_truck = −κ_wire`.
- Use the existing empirical curvature-to-steering calibration and bounded speed controller. The controller accepts
  normalized steering and PWM throttle downstream, not raw curvature and m/s. Avoid applying perception projection or
  steering gain a second time to an already-computed ROS curvature request.
- Respect the radio mode, manual intervention, speed limits and existing output arbitration.
- Evaluate `listen_to_steering` and `listen_to_speed` independently. A field whose flag is false is not a command to apply.
- On the agreed no-lane message (`listen_to_steering=false`, valid speed request `0`), request a stop and restore human
  steering. The retained curvature is reference data. Substituting zero steering under full model authority would center
  the wheels, not restore full human steering authority.
- Handle invalid steering with a nonzero valid speed request deliberately; validity flags alone are not a lane detector.
- Reject non-finite and out-of-range values according to documented limits, and expire stale requests using a monotonic
  clock. Define behavior on startup, producer disconnect, reconnect and mode changes; never retain steering indefinitely.
- The message has no source timestamp. Receipt timeout must be complemented by image-age/producer-health information
  or a verified acquisition/queue mechanism before field operation. A newly received command may use an old image.

## Validation sequence

1. Unit/integration tests with synthetic messages: both curvature signs, zero, each validity combination, no-lane,
   invalid values, stale commands, producer loss and reconnection, and mode changes.
2. Recorded-image replay, then live images with physical output disabled. Verify sign, image age, cadence and requested
   steering/speed against ground truth and the existing controller boundary.
3. Bench checks with the integrated output owner: stop behavior, wheel direction, handback, radio veto and timeout.
4. Supervised low-speed field validation after the preceding checks pass.

These are acceptance requirements. Existing non-ROS bench tests do not establish that the ROS integration passes them.
