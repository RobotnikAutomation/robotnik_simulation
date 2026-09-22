# Robotnik Gazebo Ignition

<img src="../docs/assets/img/ignition_simulation_view.png" alt="Robotnik Gazebo Ignition Simulation View" height=300>

This package provides Gazebo Ignition plugins and resources for Robotnik robots.

## 📥 Installation

1. Setup sources and keys for Gazebo packages:
```sh
sudo apt update
sudo apt-get install curl lsb-release gnupg
sudo curl https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null
```

2. Install Gazebo Harmonic.
```sh
sudo apt-get update
sudo apt-get install gz-harmonic
```

3. Install ROS 2 Jazzy and ROS-GZ bridge and manipulation dependencies.
```sh
sudo apt install -y ros-jazzy-ros-gz ros-$ROS_DISTRO-moveit* ros-$ROS_DISTRO-chomp-motion-planner* ros-$ROS_DISTRO-kdl* ros-$ROS_DISTRO-joint-trajectory-controller* ros-$ROS_DISTRO-ompl* ros-$ROS_DISTRO-pick-ik* ros-$ROS_DISTRO-pilz-industrial-motion-planner* ros-$ROS_DISTRO-trac-ik* ros-$ROS_DISTRO-stomp* ros-$ROS_DISTRO-spacenav* ros-$ROS_DISTRO-warehouse-ros-sqlite* ros-$ROS_DISTRO-ros2-control ros-$ROS_DISTRO-moveit-configs-utils
```

4. Set up workspace and install dependencies:

```sh
# Workspace
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws

# Robotnik and related packages (ROS 2 Jazzy)
vcs import --input https://raw.githubusercontent.com/RobotnikAutomation/robotnik_simulation/jazzy-devel/robotnik_simulation.jazzy.repos src/

# Install prebuilt simulation debs from this repo (run at repo root)
cd ~/ros2_ws/src/robotnik/robotnik_simulation
sudo apt-get install -y ./debs/ros-${ROS_DISTRO}-*.deb

# Resolve dependencies
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
rosdep update
rosdep install --from-paths src --ignore-src -r -y
```

5. Build the workspace:

```sh
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

## 🚀 Usage

To use the simulation, you need to spawn a world and then spawn at least one robot. Continue reading for instructions.

### 🗺️ Spawn World

First step to use this simulation is launch world where the robot will be spawned. For example, to launch the `empty` world, use the following command:

#### Basic
```bash
# Basic
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py world:=empty

# With GUI disabled
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py world:=empty gui:=false
```

#### Advanced
```bash
# Generic pattern
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py world:=<world_name> gui:=<true|false>
```

#### Parameters
| Name | Required | Purpose | Example |
|---|---|---|---|
| `world` | no | Name of the world file (without the `.world` extension) | `empty` |
| `world_path` | no | Full path to a custom world file (overrides `world` parameter) | `/path/to/custom_world.sdf` |
| `gui` | no | Enable or disable Gazebo GUI | `true` or `false` |

#### Supported Worlds

| Name | Description | Thumbnail |
|------|-------------|-----------|
| `empty` | An empty world with a flat ground plane | <img src="../docs/assets/world/empty.png" alt="empty_world" height=100> |
| `demo` | A demo world with obstacles and ramps for testing robot navigation | <img src="../docs/assets/world/demo.png" alt="demo_world" height=100> |
| `ionic` | Demo world from Gazebo to show ionic simulation features | <img src="../docs/assets/world/ionic.png" alt="ionic_world" height=100> |
| `lightweight_scene` | A lightweight scene for performance testing | <img src="../docs/assets/world/lightweight_scene.png" alt="lightweight_scene_world" height=100> |


### 🤖 Spawn Robot

Use the launch file to insert a robot into the Gazebo (Ignition) world.

#### Basic
```bash
# Basic RB-Watcher
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py robot:=rbwatcher

# Specific ID and pose
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py robot_id:=robot_a robot:=rbwatcher robot_model:=rbwatcher x:=0.0 y:=0.0 z:=0.0 run_rviz:=true

# Mobile manipulator selecting arm type
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py robot:=rbkairos robot_model:=rbkairos_plus arm_type:=ur10e run_rviz:=true
```

#### Advanced
```bash
# Generic pattern
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py robot_id:=<unique_name> robot:=<robot_type> robot_model:=<robot_model> arm_type:=<ur_model> x:=<m> y:=<m> z:=<m> has_arm:=<true/false> run_rviz:=<true/false> rviz_config:=<path/to/config.rviz>
```

#### Parameters
| Name | Required | Purpose | Example |
|---|---|---|---|
| `robot_id` | no | Instance name for the spawned robot | `robot_a` |
| `robot` | no | Robot **type** to spawn, see `supported_robots`, default is `rbwatcher` | `rbwatcher` |
| `robot_model` | no | Specific **model** within the type, see `supported_robots` | `rbwatcher` |
| `x` `y` `z` | no | Spawn position in meters | `0.0 0.0 0.0` |
| `run_rviz` | no | Launch RViz2 with a predefined configuration | `true` or `false` |
| `rviz_config` | no | Full path to a custom navigation RViz2 configuration file (overrides default config and fixed frame must be set in config) | `/path/to/custom_config.rviz` |
| `has_arm` | no | Flag stating if platform should be spawned with robotic arm | `true` or `false` |
| `arm_type` | no | Arm type forwarded to robot xacro as `ur_type` for manipulator variants | `ur10e` |

#### Supported Robots

| robot          | robot_model options     | Notes |
| -------------- | ----------------------- | --- |
| rbwatcher      | rbwatcher               | Supported |
| rb1            | rb1                     | Limited |
| rbfiqus        | rbfiqus                 | Limited |
| rbkairos       | rbkairos, rbkairos_plus | Limited |
| rbrobout       | rbrobout, rbrobout_plus | Limited |
| rbsummit       | rbsummit                | Limited |
| rbsummit_steel | rbsummit_steel          | Limited |
| rbtheron       | rbtheron, rbtheron_plus | Limited |
| rbvogui        | rbvogui, rbvogui_plus   | Limited |
| rbvogui_xl     | rbvogui_xl              | Limited |

Note: "not well tested" means that the robot has been integrated but may require further validation and adjustments to ensure optimal performance in the simulation environment.

#### Types vs. models
Description package is [robotnik_description](https://github.com/RobotnikAutomation/robotnik_description), which contains all robot types and models. The distinction is:
- **Robot type**: Category such as `rbwatcher`, `summit_xl`. See the package `robots/` folder for available types. [List of supported robots](https://github.com/RobotnikAutomation/robotnik_description/tree/jazzy-devel/robots).
- **Robot model**: Concrete variant inside a type. If omitted, the default model for that type is used. See the package `robots/<robot>/models/` folder for available models. [Example models for rbwatcher](https://github.com/RobotnikAutomation/robotnik_description/tree/jazzy-devel/robots/rbwatcher).

#### Notes
- Use a unique `robot_id` when spawning multiple robots in the same world to avoid name conflicts in topics and frames.

## 🎮 Control the Robot

After spawning the robot, you can control it using command velocity messages. The two main topics for controlling the robot are:
- `/<robot-id>/robotnik_base_control/cmd_vel`: This topic is used to send velocity commands to the robot. The messages should be of type `geometry_msgs/msg/TwistStamped`.
- `/<robot-id>/robotnik_base_control/cmd_vel_unstamped`: This topic is used to send velocity commands without a timestamp. The messages should be of type `geometry_msgs/msg/Twist`.


To control the robot, you can use teleoperation packages such as `teleop_twist_keyboard` or `teleop_twist_joy`. For example, to control the robot using the keyboard, run:

```bash
sudo apt install ros-jazzy-teleop-twist-keyboard

ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/robot/robotnik_base_control/cmd_vel -p stamped:=true
```

Make sure to replace `/robot/robotnik_base_control/cmd_vel` with the appropriate topic name based on the `robot_id` you used when spawning the robot.

Also, you can use RViz plugin on the bottom right to control the robot by clicking on the arrows.

To teleoperate the arm you need to run simulation with MoveIt (currently supported only centauro_rbvogui_plus) and when it is loaded switch controllers:

```bash
ros2 service call /robot/controller_manager/switch_controller controller_manager_msgs/srv/SwitchController "{activate_controllers: {joint_trajectory_controller}, deactivate_controllers: {forward_position_controller, velocity_controller}}"

ros2 service call /robot/controller_manager/switch_controller controller_manager_msgs/srv/SwitchController "{activate_controllers: {forward_position_controller}, deactivate_controllers: {joint_trajectory_controller, velocity_controller}}"
```

Afterwards you can run application that allows to teleoperate arm with keyboard:

```bash
ros2 run robotnik_servo_keyboard_input servo_keyboard_input
```

## 🦾 MoveIt compatibility

It is possible to use [MoveIt](https://moveit.picknik.ai/main/index.html) to control robotic arms mounted on supported platforms.

Warning!!! MoveIt support works correctly only with `robot_id:=robot`. If different robot_id will be used, then it is not possible to interact with move_group from Rviz2.

You can launch MoveIt in two ways:
1. From bringup, using `robotnik_simulation_bringup` with `run_moveit:=true`.
2. Independently, using `robotnik_simulation_moveit`.

Example launch from bringup:

```bash
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py robot:=rbkairos robot_model:=centauro_rbkairos_plus arm_type:=ur10e run_moveit:=true use_rviz:=true world_path:=<path_to_workspace>/src/robotnik/robotnik_simulation/robotnik_gazebo_ignition/worlds/centauro_capot.world

ros2 launch robotnik_simulation_bringup bringup_complete.launch.py robot:=rbrobout robot_model:=centauro_rbrobout_plus arm_type:=ur20 run_moveit:=true use_rviz:=true world_path:=<path_to_workspace>/src/robotnik/robotnik_simulation/robotnik_gazebo_ignition/worlds/centauro_muro.world

ros2 launch robotnik_simulation_bringup bringup_complete.launch.py robot:=rbvogui robot_model:=centauro_rbvogui_plus arm_type:=ur5e run_moveit:=true use_rviz:=true world_path:=<path_to_workspace>/src/robotnik/robotnik_simulation/robotnik_gazebo_ignition/worlds/centauro_muro.world
```

On the beginning both controllers (velocity_controller and joint_trajectory_controller) are loaded, to switch between them use:
```bash
ros2 service call /robot/controller_manager/switch_controller controller_manager_msgs/srv/SwitchController "{activate_controllers: {velocity_controller}, deactivate_controllers: {joint_trajectory_controller}}"

ros2 service call /robot/controller_manager/switch_controller controller_manager_msgs/srv/SwitchController "{activate_controllers: {joint_trajectory_controller}, deactivate_controllers: {velocity_controller}}"
```

Example independent launch:

```bash
ros2 launch robotnik_simulation_moveit moveit.launch.py robot_id:=robot robot:=rbkairos robot_model:=rbkairos_plus arm_type:=ur10e moveit_config_name:=rbkairos_moveit_config run_moveit_rviz:=true
```

Example independent launch with custom `robot_xacro_path`:

```bash
ros2 launch robotnik_simulation_moveit moveit.launch.py robot_id:=robot robot:=rbkairos robot_model:=rbkairos_plus robot_xacro_path:=/path/to/robot.urdf.xacro arm_type:=ur10e moveit_config_name:=rbkairos_moveit_config run_moveit_rviz:=true
```

![moveit_rviz](../docs/assets/img/moveit-rviz.png)

Robots with mobile manipulation available right now:
 - rbkairos
 - rbrobout (additionally available lift)
 - rbtheron
 - rbvogui
 - rbfiqus (bi arm setup)(WIP)

## 🎉 Enjoy

Example of RBVogui executing docking procedure in Gazebo Ignition. Currently, only for demonstration purposes, no docking controller is provided.

![rbvogui_gif](../docs/assets/img/RBVogui_Docking.gif)

## Customization

### Edit robot model

Specific robot models can be customized by creating your own URDF/XACRO files based on the existing ones in the `robotnik_description` package.

1. Copy the existing robot folder from `robotnik_description/robots/<robot>/` to a new folder, e.g., `robotnik_description/robots/my_robot/`.
2. Modify the URDF/XACRO files in the new folder to add or change components as needed.
3. Update any necessary configuration files for sensors, arms, or other components.
4. Spawn the customized robot using the `robot_xacro_path` parameter:

```sh
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py robot:=rbkairos robot_model:=rbkairos_plus arm_type:=ur10e
```

With custom `robot_xacro_path`:

```sh
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py robot_xacro_path:=<your_robot.urdf.xacro>
```

### Custom control configuration

Inside the simulation package `robotnik_gazebo_ignition/config/profile`, you can find different control profiles for various Robotnik robots. You can adjust topics, frames, velocities, and controllers there.

## 🐳 Docker
🚧 Work in progress. 🚧

Use the compose file in the repo root to run a preconfigured simulator container.

```sh
docker compose up
```

> **Note**: The first time will take a while as it builds the image. Subsequent runs will be faster.
