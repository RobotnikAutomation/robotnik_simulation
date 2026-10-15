# Robotnik Simulation Bringup
This package provides high-level launch files for complete Robotnik simulation demos.

It is intended to orchestrate several simulation components together:

- Gazebo world and robot spawning
- robot-specific laser filtering when required
- localization
- navigation
- RViz visualization
- optional MoveIt integration for mobile manipulators

For a simple Gazebo-only simulation with one robot, use the launch files in robotnik_gazebo_ignition. This package is intended for full demo bringup flows where navigation, localization or manipulation are required.

![alt text](docs/summit-gz.png)

## Quick start
### Full navigation demo

Launch the default simulation stack (with RBSummit):

```
source ~/ros2_ws/install/setup.bash
ros2 launch  robotnik_simulation_bringup bringup_complete.launch.py
```

Or launch the default simulation with rbwatcher:
```
source ~/ros2_ws/install/setup.bash
ros2 launch  robotnik_simulation_bringup bringup_complete.launch.py robot:=rbwatcher
```

Or launch complete RbKairos simulation with MoveIt enabled:
# Robotnik simulation bringup

This package orchestrates Gazebo, robot spawning, localization, navigation and
optional MoveIt. It delegates each module's nodes and configuration to that module.

## Launch

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py
```

By default, it starts an `rbsummit`, Gazebo GUI, localization and navigation.
MoveIt is disabled. To start only the world and robot:

```bash
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py \
  run_localization:=false run_navigation:=false
```

For a manipulation variant:

```
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py robot:=rbkairos robot_model:=rbkairos_plus robot_xacro_path:=/path/to/robot.urdf.xacro arm_type:=ur10e use_gui:=true use_rviz:=true run_moveit:=true
```

#### Parameters
| Name | Required | Default | Purpose |
```bash
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py \
  robot:=rbkairos robot_model:=rbkairos_plus run_moveit:=true
```

Bringup starts a new world and spawns the robot. To add functionality to an
existing session, use the module's own launch instead of starting bringup again.

## Deployment

All five modules are direct children of `bringup_complete.launch.py`:

| Module | Entry | Started when | Delay |
|---|---|---|---|
| `robot_id` | no | `robot` | Name for launch and config resources |
| `robot` | no | `rbsummit` | Robot base type used to resolve defaults |
| `robot_model` | no |  value of 'robot' | Name of the robot model |
| `robot_xacro_path` | no | resolved from `robot` and `robot_model` | Path to robot URDF/XACRO (forwarded to spawn and MoveIt) |
| `use_gui` | no | `true` | Enable simulation graphical interface |
| `low_performance_simulation` | no | `true` | Enable smooth simulation for low performance computers |
| `use_rviz` | no | `true` | Launch rviz |
| `run_localization` | no | `true` | Launch AMCL |
| `run_navigation` | no | `true` | Launch nav2 |
| `run_moveit` | no | `false` | Launch MoveIt for supported mobile manipulators |
| `run_laser_filters` | no | `true` | Launch laser filters when supported by the selected robot model. |
| `arm_type` | no | `ur10e` | Arm type used for robots with manipulator (forwarded as xacro `ur_type`) |
| `world_path` | no | `/robotnik_gazebo_ignition/worlds/demo.world` | Path of the world file |

## MoveIt

MoveIt can be launched in two modes:

### Integrated in complete bringup:

```
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py robot:=rbkairos robot_model:=rbkairos_plus arm_type:=ur10e run_moveit:=true
```

Integrated in bringup with custom xacro path:

```
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py robot:=rbkairos robot_model:=rbkairos_plus robot_xacro_path:=/path/to/robot.urdf.xacro arm_type:=ur10e run_moveit:=true
```

### Independently from the simulation bringup pipeline (use this after the robot and controllers are already running):

```
ros2 launch robotnik_simulation_moveit moveit.launch.py robot_id:=robot robot:=rbkairos robot_model:=rbkairos_plus moveit_config_name:=rbkairos_moveit_config arm_type:=ur10e run_moveit_rviz:=true
```

Independently with custom xacro path:

```
ros2 launch robotnik_simulation_moveit moveit.launch.py robot_id:=robot robot:=rbkairos robot_model:=rbkairos_plus robot_xacro_path:=/path/to/robot.urdf.xacro moveit_config_name:=rbkairos_moveit_config arm_type:=ur10e run_moveit_rviz:=true
```

### rviz only for visualization:

```
ros2 launch  robotnik_simulation_bringup rviz.launch.py
```

![alt text](docs/summit-rviz.png)

## Create and use a new map

### 1. Launch simulation

For mapping workflows, you can start the simple simulation:

```
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py gui:=true
```

Spawn the robot:

```
ros2 launch robotnik_gazebo_ignition spawn_robot.launch.py \
  robot:=rbsummit run_rviz:=false
```

If required by the selected robot (rbsummit or rbwatcher), launch the laser filters:

```
ros2 launch robotnik_simulation_bringup laser_filters.launch.py
```

### 2. Launch SLAM algorithm (Mapping)

Run mapping:

```
ros2 launch robotnik_simulation_localization localization.launch.py run_mapping:=true
```

Start mapping:

```
ros2 service call /robot/lifecycle_manager_mapping/manage_nodes nav2_msgs/srv/ManageLifecycleNodes "command: 0"
```

Save map:

```
ros2 service call /robot/map_saver/save_map nav2_msgs/srv/SaveMap "map_topic: '/robot/map'
map_url: '/home/robot/maps/demo_map/demo_map'
image_format: 'png'
map_mode: 'trinary'
free_thresh: 0.196
occupied_thresh: 0.65"
```

### 3. Launch Autonomous Navigation with your map

Stop the mapping launch before starting localization:

```
ros2 launch robotnik_simulation_localization localization.launch.py
```

Load map:

```
ros2 service call /robot/map_server/load_map nav2_msgs/srv/LoadMap "map_url: '/home/robot/maps/demo_map/demo_map.yaml'"
```

Run navigation:

```
ros2 launch robotnik_simulation_navigation navigation.launch.py
```

| [Gazebo world](../../robotnik_gazebo_ignition/README.md#spawn-world) | `spawn_world.launch.py` | Always | None |
| [Robot spawn](../../robotnik_gazebo_ignition/README.md#spawn-robot) | `spawn_robot.launch.py` | Always | None |
| [Localization](../robotnik_simulation_localization/README.md) | `localization.launch.py` | `run_localization=true` and family profile available | 10 s |
| [Navigation](../robotnik_simulation_navigation/README.md) | `navigation.launch.py` | `run_navigation=true` and family profile available | 15 s |
| [MoveIt](../robotnik_simulation_moveit/README.md) | `moveit.launch.py` | `run_moveit=true` | 25 s |

Missing localization/navigation profiles produce a warning and the module is
skipped. Localization and navigation are independently selectable. Delays are
fixed timers, not readiness checks or guarantees that dependencies are active.

Bringup passes robot identity, description, frame prefix and clock explicitly
to the children that consume them. Their configuration scopes are isolated;
the enclosing ROS namespace and environment are preserved. Child defaults do
not replace the values passed by bringup.

Bringup contains no RViz nodes or configurations. When navigation starts, it
suppresses the basic spawn view. Otherwise `run_spawn_rviz` controls that view.
MoveIt opens its own view independently. Navigation and MoveIt keep their local
RViz defaults and options; bringup does not expose those options. This selection
is made at startup and does not close windows belonging to other sessions.

## Arguments

All 21 arguments are optional:

| Argument | Default | Effect |
|---|---|---|
| `robot_id` | `robot` | Robot instance, Gazebo entity name and ROS namespace |
| `robot` | `rbsummit` | Family directory used to select profiles |
| `robot_model` | Value of `robot` | Variant for description, control, bridge and SRDF selection |
| `robot_xacro_path` | `robotnik_description/robots/<robot>/<robot_model>.urdf.xacro` | Description override passed to spawn and MoveIt |
| `frame_prefix` | `<robot_id>_` | Prefix for TF frames and joints |
| `arm_type` | `ur10e` | Arm type passed to spawn and MoveIt |
| `use_sim_time` | `true` | Clock selection passed to the modules |
| `run_gazebo_gui` | `true` | Forward GUI activation to spawn_world |
| `use_nvidia_gpu` | `false` | Forward [rendering selection](../../robotnik_gazebo_ignition/README.md#nvidia-prime-rendering) to spawn_world |
| `run_localization` | `true` | Request localization |
| `run_navigation` | `true` | Request navigation |
| `run_moveit` | `false` | Request MoveIt for a matching manipulation variant |
| `run_spawn_rviz` | `true` | Request the basic view when navigation is not started |
| `spawn_rviz_config` | Empty | Basic RViz override passed to spawn; empty selects its default |
| `low_performance_simulation` | `true` | Sensor simulation settings passed to spawn |
| `world` | `demo` | Built-in world name passed to spawn_world |
| `world_path` | `robotnik_gazebo_ignition/worlds/<world>.world` | Override the world selected by name |
| `x` | `0.0` | Initial robot X coordinate, in metres |
| `y` | `0.0` | Initial robot Y coordinate, in metres |
| `z` | `0.0` | Initial robot Z coordinate, in metres |
| `run_mapping` | `false` | Forward the mode to localization; see its [mapping workflow](../robotnik_simulation_localization/README.md#mapping-with-the-current-launch-behavior) |

Description overrides do not replace the control, bridge or manipulation
profiles selected by family and variant. See the
[profile guide](../robotnik_simulation_robots/README.md).

For environment-based startup, use the [Docker guide](../../docker/README.md).
For the complete argument propagation map, see the
[configuration audit](../../docs/configuration-audit/README.md).
