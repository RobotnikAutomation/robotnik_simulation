# Robotnik Simulation Bringup

This package orchestrates Gazebo, robot spawning, localization, navigation and
optional MoveIt. It delegates each module's nodes and configuration to that module.

![Gazebo simulation](docs/summit-gz.png)

## Quick start

Start the default navigation demo:

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

To run the navigation demo with RB-Watcher:

```bash
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py robot:=rbwatcher
```

For a manipulation variant, start a new simulation with MoveIt enabled:

```bash
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py \
  robot:=rbkairos robot_model:=rbkairos_plus run_moveit:=true
```

Bringup starts a new world by default. Set `run_world:=false` to spawn another
robot with its full stack in an existing world. To add a module to a robot
already spawned, use that module's own launch instead of spawning the robot again.

## Multiple robots in one world

Start the world and its `/clock` bridge once, in a separate terminal:

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py world:=demo use_nvidia_gpu:=true
```

Then start each robot's stack in its own terminal. For example, RB-Vogui+:

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py \
  run_world:=false robot_id:=robot_1 robot:=rbvogui robot_model:=rbvogui_plus \
  run_moveit:=true x:=0.0 y:=0.0
```

And RB-Kairos+, with its own localization, navigation and manipulation profiles:

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py \
  run_world:=false robot_id:=robot_2 robot:=rbkairos robot_model:=rbkairos_plus \
  run_moveit:=true x:=2.0 y:=0.0
```

Both robot stacks retain the same module options as a normal bringup. Their
namespaces are `/robot_1` and `/robot_2`, and their frame/joint prefixes default
to `robot_1_` and `robot_2_`. Use distinct robot IDs, prefixes and spawn positions.
Use the same ROS domain and Gazebo transport partition for the world and robots.
The spawner discovers the running world; this workflow assumes a single world
is active in that Gazebo transport partition.

Keep the world terminal running while either robot is in use. Robot-only bringup
does not start another Gazebo server, GUI or clock bridge. World path, GUI and
GPU options have no effect when `run_world=false`; set them on the world launch.
Closing a robot-only launch stops its ROS processes, but does not delete its
Gazebo entity. Removing the model or restarting the world is a separate action.

Alternatively, let the first robot's bringup start the world with the default
`run_world=true`, and set `run_world=false` for subsequent robots. In that case,
the shared world belongs to the first launch, so keep that launch running.

Spawn coordinates do not override the initial pose in AMCL's robot profile.
Set each robot's initial map pose in its navigation RViz using **2D Pose Estimate**
to match its spawn position, or configure the corresponding localization profile.

## Deployment

All five modules are direct children of `bringup_complete.launch.py`:

| Module | Entry | Started when | Delay |
|---|---|---|---|
| [Gazebo world](../../robotnik_gazebo_ignition/README.md#spawn-world) | `spawn_world.launch.py` | `run_world=true` | None |
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

The localization module owns scan preparation, including pointcloud-to-laserscan
conversion or laser merging selected by the robot profile. It replaces the old
bringup `laser_filters.launch.py` workflow; there is no `run_laser_filters`
argument in this launch.

## Visualization

Bringup contains no RViz nodes or configurations. When navigation starts, it
suppresses the basic spawn view. Otherwise `run_spawn_rviz` controls that view.
MoveIt opens its own view independently. Navigation and MoveIt keep their local
RViz defaults and options; bringup does not expose those options. This selection
is made at startup and does not close windows belonging to other sessions.

![Navigation RViz](docs/summit-rviz.png)

## Arguments

All 22 arguments are optional:

| Argument | Default | Effect |
|---|---|---|
| `robot_id` | `robot` | Robot instance, Gazebo entity name and ROS namespace |
| `robot` | `rbsummit` | Family directory used to select profiles |
| `robot_model` | Value of `robot` | Variant for description, control, bridge and SRDF selection |
| `robot_xacro_path` | `robotnik_description/robots/<robot>/<robot_model>.urdf.xacro` | Description override passed to spawn and MoveIt |
| `frame_prefix` | `<robot_id>_` | Prefix for TF frames and joints |
| `arm_type` | `ur10e` | Arm type passed to spawn and MoveIt |
| `use_sim_time` | `true` | Clock selection passed to the modules |
| `run_world` | `true` | Start Gazebo and `/clock`; false reuses an existing world |
| `run_gazebo_gui` | `true` | Forward GUI activation when starting the world |
| `use_nvidia_gpu` | `false` | Forward [rendering selection](../../robotnik_gazebo_ignition/README.md#nvidia-prime-rendering) when starting the world |
| `run_localization` | `true` | Request localization |
| `run_navigation` | `true` | Request navigation |
| `run_moveit` | `false` | Request MoveIt for a matching manipulation variant |
| `run_spawn_rviz` | `true` | Request the basic view when navigation is not started |
| `spawn_rviz_config` | Empty | Basic RViz override passed to spawn; empty selects its default |
| `low_performance_simulation` | `true` | Sensor simulation settings passed to spawn |
| `world` | `demo` | Built-in world name used when `run_world=true` |
| `world_path` | `robotnik_gazebo_ignition/worlds/<world>.world` | Override the world file when `run_world=true` |
| `x` | `0.0` | Initial robot X coordinate, in metres |
| `y` | `0.0` | Initial robot Y coordinate, in metres |
| `z` | `0.0` | Initial robot Z coordinate, in metres |
| `run_mapping` | `false` | Forward the mode to localization; see its [mapping workflow](../robotnik_simulation_localization/README.md#mapping-with-the-current-launch-behavior) |

Description overrides do not replace the control, bridge or manipulation
profiles selected by family and variant. See the
[profile guide](../robotnik_simulation_robots/README.md).

## Mapping and manipulation

For scan preparation, SLAM activation, map saving and loading a map for AMCL,
follow the [localization guide](../robotnik_simulation_localization/README.md#mapping-with-the-current-launch-behavior).
The mapping branch currently requires the scan pipeline to be started separately
and its lifecycle manager to be activated, including when selected by bringup.

For a running robot with matching manipulation controllers, start MoveIt in a
separate terminal:

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_simulation_moveit moveit.launch.py \
  robot:=rbkairos robot_model:=rbkairos_plus arm_type:=ur10e
```

Use the same robot instance, description, arm type and frame prefix as the
simulation. See the [MoveIt guide](../robotnik_simulation_moveit/README.md) for
standalone launch arguments and visualization options, and the
[navigation guide](../robotnik_simulation_navigation/README.md) for a running
simulation with localization already active.

For environment-based startup, use the [Docker guide](../../docker/README.md).
