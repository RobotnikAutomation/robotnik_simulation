# Robotnik simulation navigation

This package starts Nav2 for an existing simulation/localization session and
owns its navigation RViz. [Bringup](../robotnik_simulation_bringup/README.md)
includes it by default when the selected family has a complete navigation profile.

## Standalone launch

With a world, robot, map and the required transforms already available:

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_simulation_navigation navigation.launch.py robot:=rbsummit
```

Use the same instance, family, frame prefix and clock as the running robot.
Localization is a separate module; navigation does not start AMCL or SLAM and
has no odometry-only fallback. See the
[localization guide](../robotnik_simulation_localization/README.md).

RViz is true by default. To run this module without its window:

```bash
ros2 launch robotnik_simulation_navigation navigation.launch.py \
  robot:=rbsummit run_navigation_rviz:=false
```

If navigation is already running through bringup, do not start a second copy.
Bringup uses this module's visual defaults and does not expose its RViz options.

## Arguments of navigation.launch.py

All six arguments are optional:

| Argument | Default | Effect |
|---|---|---|
| `robot_id` | `robot` | Namespace of Nav2 and navigation RViz |
| `robot` | Empty | Family profile; empty selects this package's generic configuration |
| `frame_prefix` | `<robot_id>_` | Prefix used in frame parameters and the RViz configuration |
| `use_sim_time` | `true` | Clock for Nav2 nodes, costmaps and RViz |
| `run_navigation_rviz` | `true` | Open the navigation view |
| `navigation_rviz_config` | Empty | RViz override; empty selects `config/navigation.rviz` |

Both `nav2_task.launch.py` and `nav2_mission.launch.py` accept the first four
arguments with the same defaults. Each leaf applies the robot namespace itself;
the parent does not add it twice. These leaves do not open RViz.

## Configuration and execution

A nonempty `robot` selects files in
`robotnik_simulation_robots/<robot>/navigation/`. Files replace the generic
configuration rather than overlaying it. Launch substitutions resolve instance,
frame prefix and clock; local and global costmaps receive the clock explicitly.

| Launch | Nodes |
|---|---|
| `nav2_task.launch.py` | Controller, planner, behavior, smoother, BT Navigator and lifecycle manager |
| `nav2_mission.launch.py` | Waypoint follower and its lifecycle manager |
| `navigation.launch.py` | Both leaves and optional navigation RViz |

The task lifecycle manager has autostart true. The mission lifecycle manager has
autostart false. Its `route_server` action is currently excluded, although
`route_server.yaml` is still required by the configuration path and bringup
profile check. Having a route YAML does not enable routing.

The BT XML files and route graph path remain selected by the launch. The scan
pipeline must publish the topic configured for the costmaps. Changing only the
scan output in the localization profile does not update its consumers.

## RViz

The package configuration resolves `robot_id` and `frame_prefix` before RViz
starts. Starting navigation from a separate terminal does not close a basic
RViz that was already running. Bringup suppresses the basic view when it starts
navigation in the same invocation.

The display tree is organized into groups:

- `Robot`: robot model and TF, alongside the grid at the root.
- `Sensors`: standard front/rear laser scans, top point cloud and front camera,
  all disabled initially. Enable the sensors fitted to your robot and adjust
  their topics if needed.
- `Navigation`: `Map`, `Costmaps` (global and local), and `Paths` (global in
  green, local in blue).
- `Localization`: the processed `localization/scan`, the AMCL pose with
  covariance (`amcl_pose`), and optional AMCL particles (`particle_cloud`,
  disabled initially). When using SLAM, disable the AMCL displays.

The navigation view uses the prefixed `map` frame. Sensor, navigation and
localization display topics are relative to the robot namespace. The standard
sensor examples use Best Effort reliability, and the robot description uses
Transient Local durability so the model can load when RViz starts after the
state publisher. The basic view provides the same `Robot` and `Sensors` groups
in the prefixed `odom` frame.

For family availability, see [robot profiles](../robotnik_simulation_robots/README.md).
For the include hierarchy, see the [configuration map](../../docs/configuration-audit/README.md).
