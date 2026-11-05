# MoveIt for Robotnik simulation

This package starts MoveIt for a robot already spawned with matching controllers.
It can also be included by [bringup](../robotnik_simulation_bringup/README.md)
using `run_moveit:=true`.

## Launch

For an existing Kairos+ simulation:

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_simulation_moveit moveit.launch.py \
  robot:=rbkairos robot_model:=rbkairos_plus
```

RViz is enabled by default. To start only the planning stack:

```bash
ros2 launch robotnik_simulation_moveit moveit.launch.py \
  robot:=rbkairos robot_model:=rbkairos_plus run_moveit_rviz:=false
```

To start simulation and manipulation together, rather than adding a second
bringup to an existing simulation:

```bash
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py \
  robot:=rbkairos robot_model:=rbkairos_plus run_moveit:=true
```

Bringup passes robot identity, description and clock arguments. It does not
expose or forward MoveIt's RViz options; the module uses its own defaults.

## Arguments of moveit.launch.py

| Argument | Default | Effect |
|---|---|---|
| `robot_id` | `robot` | Same robot instance as the simulation |
| `robot` | `rbkairos` | Robot family directory |
| `robot_model` | `rbkairos_plus` | Exact variant used for the SRDF |
| `robot_xacro_path` | `robotnik_description/robots/<robot>/<robot_model>.urdf.xacro` | Description override |
| `arm_type` | `ur10e` | Xacro `ur_type` |
| `frame_prefix` | `<robot_id>_` | Same frame/joint prefix as the spawned robot |
| `use_sim_time` | `true` | Use the simulation clock |
| `run_moveit_rviz` | `true` | Open the manipulation view |
| `moveit_rviz_config` | Empty | RViz path override; empty selects `config/moveit.rviz` in this package |
| `use_fixed_frame` | `false` | Override the RViz frame with `<frame_prefix>odom` |

For another family, specify both `robot` and `robot_model`: changing `robot`
alone does not replace the fixed standalone default `rbkairos_plus`.

## Launch structure

| Entry | Purpose | Arguments |
|---|---|---|
| `moveit.launch.py` | Include move_group and optional RViz | All ten above |
| `move_group.launch.py` | Planning node | First seven above |
| `moveit_rviz.launch.py` | RViz only, for an existing planning session | First seven plus `moveit_rviz_config` and `use_fixed_frame` |

The separate RViz launch is still present. Opening it alone does not start
move_group, controllers or the simulator.

## Profiles and generic RViz

The supported profile pairs are:

| `robot` | `robot_model` | Group in the current SRDF |
|---|---|---|
| `rbkairos` | `rbkairos_plus` | `arm` |
| `rbrobout` | `rbrobout_plus` | `arm_with_lift` |
| `rbtheron` | `rbtheron_plus` | `arm` |
| `rbvogui` | `rbvogui_plus` | `arm` |

SRDF, kinematics, limits, controllers and Pilz configuration remain in
`robotnik_simulation_robots/<robot>/manipulation/`. The URDF is generated from
`robotnik_description` or the explicit description override. Missing profile
files stop the launch; MoveIt never changes the spawned variant automatically.
OMPL, CHOMP and STOMP defaults come from the installed `moveit_configs_utils`.

One generic RViz file serves the four profiles. The RViz launcher reads the
expanded SRDF, selects its sole planning group, leaves selection to the UI when
there are several and reports an error when there are none. An override file
keeps its own group selection. Namespace/frame substitutions, temporary-file
lifetime and the existing RViz-specific kinematics filtering are retained.

The examples use the default instance `robot`. Custom namespace and prefix
substitutions were checked offline; full interactive MoveIt/RViz behavior with
other namespaces has not been verified in this documentation review.

For robot spawning, see [Gazebo](../../robotnik_gazebo_ignition/README.md#spawn-robot).
For integrated deployment, see [bringup](../robotnik_simulation_bringup/README.md).
