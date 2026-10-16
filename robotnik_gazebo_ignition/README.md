# Robotnik Gazebo Ignition

<img src="../docs/assets/img/ignition_simulation_view.png" alt="Robotnik Gazebo Ignition Simulation View" height=300>

This package provides the Gazebo-based simulation layer for Robotnik robots on ROS 2. It includes world launching, robot spawning, ROS 2 <-> Gazebo bridges, control integration and auxiliary simulation resources.

> **Benchmark scope:** this package is also used as the Gazebo Harmonic
> backend for the Robotnik simulator benchmarking system. Benchmark-specific
> profiles and branches may pin a narrower sensor and world contract than the
> general simulation package.

> **Branch-specific guide**: `robotnik_gazebo_ignition` is maintained across ROS 2 distro branches, but the Gazebo version changes with each branch. This README documents only the validated workflow for `jazzy-devel`: ROS 2 Jazzy + Gazebo Harmonic. For conceptual background about architecture, compatibility and versioning, see [`../docs/ros2-gazebo-compatibility.md`](../docs/ros2-gazebo-compatibility.md).
>
> **Docker guide**: the full development Docker workflow is documented separately in [`../docker/README.md`](../docker/README.md).

## What this package includes

- Gazebo world launch files
- Robot spawn launch files
- ROS 2 <-> Gazebo topic bridging
- `gz_ros2_control` integration for simulated control
- RViz resources and simulation control profiles

## Installation

### General requirements

Before following the branch-specific steps below, make sure you have:

- ROS 2 Jazzy installed
- `curl`, `gnupg`, `vcs`, `rosdep` and `colcon` available
- permission to install Gazebo and ROS 2 packages from apt

This README documents the manual installation path currently validated for this branch.

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

3. Create the workspace and import the canonical repository manifest for `jazzy-devel`:

```bash
# Run from your home directory to create and populate the workspace
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws

vcs import --input https://raw.githubusercontent.com/RobotnikAutomation/robotnik_simulation/refs/heads/jazzy-devel/dependencies/repos/robotnik_simulation.jazzy.repos src/
```

`robotnik_simulation.jazzy.repos` is the validated static release manifest. Use `jazzy-devel` when you want the development branch versions instead of the fixed functional revision set.

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

Once the installation is complete and the workspace is built, the recommended Gazebo workflow is to launch a world first and then spawn one or more robots into that running world.

### Option 1: Gazebo world + robot
Terminal 1:

```bash
# Run after building the workspace
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py world:=empty
```

Terminal 2:
```bash
# Run after building the workspace
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py \
  robot:=rbwatcher \
  run_rviz:=true
```
This flow is recommended when you want to keep Gazebo running, spawn multiple robots, respawn robots during development, or test different robot models and poses without restarting the world.

### Option 2: Full navigation/manipulation demo
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py \
  robot:=rbwatcher \
  use_rviz:=true
```
`robotnik_gazebo_ignition` intentionally keeps world launching and robot spawning as separate launch files. This makes multi-robot simulation and iterative development easier. For a higher-level demo launcher, use `robotnik_simulation_bringup`.

## Usage

### Spawn World

This is the first operational step in the simulation flow. It launches Gazebo and loads the selected world.

#### Basic

```bash
# Run after sourcing the workspace and with no robot spawned yet
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py world:=empty

# Run to start the same world without the Gazebo GUI
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py world:=empty gui:=false
```

#### Advanced

```bash
# Run after sourcing the workspace to launch any available world
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py world:=<world_name> gui:=<true|false>
```

#### Parameters

| Name | Required | Purpose | Example |
|---|---|---|---|
| `world` | no | Name of the world file without the `.world` extension | `empty` |
| `world_path` | no | Full path to a custom world file; overrides `world` | `/path/to/custom_world.sdf` |
| `gui` | no | Enable or disable Gazebo GUI | `true` or `false` |

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
  run_rviz:=true

# Run to spawn a mobile manipulator variant with a specific arm
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py \
  robot:=rbkairos \
  robot_model:=rbkairos_plus \
  arm_type:=ur10e \
  run_rviz:=true
```

#### Advanced

```bash
# Run after Gazebo is active to spawn any supported robot configuration
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py \
  robot_id:=<unique_name> \
  robot:=<robot_type> \
  robot_model:=<robot_model> \
  arm_type:=<ur_model> \
  x:=<m> y:=<m> z:=<m> \
  run_rviz:=<true|false> \
  rviz_config:=<path/to/config.rviz>
```

#### Parameters

| Name | Required | Purpose | Example |
|---|---|---|---|
| `robot_id` | no | Instance name and ROS namespace for the spawned robot | `robot_a` |
| `robot` | no | Robot type to spawn; default is `rbwatcher` | `rbwatcher` |
| `robot_model` | no | Concrete model or variant; defaults to `robot` | `rbwatcher` |
| `frame_prefix` | no | TF frame prefix; defaults to `<robot_id>_` | `robot_a_` |
| `robot_xacro_path` | no | Full path to a custom robot XACRO | `/path/to/robot.urdf.xacro` |
| `x` `y` `z` | no | Spawn position in meters | `0.0 0.0 0.0` |
| `arm_type` | no | Arm type forwarded to the robot xacro as `ur_type` | `ur10e` |
| `run_rviz` | no | Launch RViz2 with a predefined Gazebo simulation config | `true` |
| `rviz_config` | no | Full path to a custom RViz2 config; overrides the default | `/path/to/custom_config.rviz` |
| `use_sim_time` | no | Use simulation time | `true` |
| `low_performance_simulation` | no | Enable lower-performance simulation options where supported | `false` |

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

Description package is [robotnik_description](https://github.com/RobotnikAutomation/robotnik_description), which contains all robot types and models. The distinction is:

- **Robot type**: Category such as `rbwatcher`, `summit_xl`. See the package `robots/` folder for available types. [List of supported robots](https://github.com/RobotnikAutomation/robotnik_description/tree/jazzy-devel/robots).
- **Robot model**: Concrete variant inside a type. If `robot_model` is not provided, it defaults to the selected `robot` value. See the package `robots/<robot>/models/` folder for available models. [Example models for rbwatcher](https://github.com/RobotnikAutomation/robotnik_description/tree/jazzy-devel/robots/rbwatcher).

#### Notes

- Use a unique `robot_id` when spawning multiple robots in the same world to avoid name conflicts in topics and frames.
- `rbcar` spawns the `ros2_control` Ackermann controller, so its velocity commands use `geometry_msgs/msg/TwistStamped`.
- For additional launch variants, GPU-specific notes and troubleshooting guidance, see [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md).
- If Gazebo server processes or ROS 2 control nodes remain after closing a simulation, see [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md#gazebo-server-remains-alive-after-closing-the-simulation).

## Control the robot

After spawning the robot, you can control it using command velocity messages. The two main topics for controlling the robot are:

- `/<robot-id>/robotnik_base_control/cmd_vel`: This topic is used to send velocity commands to the robot. The messages should be of type `geometry_msgs/msg/TwistStamped`.
- `/<robot-id>/robotnik_base_control/cmd_vel_unstamped`: This topic is used to send velocity commands without a timestamp. The messages should be of type `geometry_msgs/msg/Twist`.

The simulation includes an RViz teleoperation panel by default. Once the robot is spawned and RViz is open, you can use the `Teleop` panel shown in the interface to send velocity commands directly to the robot.

The panel is already configured in the provided RViz layouts and publishes to the robot command topic. If you use a different `robot_id` or namespace, update the panel topic accordingly.

As an optional alternative, you can also control the robot from the keyboard with `teleop_twist_keyboard`:

```bash
# Run in another terminal after the robot is already spawned
sudo apt install ros-jazzy-teleop-twist-keyboard

ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -r cmd_vel:=/robot/robotnik_base_control/cmd_vel_unstamped \
  -p stamped:=false
```

Replace `/robot/robotnik_base_control/cmd_vel_unstamped` with the correct namespace for the `robot_id` you used when spawning the robot.

> **Important**: if multiple teleoperation or navigation sources are active at the same time, they can still interfere with each other because they publish to the same command topic.

## MoveIt compatibility

It is possible to use [MoveIt](https://moveit.picknik.ai/main/index.html) to control robotic arms mounted on supported platforms.

> **Important**: MoveIt support currently works correctly only with `robot_id:=robot`. If a different `robot_id` is used, interaction with `move_group` from RViz2 is not supported.

MoveIt can be launched in two ways:

1. From `robotnik_simulation_bringup` using `run_moveit:=true`
2. Independently from `robotnik_simulation_moveit`

Example from bringup:

```bash
# Run after the simulation is active if you want integrated MoveIt bringup
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py \
  robot:=rbkairos \
  robot_model:=rbkairos_plus \
  arm_type:=ur10e \
  run_moveit:=true \
  use_rviz:=true
```

Example standalone:

```bash
# Run after the robot and controllers are already running in simulation
ros2 launch robotnik_simulation_moveit moveit.launch.py \
  robot_id:=robot \
  robot:=rbkairos \
  robot_model:=rbkairos_plus \
  arm_type:=ur10e \
  moveit_config_name:=rbkairos_moveit_config \
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
  moveit_config_name:=rbkairos_moveit_config \
  run_moveit_rviz:=true
```

![moveit_rviz](../docs/assets/img/moveit-rviz.png)

Currently documented mobile manipulation platforms:

- `rbkairos`
- `rbrobout` including lift variants
- `rbtheron`
- `rbvogui`
- `rbfiqus` bi-arm setup (WIP)

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
  robot_xacro_path:=/path/to/your_robot.urdf.xacro
```

### Custom control configuration

The package includes control profiles under `robotnik_gazebo_ignition/config/profile`. These profiles can be used to adjust topics, frames, velocities and controller settings for different Robotnik robots.

## Docker

The full development Docker workflow is documented in [`../docker/README.md`](../docker/README.md).

Use that guide for:

- running the published image or building an image that copies only this repository from the local machine and pulls any extra required repositories from [`../dependencies/repos/robotnik_simulation.jazzy.repos`](../dependencies/repos/robotnik_simulation.jazzy.repos)
- editing the runtime configuration in [`../env/robot.env`](../env/robot.env)
- opening a second terminal with `docker exec` to interact with the running simulation inside the runtime container
- GPU-enabled Docker sessions
- cleanup and reset commands
- notes about the future release-oriented Docker image workflow


## Related documentation

- Conceptual ROS 2 + Gazebo guide: [`../docs/ros2-gazebo-compatibility.md`](../docs/ros2-gazebo-compatibility.md)
- Integrated simulation bringup: [`../common/robotnik_simulation_bringup/README.md`](../common/robotnik_simulation_bringup/README.md)
- Standalone MoveIt flow: [`../common/robotnik_simulation_moveit/README.md`](../common/robotnik_simulation_moveit/README.md)
- GPU notes and troubleshooting: [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
