# The one negation, written down

- **Wire (`/desired_control.curvature`):** positive = left. ROS right-handed, `base_footprint`.
- **Truck tools (`live_trail.py`, the field logs):** a left bend produces goal x < 0 and κ < 0; positive κ = right.
- **Servo:** higher PWM = wheels left (measured on the truck, 2026-09-06 and 2026-09-07).

The bridge applies `κ_truck = −κ_wire` exactly once. Nowhere else in either stack flips a sign for this reason.
