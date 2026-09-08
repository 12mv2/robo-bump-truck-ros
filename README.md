# robo-bump-truck-ros

**Drive the [Robo Bump Truck](https://vaguebutexciting.dev/posts/kitchen-robot-eyes-log1/) from any lane- or trail-following model.**
This repo is the ROS 2 interface to the truck: the message a model publishes, and the bridge node that turns it into a
steering and throttle request for the truck's flight controller. Your model stays in your repo; you depend on this one.

The truck is an RC Traxxas Stampede 2WD with a Jetson Orin Nano, a Pixhawk 6C Mini running ArduPilot Rover, and an iPhone
as the camera ([Robot Eyes](https://github.com/12mv2/robot-eyes) records and streams it). It has steered itself on a real
trail from the phone's camera. Everything here is the seam between a perception model and that vehicle.

## The contract

A model publishes one topic, `/desired_control`, at ~10 Hz:

| field | meaning | convention |
|---|---|---|
| `curvature` | requested path curvature, 1/m | **positive = LEFT** (ROS right-handed, `base_footprint` frame: X forward, Y left, Z up, on the ground under the rear axle) |
| `speed` | requested forward speed, m/s | the truck may cap it; today the human keeps the throttle |
| `listen_to_steering` | the request is valid | **`false` = "I do not see a lane"**: speed 0, steering holds its last valid angle, the human can take over |
| `listen_to_speed` | the speed field is valid | |
| `header` | stamp + frame | |

The exact `.msg` lives in `desired_control_msgs/` and is imported verbatim by both sides — never retyped.

**No-lane behaviour is a safety contract, not a detail.** Publishing nothing means the bridge holds the last command and the
truck keeps turning into whatever made the model lose the lane; publishing zero curvature means it straightens and drives off
the trail. So the model always publishes, and says so with the flag.

## What the bridge does with it

`truck_bridge/` turns the request into what ArduPilot Rover accepts today: an RC override on the steering channel while the
vehicle is in MANUAL. Steering angle `δ = atan(L·κ)` with wheelbase `L = 0.269 m`, mapped to the servo's calibrated PWM.
On the truck **positive PWM = left** and the truck's own tools use **positive κ = right**, so the bridge negates once, here,
and the wire convention above wins.

Safety model, all enforced by the flight controller and the radio, none by this node:
- the radio's 3-position switch: **out = model steers · middle = blend with the human's wheel · toward the driver = HOLD**;
- a kill knob that stops the motor regardless of anything on the Orin;
- `RC_OVERRIDE_TIME 3 s`: if the bridge stops publishing, steering returns to the radio within three seconds;
- throttle stays on the human's trigger until the truck earns otherwise.

A configured failsafe is not a demonstrated failsafe. Every one of these has been induced on the bench and watched.

## Layout

```
desired_control_msgs/   the message package (colcon; imported verbatim by model and bridge)
truck_bridge/           the bridge node: /desired_control → ArduPilot (MAVLink RC override today; MAVROS later)
workspace.repos         a vcstool list to assemble a workspace with your model alongside these two
docs/                   calibration (camera → vehicle frame), the seam sign convention, field notes
```

## Distros

The truck's Orin is JetPack 6 = Ubuntu 22.04 = **ROS 2 Humble** natively. A Jazzy model runs in a 24.04 container on it.
The message package builds on both.

## Status

Interface repo, freshly cut (2026-09-08). The message definition is being supplied by the model side; the bridge node follows.
Nothing here is claimed until it has driven the truck: **not tested, therefore not claimed.**

---
Colin Rooney · [ROONEY Tech](https://rooneytech.com) · © 2026 Rooney Industries LLC · MIT.
Build log: [vaguebutexciting.dev](https://vaguebutexciting.dev) · [YouTube](https://www.youtube.com/@cprooney).
