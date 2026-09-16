# The one negation

- **Wire (`control_cmd`, `control_interfaces/msg/ControlMsg.desired_curvature`):** positive = left, in 1/m.
  Vehicle axes are X forward, Y left, Z up, with the origin on the ground under the rear axle.
- **Truck controller (`live_trail.py`, field logs):** positive curvature = right.
- **Servo:** higher PWM = wheels left (measured on the truck, 2026-09-06 and 2026-09-07).

The planned bridge applies `κ_truck = −κ_wire` exactly once when creating the existing controller's steering request.
Do not add another negation in the ROS publisher or output owner to compensate for this convention.
The existing empirical steering calibration and output path remain responsible for converting the truck's signed
curvature into servo output. A direct bicycle-model `atan(wheelbase × curvature)` mapping is not that calibration.

Before enabling physical output, test positive, negative and zero curvature with the bridge connected to the existing
controller, then verify wheel direction on the bench. This file defines the required convention; it is not a test result.
