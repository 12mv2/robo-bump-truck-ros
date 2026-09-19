# Running a perception node on a Jetson Orin

How to get a ROS 2 node that links **libtorch, OpenCV, cv_bridge and yaml-cpp** building and
publishing `/control_cmd` on a Jetson Orin Nano / Orin Nano Super, with no truck and no camera.
If you use Claude Code or another agent, hand it [AGENT-BRIEF.md](../AGENT-BRIEF.md) instead of this page.

No container is needed. JetPack 6 is Ubuntu 22.04, which runs ROS 2 Humble natively, and the
node's dependencies are all apt or pip packages.

## Verified on

This exact procedure was run end to end on this hardware. Versions below are what the script installed or found.

| Item | Version | Date |
|---|---|---|
| Board | NVIDIA Jetson Orin Nano Developer Kit (Super), 8 GB | 2026-09-18 |
| JetPack / L4T | 6.2.1 / R36.4.7 | |
| Ubuntu | 22.04.5 LTS | |
| ROS 2 | Humble, rclcpp 16.0.19, cv_bridge 3.2.1, colcon-core 0.21.3 (common-extensions 0.3.0) | |
| PyTorch / libtorch | 2.8.0, CUDA 12.6, cuDNN 9.3 (NVIDIA Jetson wheel) | |
| OpenCV | libopencv-dev 4.8.0 | |
| yaml-cpp | 0.7.0 | |
| Toolchain | cmake 3.22.1, g++ 11.4.0 | |

If your versions differ, the script still runs; the table is what "known good" means.

Measured on that machine the same day, with a perception node (rclcpp + libtorch CPU + cv_bridge, TorchScript model,
160×120 input) built by steps 2–3 and fed by step 4. **The model was a zero-parameter stand-in with the same output
shape**, so these numbers prove the pipeline and the publisher limits, not a trained model's throughput. Steering was
not accepted in this test (`listen_to_steering=false` throughout: no flat-world calibration file was configured, so
curvature was NaN by design). An independent rerun the same evening reproduced them: 4.66 Hz in, 4.59 Hz out, one process.

| Replay resolution | `/image_raw` rate | `/control_cmd` rate | Note |
|---|---|---|---|
| 640×480 | 4.7 Hz | 3.7 Hz over a 22 s window that includes node start-up; one command per frame once running | node keeps up on CPU |
| 1920×1440 | 0.57 Hz | 0.45 Hz | the Python publisher is the limit, not the node |

One node process was confirmed running during each measurement. An earlier pass had leaked copies of the node
(killing the `ros2 run` wrapper does not kill the node; and `pkill -x` misses it because Linux truncates process
names to 15 characters), which multiplied the command rate. Kill the node by PID, or `pkill road_centerline`.

Build of that node on the Orin: 92 s. The only source change it needed for Humble was the cv_bridge include (see
troubleshooting). The nvcc PATH line was needed; without it CMake fails inside TorchConfig.

## 1. Which JetPack am I on?

```bash
head -1 /etc/nv_tegra_release
```

| Line starts with | JetPack | Ubuntu | ROS 2 | Path |
|---|---|---|---|---|
| `# R36` | 6.x | 22.04 | Humble | this page, step 2 |
| `# R35` | 5.x | 20.04 | none native | reflash to JetPack 6 with SDK Manager (recommended), or see *JetPack 5* below |

A plain Ubuntu 22.04 or 24.04 laptop also works with this script (Humble or Jazzy). It just has no CUDA.

## Working on the Jetson from a laptop

The Jetson needs a keyboard only to set up SSH once. After that, work from your laptop.

**Direct Ethernet cable (simplest, no router).** Plug a cable between the laptop and the Jetson. On the laptop share
the internet connection to that port (macOS: System Settings › General › Sharing › Internet Sharing; Ubuntu: set the
wired connection to "Shared to other computers"). The Jetson then gets an address in the laptop's shared range;
find it with `arp -a` on the laptop, or on the Jetson `ip -4 addr show eth0`.

**Same Wi-Fi or router.** `hostname -I` on the Jetson gives its address.

Then:

```bash
ssh <user>@<jetson-address>
```

**Running an agent.** Claude Code runs on the Jetson itself (arm64 Linux), so the agent sees the real machine:

```bash
# on the Jetson, once
curl -fsSL https://claude.ai/install.sh | bash
# then, in the repository
cd ~/robo-bump-truck-ros && claude
```

Paste the contents of [AGENT-BRIEF.md](../AGENT-BRIEF.md) as the first message. Alternatively run the agent on the
laptop and let it drive the Jetson through `ssh`; that works but every command then needs the ssh prefix.

## 2. Install everything

```bash
git clone https://github.com/12mv2/robo-bump-truck-ros.git
cd robo-bump-truck-ros
bash tools/jetson_setup.sh
```

The script installs ROS 2 if missing, the build tools, `cv_bridge`, `image_transport`,
`camera_calibration`, OpenCV and yaml-cpp dev packages, and the NVIDIA Jetson build of PyTorch
(which contains libtorch and its CMake config). It ends with a check table and a `RESULT:` line.
Re-run it any time; it only installs what is missing. `bash tools/jetson_setup.sh --check` prints the
table without installing anything.

The last lines give you the libtorch prefix for CMake, for example:

```text
colcon build --cmake-args -DCMAKE_PREFIX_PATH=/home/you/.local/lib/python3.10/site-packages/torch
```

## 3. Build a workspace with your node in it

```bash
mkdir -p ~/ros2_ws/src
ln -s ~/robo-bump-truck-ros/control_interfaces ~/ros2_ws/src/
cp -r /path/to/your_node_package ~/ros2_ws/src/        # your rclcpp node, its msg package if any, config and model file
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -y --rosdistro humble
export CUDACXX=/usr/local/cuda/bin/nvcc PATH=/usr/local/cuda/bin:$PATH   # Jetson only: CUDA torch needs nvcc
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=$TORCH_PREFIX
source install/setup.bash
```

`$TORCH_PREFIX` is the path the setup script printed (it also prints the two lines above, ready to paste). In your node's `CMakeLists.txt`, `find_package(Torch REQUIRED)`
and `target_link_libraries(... ${TORCH_LIBRARIES})` are enough; do not download an x86 libtorch.

## 4. Prove it publishes, with recorded frames

Terminal A, watch the output topic:

```bash
source ~/ros2_ws/install/setup.bash
python3 ~/robo-bump-truck-ros/tools/watch_control_cmd.py
```

Terminal B, run your node (your own launch command, model path pointing at your `.pt`).

Terminal C, replay frames into `/image_raw` at the truck's 5 fps:

```bash
source /opt/ros/humble/setup.bash
python3 ~/robo-bump-truck-ros/tools/replay_images.py /path/to/frames --rate 5 --loop --resize 640x480
```

Keep `--resize`. Full 1920×1440 frames are 8 MB each and the Python publisher cannot push them through DDS at 5 fps
(measured 0.57 fps on an Orin Nano); at 640×480 it holds 4.6 fps, and a node resizes to its own model input anyway.

Expected in terminal A, one line per message:

```text
#    1    0.21s  curvature=+0.0312 1/m  speed=1.00 m/s  steer=1 speed_ok=1  avg 4.85 Hz
```

Pass means: messages arrive, `avg` Hz is close to the replay rate, `steer=1` on frames with a visible road,
`steer=0` with `speed=0.00` on frames without one. Report the Hz and a screenshot of about 20 lines.

This is a wiring and throughput test. It says nothing about whether the curvature is *correct*; that needs the
camera calibration in the README's *Camera and calibration* section and then a replay on the truck.

### Frames to replay

Any folder of `.jpg`/`.png`. To extract frames from a recorded video at 5 fps:

```bash
mkdir frames && ffmpeg -i recording.mp4 -vf fps=5 frames/%05d.jpg
```

## 5. Optional: check the wiring without your node

The repository's example publisher and listener prove the topic path on this machine in under a minute:

```bash
cd ~/ros2_ws && colcon build --base-paths ~/robo-bump-truck-ros/control_interfaces ~/robo-bump-truck-ros/examples
source install/setup.bash
ros2 run control_listener_pkg control_listener_node --ros-args -r __ns:=/interface_demo &
ros2 run control_node_pkg control_publisher_node --ros-args -r __ns:=/interface_demo
```

## CPU or GPU

If your node loads the model with `torch::kCPU`, it runs on the Orin's six ARM cores. Measure the Hz first.
If it is below the frame rate, change the load and the input tensor to `torch::kCUDA`; the Jetson wheel has CUDA
built in (`python3 -c 'import torch;print(torch.cuda.is_available())'` should print `True`).

## JetPack 5

Ubuntu 20.04 has no supported ROS 2 Humble packages. If you cannot reflash, build inside the official arm64 image:

```bash
sudo docker run -it --rm --runtime nvidia --network host -v ~/ros2_ws:/ws ros:humble-ros-base
# inside: apt-get update && bash /ws/robo-bump-truck-ros/tools/jetson_setup.sh, then steps 3-4
```

CUDA inside the container needs the NVIDIA container runtime that JetPack installs; without it the node runs on CPU.
This is the only situation in this project where a container is needed.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Could not find a package configuration file provided by "Torch"` | CMake cannot see libtorch | pass `-DCMAKE_PREFIX_PATH=<torch prefix>` from the setup script |
| `No CMAKE_CUDA_COMPILER could be found` from `Caffe2/public/cuda.cmake` | CUDA torch needs nvcc; JetPack does not put it on PATH | `export CUDACXX=/usr/local/cuda/bin/nvcc PATH=/usr/local/cuda/bin:$PATH` before `colcon build` (the setup script prints this) |
| `libtorch_cuda.so: cannot open shared object` at run time | wheel installed with `--user`, not on the loader path | `export LD_LIBRARY_PATH=<torch prefix>/lib:$LD_LIBRARY_PATH` |
| `cv_bridge/cv_bridge.hpp: No such file` on Humble | Humble installs `cv_bridge/cv_bridge.h` | include `<cv_bridge/cv_bridge.h>`, or add both behind `__has_include` |
| `ros2 pkg prefix cv_bridge` fails after install | ROS not sourced in this shell | `source /opt/ros/humble/setup.bash` |
| `rosdep init` says already initialized | harmless | ignore |
| watcher prints nothing | topic name mismatch | `ros2 topic list`, then `ros2 topic echo` the one your node publishes |
| command rate higher than the frame rate | more than one copy of the node is running | `pgrep -a road_centerline`; kill by PID. Ctrl-C on `ros2 run` does kill the node, `kill` on the wrapper PID does not |
