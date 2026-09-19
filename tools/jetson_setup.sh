#!/usr/bin/env bash
# jetson_setup.sh — prepare a Jetson Orin (or any Ubuntu 22.04/24.04 box) to build and
# run a ROS 2 perception node that links libtorch, OpenCV, cv_bridge and yaml-cpp,
# alongside the control interface packages in this repository.
#
#   bash tools/jetson_setup.sh            # install what is missing, then print the check table
#   bash tools/jetson_setup.sh --check    # print the check table only, install nothing
#
# Idempotent: re-running skips what is already present. Needs sudo for apt.
# Exit codes: 0 all checks pass · 1 a check failed · 2 unsupported platform (see message).
set -uo pipefail

CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '  \033[32mPASS\033[0m  %s\n' "$*"; }
fail() { printf '  \033[31mFAIL\033[0m  %s\n' "$*"; FAILED=1; }
FAILED=0

# ---------------------------------------------------------------- platform
say "Platform"
[[ -f /etc/os-release ]] || { echo "  This is not a Linux host; run it on the Jetson (or an Ubuntu laptop)."; exit 2; }
UBU="$(. /etc/os-release && echo "$VERSION_ID")"
ARCH="$(uname -m)"
JETPACK="none"
if [[ -f /etc/nv_tegra_release ]]; then
  L4T="$(head -1 /etc/nv_tegra_release | sed -E 's/^# (R[0-9]+) \(release\), REVISION: ([0-9.]+).*/\1.\2/')"
  case "$L4T" in
    R36.*) JETPACK="6 ($L4T)";;
    R35.*) JETPACK="5 ($L4T)";;
    *)     JETPACK="unknown ($L4T)";;
  esac
fi
echo "  Ubuntu $UBU · $ARCH · JetPack $JETPACK"

case "$UBU" in
  22.04) ROS_DISTRO_WANT=humble;;
  24.04) ROS_DISTRO_WANT=jazzy;;
  *)
    echo
    echo "  Ubuntu $UBU is not a ROS 2 Humble/Jazzy host."
    if [[ "$JETPACK" == 5* ]]; then
      echo "  JetPack 5 ships Ubuntu 20.04. Two options:"
      echo "    a) Reflash to JetPack 6 (Ubuntu 22.04) with NVIDIA SDK Manager, then re-run this script.  <- recommended"
      echo "    b) Stay on JetPack 5 and build inside a container: see docs/jetson-orin-setup.md, section 'JetPack 5'."
    fi
    exit 2;;
esac
echo "  ROS 2 target: $ROS_DISTRO_WANT"

# ---------------------------------------------------------------- installers
apt_install() {  # apt_install pkg...
  local missing=()
  for p in "$@"; do dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p"); done
  if ((${#missing[@]})); then
    if ((CHECK_ONLY)); then echo "  would install: ${missing[*]}"; return; fi
    sudo apt-get install -y --no-install-recommends "${missing[@]}"
  fi
}

if ((!CHECK_ONLY)); then
  say "ROS 2 $ROS_DISTRO_WANT"
  if [[ ! -d /opt/ros/$ROS_DISTRO_WANT ]]; then
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends curl gnupg lsb-release software-properties-common
    sudo add-apt-repository -y universe
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo "$UBUNTU_CODENAME") main" \
      | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends "ros-$ROS_DISTRO_WANT-ros-base"
  else
    echo "  already at /opt/ros/$ROS_DISTRO_WANT"
    sudo apt-get update
  fi

  say "Build tools and node dependencies"
  apt_install build-essential cmake git \
    python3-colcon-common-extensions python3-rosdep python3-pip python3-opencv python3-numpy \
    "ros-$ROS_DISTRO_WANT-cv-bridge" "ros-$ROS_DISTRO_WANT-image-transport" \
    "ros-$ROS_DISTRO_WANT-camera-calibration" "ros-$ROS_DISTRO_WANT-vision-opencv" \
    libopencv-dev libyaml-cpp-dev
  [[ -f /etc/ros/rosdep/sources.list.d/20-default.list ]] || sudo rosdep init
  rosdep update --rosdistro "$ROS_DISTRO_WANT" >/dev/null 2>&1 || true

  say "PyTorch / libtorch"
  if python3 -c 'import torch' >/dev/null 2>&1; then
    echo "  torch already installed: $(python3 -c 'import torch;print(torch.__version__)')"
  else
    if [[ "$JETPACK" == 6* ]]; then
      # NVIDIA's Jetson wheel index: CUDA-enabled torch for JetPack 6.x (CUDA 12.6).
      pip3 install --user --index-url https://pypi.jetson-ai-lab.io/jp6/cu126 torch torchvision \
        || { echo "  Jetson CUDA wheel failed; falling back to the CPU wheel from PyPI."; pip3 install --user torch torchvision; }
    else
      pip3 install --user torch torchvision
    fi
  fi
fi

# ---------------------------------------------------------------- checks
say "Checks"
if [[ -d /opt/ros/$ROS_DISTRO_WANT ]]; then ok "ROS 2 $ROS_DISTRO_WANT at /opt/ros/$ROS_DISTRO_WANT"; else fail "ROS 2 $ROS_DISTRO_WANT not installed"; fi
# shellcheck disable=SC1090
set +u; source "/opt/ros/$ROS_DISTRO_WANT/setup.bash" 2>/dev/null || true; set -u   # ROS setup files use unbound vars
command -v colcon >/dev/null && ok "colcon $(colcon version-check 2>/dev/null | head -1 | awk '{print $2}')" || fail "colcon missing"
for p in cv_bridge image_transport camera_calibration sensor_msgs rclcpp; do
  ros2 pkg prefix "$p" >/dev/null 2>&1 && ok "ros package $p" || fail "ros package $p missing"
done
dpkg -s libopencv-dev >/dev/null 2>&1 && ok "libopencv-dev $(dpkg -s libopencv-dev | awk '/^Version/{print $2}')" || fail "libopencv-dev missing"
dpkg -s libyaml-cpp-dev >/dev/null 2>&1 && ok "libyaml-cpp-dev" || fail "libyaml-cpp-dev missing"

TORCH_DIR="$(python3 -c 'import torch,os;print(os.path.dirname(torch.__file__))' 2>/dev/null || true)"
if [[ -n "$TORCH_DIR" ]]; then
  TV="$(python3 -c 'import torch;print(torch.__version__)')"
  CUDA="$(python3 -c 'import torch;print("cuda" if torch.cuda.is_available() else "cpu")')"
  ok "torch $TV ($CUDA)"
  [[ -f "$TORCH_DIR/include/torch/script.h" ]] && ok "libtorch headers" || fail "libtorch headers missing (torch/script.h)"
  [[ -f "$TORCH_DIR/share/cmake/Torch/TorchConfig.cmake" ]] && ok "TorchConfig.cmake" || fail "TorchConfig.cmake missing"
  if [[ "$CUDA" == cuda ]]; then
    # The CUDA torch's TorchConfig.cmake calls enable_language(CUDA); JetPack installs nvcc but not on PATH.
    if [[ -x /usr/local/cuda/bin/nvcc ]]; then ok "nvcc at /usr/local/cuda/bin/nvcc"; else fail "nvcc missing: sudo apt-get install cuda-toolkit-12-6"; fi
  fi
  echo
  echo "  Before you build a node that links libtorch, in the same shell:"
  [[ "$CUDA" == cuda ]] && echo "    export CUDACXX=/usr/local/cuda/bin/nvcc PATH=/usr/local/cuda/bin:\$PATH"
  echo "    colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=$TORCH_DIR"
else
  fail "python torch not importable (libtorch comes from the torch wheel)"
fi

echo
if ((FAILED)); then echo "RESULT: FAIL — fix the lines above, then re-run."; exit 1; fi
echo "RESULT: PASS — this machine can build and run the node. Next: docs/jetson-orin-setup.md, step 3."
