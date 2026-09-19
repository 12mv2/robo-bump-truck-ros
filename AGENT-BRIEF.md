# Brief for a coding agent: get a perception node running on a Jetson Orin

Paste this file to Claude Code (or any agent) running on the Jetson. It is self-contained.
The human owns the node's source, its trained model file and its config. This repository owns the ROS
interface and the setup tooling. Nothing here drives a vehicle.

## Goal

A ROS 2 node that subscribes to `/image_raw` (`sensor_msgs/Image`) and publishes `/control_cmd`
(`control_interfaces/ControlMsg`) builds on this Jetson and publishes at close to the replay rate when
recorded frames are fed to it.

## Steps, each with its pass signal

1. **Platform.** Run `head -1 /etc/nv_tegra_release`. Pass: it starts with `# R36` (JetPack 6). If `# R35`, stop
   and tell the human: JetPack 5 needs a reflash to JetPack 6 or the container path in `docs/jetson-orin-setup.md`.
2. **Setup.** `git clone https://github.com/12mv2/robo-bump-truck-ros.git && cd robo-bump-truck-ros && bash tools/jetson_setup.sh`.
   Pass: the final line is `RESULT: PASS`. Note the `-DCMAKE_PREFIX_PATH=...` line it prints; you need it in step 4.
   If a line says FAIL, fix that one item and re-run the script. Do not skip to the build.
3. **Workspace.** Create `~/ros2_ws/src`, symlink `control_interfaces` from this repo into it, and copy in the human's
   node package (source, `CMakeLists.txt`, `package.xml`), any message package it defines, its YAML config and its
   `.pt` model file. Ask the human where those are; do not invent them.
4. **Build.** From `~/ros2_ws`: `source /opt/ros/humble/setup.bash`, then `rosdep install --from-paths src --ignore-src -y`,
   then the `export CUDACXX=... PATH=...` line and the `colcon build ...` line exactly as the setup script printed them.
   Pass: `Summary: N packages finished` with 0 failed. Common fixes are in the troubleshooting table of
   `docs/jetson-orin-setup.md`. The node was written against ROS 2 Jazzy; on Humble the most likely difference is
   the cv_bridge header name (`.h` on Humble, `.hpp` on Jazzy). Fix that with `__has_include`, not by editing anything else.
5. **Run.** Three terminals, all with `source ~/ros2_ws/install/setup.bash`:
   - A: `python3 tools/watch_control_cmd.py`
   - B: the node, with its `model_path` parameter pointing at the `.pt` file
   - C: `python3 tools/replay_images.py <frames folder> --rate 5 --loop` (frames: any folder of jpg/png; from a video,
     `ffmpeg -i in.mp4 -vf fps=5 frames/%05d.jpg`)
   Pass: terminal A prints one line per message at about 5 Hz, with `steer=1` on frames that show a road.
6. **Report** back to the human, in this order: the `RESULT` line from step 2, the colcon summary from step 4, twenty
   lines from terminal A, and the average Hz. If the Hz is well below 5, say so; do not change the node to CUDA
   unless the human asks.

## Rules

- Do not modify `control_interfaces/msg/ControlMsg.msg`. It is the shared contract.
- Do not download an x86 libtorch. The torch wheel the script installs already contains the aarch64 libtorch.
- Do not commit the model file or config into this repository.
- If something fails twice the same way, stop and show the human the exact error rather than trying a third workaround.
