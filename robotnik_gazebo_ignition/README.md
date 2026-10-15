# Robotnik Gazebo Ignition

<img src="../docs/assets/img/ignition_simulation_view.png" alt="Robotnik Gazebo Ignition Simulation View" height=300>

This package provides the Gazebo-based simulation layer for Robotnik robots on ROS 2. It includes world launching, robot spawning, ROS 2 <-> Gazebo bridges, control integration and auxiliary simulation resources.

> **Branch-specific guide**: `robotnik_gazebo_ignition` is maintained across ROS 2 distro branches, but the Gazebo version changes with each branch. This README documents only the launch/configuration workflow in this checkout for `jazzy-devel`: ROS 2 Jazzy + Gazebo Harmonic. For conceptual background about architecture, compatibility and versioning, see [`../docs/ros2-gazebo-compatibility.md`](../docs/ros2-gazebo-compatibility.md).
>
> **Docker guide**: the Docker build and runtime workflow is documented separately in [`../docker/README.md`](../docker/README.md).

## What this package includes

- Gazebo world launch files
- Robot spawn launch files
- ROS 2 <-> Gazebo topic bridging
- `gz_ros2_control` integration for simulated control
- RViz resources and Gazebo bridge profiles

The robot files in `robotnik_description` provide the robot description.
The base Gazebo control adapter is composed separately; individual components
such as an arm or lift can already contribute their own control systems. `spawn_robot.launch.py` composes the selected
`robot_xacro_path` with the matching adapter under
`robotnik_description/simulators/gazebo_ignition`. Expanding a description
xacro directly with `gazebo_ignition:=true` does not add the base control adapter; use this package's launcher or
`robotnik_description/simulators/gazebo_ignition/robot.urdf.xacro` when a
complete Gazebo robot description is required.

## Installation

### General requirements

Before following the branch-specific steps below, make sure you have:

- ROS 2 Jazzy installed
- `curl`, `gnupg`, `vcs`, `rosdep` and `colcon` available
- permission to install Gazebo and ROS 2 packages from apt

The following commands describe a source installation. Docker has a separate
[installation and GPU guide](../docker/README.md).

### Jazzy-specific installation

1. Set up the Gazebo package repository:

```bash
# Run on a machine with ROS 2 Jazzy already installed
sudo apt update
sudo apt-get install curl lsb-release gnupg
sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
```

2. Install Gazebo Harmonic:

```bash
# Run after adding the Gazebo package repository
sudo apt-get update
sudo apt-get install -y \
  gz-harmonic \
  libgz-sim8-dev
```

3. Clone this repository, then import its external dependencies from a local manifest:

```bash
mkdir -p ~/ros2_ws/src/robotnik
cd ~/ros2_ws
git clone --branch jazzy-devel https://github.com/RobotnikAutomation/robotnik_simulation.git src/robotnik/robotnik_simulation
vcs import --skip-existing src < src/robotnik/robotnik_simulation/dependencies/repos/robotnik_simulation.jazzy.repos
```

If this repository is already checked out, keep that checkout and run only the
import command from the workspace root. The release manifest pins external
repository revisions. For the branch-based dependency set, use
[`robotnik_simulation.jazzy-devel.repos`](../dependencies/repos/robotnik_simulation.jazzy-devel.repos)
instead. Docker uses the pinned
[`robotnik_simulation.jazzy.repos`](../dependencies/repos/robotnik_simulation.jazzy.repos).
Use a dependency set compatible with your simulation/description sources.

4. Install the Robotnik-specific prebuilt debs shipped in this repository:

```bash
# Run from the repository root inside the workspace
cd ~/ros2_ws/src/robotnik/robotnik_simulation
sudo apt-get install -y ./debs/ros-jazzy-*.deb
```

5. Resolve the remaining dependencies and build the workspace:

```bash
# Run from the workspace root after importing all repositories
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
rosdep update
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Quick start

Once the installation is complete and the workspace is built, these are two ways to get `rbwatcher` running.

### Option 1: Integrated bringup for `rbwatcher`

```bash
# Run after building the workspace
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py \
  robot:=rbwatcher \
  robot_model:=rbwatcher
```

### Option 2: Standalone world + robot flow for `rbwatcher`

Terminal 1:

```bash
# Run after building the workspace
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py world:=empty
```

Terminal 2:

```bash
# Run while Gazebo is already active
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py \
  robot:=rbwatcher \
  robot_model:=rbwatcher \
  run_spawn_rviz:=true
```

## Usage

### Spawn World

This is the first operational step in the simulation flow. It launches Gazebo and loads the selected world.

#### Basic

```bash
# Run after sourcing the workspace and with no robot spawned yet
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py world:=empty

# Run to start the same world without the Gazebo GUI
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py world:=empty run_gazebo_gui:=false
```

#### Arguments

All four arguments are optional:

| Argument | Default | Effect |
|---|---|---|
| `world` | `demo` | Built-in world name, without `.world` |
| `world_path` | `worlds/<world>.world` in this package | Explicit world file overrides the name-derived path |
| `run_gazebo_gui` | `true` | Start the GUI in addition to the server |
| `use_nvidia_gpu` | `false` | Request NVIDIA PRIME rendering for the server and GUI |

An empty `world_path` is not a default selector: omit the argument to use the
path derived from `world`.

#### NVIDIA PRIME rendering

Use the launch argument instead of adding PRIME variables before every command:

```bash
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py use_nvidia_gpu:=true
```

It is also accepted by `bringup_complete.launch.py`. The launcher applies the
PRIME environment settings only to the Gazebo server and GUI, including
server-side sensor rendering when `run_gazebo_gui:=false`. RViz and the clock
bridge keep their inherited environment.

The default is **false**. False preserves normal GPU selection and inherited
environment settings; it does not disable hardware acceleration or force
software rendering. In Docker, set `USE_NVIDIA_GPU=true` and use the
[GPU Compose overlay](../docker/README.md#nvidia-gpu). The argument requests
PRIME offload; it does not install a driver or expose container devices.

#### Supported worlds

| Name | Description | Thumbnail |
|---|---|---|
| `empty` | Empty world with a flat ground plane | <img src="../docs/assets/world/empty.png" alt="empty world" height=100> |
| `demo` | Demo world with obstacles and ramps for navigation testing | <img src="../docs/assets/world/demo.png" alt="demo world" height=100> |
| `ionic` | Demo world from Gazebo showing Ionic simulation features | <img src="../docs/assets/world/ionic.png" alt="ionic world" height=100> |
| `lightweight_scene` | Lightweight scene for performance testing | <img src="../docs/assets/world/lightweight_scene.png" alt="lightweight scene" height=100> |

### Spawn Robot

This launch file inserts a robot into an already running Gazebo simulation.

> **Important**: `spawn_robot.launch.py` does not launch Gazebo. A world must already be active before spawning a robot.

#### Basic

```bash
# Run after Gazebo is already running to spawn the default RB-Watcher
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py robot:=rbwatcher

# Run to spawn the robot with a custom namespace and pose
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py \
  robot_id:=robot_a \
  robot:=rbwatcher \
  robot_model:=rbwatcher \
  x:=0.0 y:=0.0 z:=0.0 \
  run_spawn_rviz:=true

# Run to spawn a mobile manipulator variant with a specific arm
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py \
  robot:=rbkairos \
  robot_model:=rbkairos_plus \
  arm_type:=ur10e \
  run_spawn_rviz:=true
```

#### Advanced

```bash
# Run after Gazebo is active to spawn any supported robot configuration
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py \
  robot_id:=robot_a \
  robot:=rbkairos robot_model:=rbkairos_plus arm_type:=ur10e \
  x:=1.0 y:=0.0 z:=0.0 \
  run_spawn_rviz:=false
```

#### Arguments

All thirteen arguments are optional:

| Argument | Default | Effect |
|---|---|---|
| `robot_id` | `robot` | Gazebo entity name and ROS namespace |
| `robot` | `rbwatcher` | Robot family |
| `robot_model` | Value of `robot` | Robot variant |
| `robot_xacro_path` | `robotnik_description/robots/<robot>/<robot_model>.urdf.xacro` | Description override |
| `frame_prefix` | `<robot_id>_` | Prefix of frames and joints |
| `x` | `0.0` | Initial X position in metres |
| `y` | `0.0` | Initial Y position in metres |
| `z` | `0.0` | Initial Z position in metres |
| `arm_type` | `ur10e` | Xacro `ur_type` for variants with a manipulator |
| `run_spawn_rviz` | `true` | Open the basic RViz view |
| `spawn_rviz_config` | Empty | Basic RViz override; empty selects the package configuration |
| `use_sim_time` | `true` | Use the simulated clock for launch-configured processes |
| `low_performance_simulation` | `false` | Reduced sensor settings passed to Xacro |

A manipulator is selected through `robot_model`, for example `rbkairos_plus`.
There is no `has_arm` launch argument. The Xacro override changes only the
robot description: matching control and bridge profiles are still selected
using `robot` and `robot_model`.

These are standalone defaults. Bringup passes its own values explicitly; in
particular its default family is `rbsummit` and reduced sensor settings are true.
The launch does not read `robot.env` or uppercase environment variables.

#### Supported robots

| robot | robot_model options | Notes |
|---|---|---|
| `rbwatcher` | `rbwatcher` | Supported |
| `rb1` | `rb1` | Limited |
| `rbcar` | `rbcar` | Limited |
| `rbfiqus` | `rbfiqus` | Limited |
| `rbkairos` | `rbkairos`, `rbkairos_plus` | Limited |
| `rbrobout` | `rbrobout`, `rbrobout_plus` | Limited |
| `rbsummit` | `rbsummit` | Limited |
| `rbsummit_steel` | `rbsummit_steel` | Limited |
| `rbtheron` | `rbtheron`, `rbtheron_plus` | Limited |
| `rbvogui` | `rbvogui`, `rbvogui_plus` | Limited |
| `rbvogui_xl` | `rbvogui_xl` | Limited |

`Limited` means the robot has been integrated but may still require additional validation or tuning for some workflows.

#### Robot type vs robot model

The description package is [robotnik_description](https://github.com/RobotnikAutomation/robotnik_description).
`robot` selects a family directory, such as `rbwatcher` or `rbsummit`;
`robot_model` selects `<robot_model>.urdf.xacro` directly inside that directory.
With no variant override, spawn uses the family name as the variant. There is
no intermediate `models/` directory in the current description layout.

#### Notes

- Use a unique `robot_id` when spawning multiple robots in the same world to avoid name conflicts in topics and frames.
- `rbcar` spawns the `ros2_control` Ackermann controller, so its velocity commands use `geometry_msgs/msg/TwistStamped`.
- For additional launch variants, GPU-specific notes and troubleshooting guidance, see [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md).

## Control the robot

The command topic and message type depend on the selected controller. Inspect
the running robot before selecting a publisher:

```bash
ros2 topic list -t
ros2 topic info /robot/robotnik_base_control/cmd_vel_unstamped
```

For an RB-Watcher using its packaged base controller, the keyboard example is:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -r cmd_vel:=/robot/robotnik_base_control/cmd_vel_unstamped \
  -p stamped:=false
```

This publishes `geometry_msgs/msg/Twist`. If the selected input expects
`TwistStamped`, use `stamped:=true` and the corresponding topic. For example,
RB-Car's Ackermann spawner remaps its reference input to
`/robot/robotnik_base_control/cmd_vel`. Replace `/robot` for a different instance.
Install `ros-jazzy-teleop-twist-keyboard` separately if it is not available.

The packaged basic/navigation RViz layouts include a Teleop panel whose topic
is resolved using `robot_id`. A custom RViz file must provide its own compatible
displays and command topic. Avoid competing keyboard, panel and navigation
publishers unless your system explicitly arbitrates them.

## MoveIt compatibility

It is possible to use [MoveIt](https://moveit.picknik.ai/main/index.html) to control robotic arms mounted on supported platforms.

The examples use `robot_id:=robot`. Namespace/prefix substitution has been
checked offline; interactive operation with other namespaces still needs runtime
validation. Use matching identity, prefix and description arguments in simulation
and MoveIt.

MoveIt can be launched in two ways:

1. From `robotnik_simulation_bringup` using `run_moveit:=true`
2. Independently from `robotnik_simulation_moveit`

Example from bringup:

```bash
# Start a new simulation with manipulation; do not run over an existing world
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py \
  robot:=rbkairos \
  robot_model:=rbkairos_plus \
  arm_type:=ur10e \
  run_moveit:=true
```

Example standalone:

```bash
# Run after the robot and controllers are already running in simulation
ros2 launch robotnik_simulation_moveit moveit.launch.py \
  robot_id:=robot \
  robot:=rbkairos \
  robot_model:=rbkairos_plus \
  arm_type:=ur10e \
  run_moveit_rviz:=true
```

Example standalone with custom `robot_xacro_path`:

```bash
# Run after the robot and controllers are already running, using a custom robot description
ros2 launch robotnik_simulation_moveit moveit.launch.py \
  robot_id:=robot \
  robot:=rbkairos \
  robot_model:=rbkairos_plus \
  robot_xacro_path:=/path/to/robot.urdf.xacro \
  arm_type:=ur10e \
  run_moveit_rviz:=true
```

![moveit_rviz](../docs/assets/img/moveit-rviz.png)

The current manipulation profile pairs are:

- `robot:=rbkairos robot_model:=rbkairos_plus`
- `robot:=rbrobout robot_model:=rbrobout_plus`
- `robot:=rbtheron robot_model:=rbtheron_plus`
- `robot:=rbvogui robot_model:=rbvogui_plus`

For the standalone MoveIt flow and its parameters, see [`../common/robotnik_simulation_moveit/README.md`](../common/robotnik_simulation_moveit/README.md).

## Customization

### Edit the robot model

Specific robot models can be customized by creating your own URDF/XACRO files based on the existing ones in `robotnik_description`.

1. Copy the existing robot folder from `robotnik_description/robots/<robot>/` into a new custom folder.
2. Modify the URDF/XACRO files to add or adapt components.
3. Update any required configuration files for sensors, arms or other components.
4. Spawn the customized robot using `robot_xacro_path`.

Example:

```bash
# Run after Gazebo is active to spawn a customized robot variant
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py \
  robot:=rbkairos \
  robot_model:=rbkairos_plus \
  arm_type:=ur10e
```

With custom `robot_xacro_path`:

```bash
# Run after Gazebo is active to spawn a robot from your custom XACRO path
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py \
  robot:=rbkairos robot_model:=rbkairos_plus \
  robot_xacro_path:=/absolute/path/to/custom_kairos.urdf.xacro
```

### Robot-specific control configuration

Robot-specific `ros2_control` configurations are maintained by
`robotnik_simulation_robots` under each robot's `control/` directory. The
`config/profile/` files in this package configure Gazebo-to-ROS topic bridges.

## Docker

The full development Docker workflow is documented in [`../docker/README.md`](../docker/README.md).

Use that guide for:

- running the published image or building an image that copies only this repository from the local machine and pulls any extra required repositories from [`../dependencies/repos/robotnik_simulation.jazzy.repos`](../dependencies/repos/robotnik_simulation.jazzy.repos)
- editing the runtime configuration in [`../env/robot.env`](../env/robot.env)
- opening a second terminal with `docker exec` to interact with the running simulation inside the runtime container
- GPU-enabled Docker sessions
- cleanup and reset commands


## Related documentation

- Conceptual ROS 2 + Gazebo guide: [`../docs/ros2-gazebo-compatibility.md`](../docs/ros2-gazebo-compatibility.md)
- Integrated simulation bringup: [`../common/robotnik_simulation_bringup/README.md`](../common/robotnik_simulation_bringup/README.md)
- Standalone MoveIt flow: [`../common/robotnik_simulation_moveit/README.md`](../common/robotnik_simulation_moveit/README.md)
- GPU notes and troubleshooting: [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
