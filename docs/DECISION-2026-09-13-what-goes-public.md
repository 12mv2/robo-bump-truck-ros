# What of the model side goes into this PUBLIC repo — Colin's decision, 2026-09-13 19:4x

**This repo is public** (`gh repo view` → `PUBLIC`, checked 19:34). The standing rule is that nothing about the collaborator
is public. Committing their code here publishes it, irreversibly, under their name's absence but not their permission. So the
agent stopped at that line and staged everything instead.

## Staged, NOT committed

`.staging-model-side/` (git-ignored) holds what was pulled from the shared Drive `ros2_ws_code/src/` on 2026-09-13 19:3x:

| staged file | size | what it is |
|---|---|---|
| `control_interfaces/msg/ControlMsg.msg` | 106 B | **the contract itself** — 4 fields, no header |
| `control_interfaces/CMakeLists.txt`, `package.xml` | 1 KB | the message package (`rosidl_generate_interfaces`, ament_cmake) |
| `control_listener_pkg/src/control_listener_node.cpp` | 642 B | example subscriber on `control_cmd` |
| `control_node_pkg/src/control_publisher_node.cpp` | 741 B | example publisher on `control_cmd` |
| `runtime_road_centerline_node/src/road_centerline_node.cpp` | 49 KB | **their real runtime node**: image in, `CenterlineResult` + `ControlMsg` out |

Not pulled, deliberately: `build/`, `install/`, `log/`, `.git/`, and the two ~20 MB trained models
(`road_model.pt`, `west_virginia_road_model.pt`). Model weights should not be in a public repo under any option below.

## The question

Four options, and only Colin can pick:

1. **Nothing goes public.** Keep this repo as the truck's side only (bridge + docs). The message is described in the README
   and both sides keep their own copy — which is exactly the "never retyped" failure the contract was meant to prevent.
2. **The message package only** (`control_interfaces/`, ~1 KB, three files). It is the interface, it is what both sides must
   import identically, and it names no one. This is the smallest thing that makes the seam real. **Recommended, with their
   explicit yes first.**
3. **Message package + the two examples.** Adds ~1.4 KB of publisher/subscriber demo code. Useful to a third party; still
   nothing about the model or the trail.
4. **All of it, including the runtime node.** Publishes 49 KB of their perception work. The agent recommends against this
   without a clear, written yes from them.

**In every option: ask them first.** They wrote it; the repo being ours does not make the code ours to publish.

## Done in this branch already, needing no decision

- **The README contract is corrected** against their actual `ControlMsg.msg` and runtime node. Four errors fixed: the topic is
  `control_cmd`, not `/desired_control`; the package is `control_interfaces`, not `desired_control_msgs`; the fields are
  `desired_curvature` / `desired_speed`, not `curvature` / `speed`; and there is **no header**. The sign convention was already
  right (positive = LEFT), now with their derivation cited: `κ = 2·Y/L²` with Y measured left in the standard ROS vehicle frame.
- The agreed no-lane behaviour is written as a table, transcribed from what their node actually does (lane missing for several
  frames → last valid curvature held for reference, speed 0, `listen_to_steering false`).
- **`.github/workflows/colcon.yml`**: builds every package on Jazzy AND Humble (the Orin is Humble natively, the model runs in a
  Jazzy container), plus a contract check that fails if the message and the README ever drift apart. Inert until a package lands
  — deliberately, so the first real commit is checked rather than a green tick claimed today.
