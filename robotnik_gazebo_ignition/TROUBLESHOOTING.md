# Robotnik Gazebo Ignition Troubleshooting

This document collects the operational notes that are useful after the initial setup is complete, including installation checks, launch and control issues, GPU validation and current known limitations.

## Installation issues

### `rosdep install` fails

- Confirm that the workspace repositories were imported successfully with `vcs` before running `rosdep`.
- Make sure you are running the command from the workspace root after sourcing `/opt/ros/jazzy/setup.bash`.
- If the failure is related to missing local source packages such as `robotnik_description`, `robotnik_sensors` or `teleop_panel`, check that those repositories are present under `src/`.

### Local Robotnik `.deb` packages are not found

- Confirm that you are running the install command from `~/ros2_ws/src/robotnik/robotnik_simulation`.
- Check that the `debs/` directory exists and contains the expected `ros-jazzy-*.deb` files.
- If the directory is missing, verify that you imported the correct repository and branch.

### `colcon build` does not find expected packages

- Confirm that the repository import step completed without errors.
- Check that the required repositories are present under `~/ros2_ws/src/robotnik/`.
- If you recently changed package dependencies or manifests, rerun `rosdep install --from-paths src --ignore-src -r -y` before rebuilding.

## Launch and spawn issues

### Gazebo launches but the robot does not appear

- Confirm that a Gazebo world is already running before launching `spawn_robot.launch.py`.
- Review the selected `robot` and `robot_model` values and make sure that combination exists in `robotnik_description`.
- If you are using `robot_xacro_path`, verify that the file exists and is readable.
- If you are spawning multiple robots, confirm that each one uses a unique `robot_id`.

### The expected ROS 2 topics are missing

- Review the selected `robot_id` and namespace in use.
- Confirm that the Gazebo bridges are active and that the robot was spawned successfully.
- If you launched only the world, remember that robot-specific topics do not exist until `spawn_robot.launch.py` completes.

### Gazebo server remains alive after closing the simulation

Gazebo Sim runs the server and the GUI as separate processes. Closing the GUI, or interrupting only part of the launch tree, may leave the Gazebo server running in the background.

When this happens, previously spawned robot models can remain loaded in the world. If those models include `gz_ros2_control`, Gazebo-side ROS 2 control nodes such as `controller_manager` and `gz_ros_control` may still appear in the ROS graph even after closing the simulation terminal.

Typical symptoms:

```bash
ros2 node list | grep -E "controller_manager|gz_ros_control"
```

still shows nodes such as:

```text
/<robot_id>/controller_manager
/<robot_id>/gz_ros_control
```

or a new empty world unexpectedly contains robots from a previous simulation run.

Check whether a Gazebo server is still running:

```bash
ps -ef | grep -E "gz sim|ign gazebo|ruby.*gz.*sim" | grep -v grep
```

You can also check whether Gazebo world services are still available:

```bash
gz service -l | grep /world/
```

If the Gazebo server is still running and you want to stop the simulation
completely, run the cleanup helper manually. Closing the GUI or pressing Ctrl+C
in a launch terminal does not invoke this script automatically:

```bash
ros2 run robotnik_gazebo_ignition stop_gazebo_sim.sh
```

If common ROS simulation helper processes also remain, use:

```bash
ros2 run robotnik_gazebo_ignition stop_gazebo_sim.sh --all
```

Use `--force` only if the graceful shutdown does not stop the remaining processes:

```bash
ros2 run robotnik_gazebo_ignition stop_gazebo_sim.sh --force
```

Note that this helper is intended for development cleanup. It stops lingering Gazebo simulation processes and, with `--all`, common ROS simulation helper processes. Do not use it if you are intentionally running another Gazebo simulation in the same machine.


## RViz and MoveIt issues

### RViz opens without the expected Robotnik layout or teleoperation panel

- Confirm that RViz was started from the provided launch files instead of a manual `rviz2` invocation.
- If you use a custom RViz config, make sure it still includes the expected Robotnik displays and the `Teleop` panel.

### MoveIt does not connect or interact correctly

- Match `robot_id`, `frame_prefix`, `robot`, `robot_model`, description and arm
  arguments with the spawned robot. Examples use `robot_id:=robot`; custom
  namespaces need runtime validation rather than an automatic model change.
- Verify that the selected `robot` and `robot_model` have a matching manipulation profile under `robotnik_simulation_robots/<robot>/manipulation/`.
- If you are using a mobile manipulator, check that `arm_type` matches the robot configuration being launched.

### Unexpected RViz windows

Bringup has no RViz node. Navigation and MoveIt enable their views by default;
`run_gazebo_gui=false` only hides Gazebo's GUI. To disable a module's view,
configure its own standalone launch. Basic RViz is only omitted when navigation
starts through bringup; launching navigation later does not close an existing
basic window. See the [bringup guide](../common/robotnik_simulation_bringup/README.md).

## Control issues

### The robot does not respond to control commands

- Review the selected command topic and confirm that it matches the active `robot_id`.
- Check whether navigation, RViz teleoperation and keyboard teleoperation are publishing to the same command topic at the same time.
- If the robot was launched with a custom namespace, update the control topic accordingly.

### Teleoperation sources interfere with each other

- Avoid running multiple teleoperation or navigation sources simultaneously unless you are intentionally multiplexing commands.
- If the robot behaves unpredictably, stop all command sources and restart only the one you want to test.

## GPU selection and verification

### Enable PRIME offload through launch

Use the argument provided by spawn_world; do not add rendering environment
variables to every launch command:

```bash
ros2 launch robotnik_gazebo_ignition spawn_world.launch.py world:=empty use_nvidia_gpu:=true
```

The same argument works in bringup. It is **false by default**, applies to
Gazebo server/GUI only and leaves RViz unchanged. For Docker use
`USE_NVIDIA_GPU=true` together with the
[GPU Compose overlay](../docker/README.md#nvidia-gpu). See the
[rendering contract](README.md#nvidia-prime-rendering) for scope and defaults.

### Check device visibility and the actual Gazebo process

```bash
nvidia-smi
```

Check on the host or inside the container where simulation runs. A missing
command, driver error or missing device indicates a visibility/setup problem
that the launch flag cannot fix. With Gazebo running, inspect the GPU process
list, utilization and rendering errors in its logs. Process reporting depends
on the driver and container setup; no single diagnostic guarantees rendering.

`glxinfo -B`, when available, describes the renderer selected by **glxinfo**.
Because the PRIME settings are scoped to Gazebo, a separately launched
`glxinfo` may legitimately show Intel even while Gazebo uses NVIDIA. Likewise,
`nvidia-smi` succeeding only proves device/driver visibility, not that Gazebo
created a rendering context on it.

## Known limitations

- Some robots in the support table are marked as `Limited` and may still require additional validation or tuning for specific workflows.
- Custom MoveIt namespace/prefix substitution has been checked offline; full
  interactive behavior still needs verification in a running session.
- Mapping currently needs its scan pipeline started separately and lifecycle
  activation. See the [localization guide](../common/robotnik_simulation_localization/README.md).
- Disabling localization does not add an odometry-only navigation fallback.

## Related

- Main package guide: [`README.md`](README.md)
- Docker workflow: [`../docker/README.md`](../docker/README.md)
