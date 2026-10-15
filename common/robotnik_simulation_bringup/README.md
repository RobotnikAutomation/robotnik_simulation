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
