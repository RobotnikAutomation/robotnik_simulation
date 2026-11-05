# Robotnik simulation localization

This package prepares a localization scan and starts either AMCL with a map
server or SLAM Toolbox for an existing simulation. It does not start Gazebo,
navigation or RViz. [Bringup](../robotnik_simulation_bringup/README.md) requests
localization by default when the selected family has its required profile files.

## AMCL for a running robot

Source the workspace in every terminal and match the running robot's arguments:

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch robotnik_simulation_localization localization.launch.py robot:=rbsummit
```

The default AMCL branch starts both `localization_scan.launch.py` and
`localization_2d.launch.py`; do not launch a duplicate scan pipeline. Its
lifecycle manager has autostart true. The map server initially loads the packaged
demo map. To load another map after activation:

```bash
ros2 service call /robot/map_server/load_map nav2_msgs/srv/LoadMap \
  "{map_url: '/absolute/path/to/map.yaml'}"
```

Replace `/robot` with the selected instance. Navigation is launched separately;
see the [navigation guide](../robotnik_simulation_navigation/README.md).

## Arguments and launch hierarchy

| Argument | Default | Effect |
|---|---|---|
| `robot_id` | `robot` | Namespace for localization nodes and relative topics |
| `robot` | Empty | Family profile; empty selects this package's generic files |
| `frame_prefix` | `<robot_id>_` | Prefix of configured frames |
| `use_sim_time` | `true` | Clock for localization nodes and scan components |
| `run_mapping` | `false` | Select SLAM instead of the AMCL branch |
| `run_scan_pipeline` | `true` | Prepare scans in either mode; false uses an existing publisher |
| `mapping_autostart` | `true` | Activate SLAM and map_saver automatically |

`localization.launch.py` accepts all seven. The leaves
`localization_scan.launch.py`, `localization_2d.launch.py` and
`mapping_2d.launch.py` each accept the first four with the same defaults.
Mapping also accepts `mapping_autostart`.
Bringup passes the family explicitly; its default is `rbsummit`.

```text
localization.launch.py
├── run_scan_pipeline=true → localization_scan.launch.py
├── run_mapping=false → localization_2d.launch.py → AMCL + map server + lifecycle
└── run_mapping=true → mapping_2d.launch.py → SLAM + map saver + lifecycle
```

A family profile is selected from
`robotnik_simulation_robots/<robot>/localization/`. It replaces the corresponding
generic files; no partial merge is applied. The plain `localization_scan.yaml`
schema selects pointcloud conversion, passthrough relay or dual-laser merge.
It is read directly by Python and does not expand arbitrary launch substitutions.

Its `target_frame` is a suffix to which the launch adds `frame_prefix`. Changing
its output topic requires matching changes in AMCL, SLAM and costmap consumers.
See the [profile guide](../robotnik_simulation_robots/README.md).

## Mapping

For a complete simulation with mapping and navigation:

```bash
ros2 launch robotnik_simulation_bringup bringup_complete.launch.py \
  robot:=rbsummit run_mapping:=true
```

For an already spawned robot, start mapping independently:

```bash
ros2 launch robotnik_simulation_localization localization.launch.py \
  robot:=rbsummit run_mapping:=true
```

Both paths prepare scans and activate SLAM and map_saver automatically. Do not
start another scan pipeline. Pass `run_scan_pipeline:=false` if a publisher is
already supplying `localization/scan` in this robot's namespace.

For manual lifecycle activation, start with `mapping_autostart:=false`, then:

```bash
ros2 service call /robot/lifecycle_manager_mapping/manage_nodes \
  nav2_msgs/srv/ManageLifecycleNodes "{command: 0}"
```

When combining standalone localization and navigation, let localization own the
pipeline and pass `run_scan_pipeline:=false` to navigation. Direct leaf launches
such as `mapping_2d.launch.py` do not prepare scans themselves.

## Saving a map

After activation, save to an existing writable directory:

```bash
ros2 service call /robot/map_saver/save_map nav2_msgs/srv/SaveMap \
  "{map_topic: '/robot/map', map_url: '/tmp/test_map', image_format: 'pgm', map_mode: 'trinary', free_thresh: 0.196, occupied_thresh: 0.65}"
```

The separate `launch/utils/save_map.launch.py` utility has three arguments:

| Argument | Default | Effect |
|---|---|---|
| `robot_id` | `robot` | Namespace for the map topic |
| `maps_path` | `/tmp` | Initial output directory |
| `map_name` | `demo_map` | Folder name and saved map basename |

That utility then moves the folder into an inferred workspace's `src/maps`.
It assumes a workspace layout and a destination folder that does not already
exist. The Docker runtime removes source files, so use an explicit service output
path there rather than treating this utility as a portable output-directory API.
