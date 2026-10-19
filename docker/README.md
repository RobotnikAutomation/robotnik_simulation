# Docker guide

This directory contains the Docker files used to run `robotnik_simulation`.

The simulation configuration is defined in [env/robot.env](../env/robot.env).

Edit that file to choose the robot, world, Gazebo rendering, basic RViz and
module activation before launching the container. The file defaults to
`rbwatcher`, whereas the standalone bringup default is `rbsummit`. NVIDIA PRIME
is false in both. Changes take effect when the entrypoint runs again; recreate
the container after editing the mounted file, without rebuilding the image:

```bash
docker compose -f docker/docker-compose.yaml up -d --force-recreate
```

## Workspace model

This Docker setup does not run directly from your host ROS 2 workspace as a bind-mounted development tree.

When the image is built, it creates an internal workspace at `/opt/robotnik_ws` and:

- copies only this `robotnik_simulation` repository from your local machine into that workspace
- imports the additional Robotnik repositories declared in `dependencies/repos/robotnik_simulation.jazzy.repos`
- resolves dependencies and builds the workspace inside the image

The runtime container uses the installed workspace from `/opt/robotnik_ws/install`. It does not keep the `src` tree from the build stage.

That means:

- changes in your local repository are not reflected in the container until you rebuild the image
- other local packages from your host workspace are not included automatically
- if the image needs additional repositories, they must be added to `dependencies/repos/robotnik_simulation.jazzy.repos`
- `docker exec` gives you access to the runtime environment and installed packages, not to a live bind-mounted source workspace

## Prerequisites

- Docker must be installed.
- Your user should have permission to use Docker.
- If your user is not in the Docker group, run the commands below with `sudo`.

## 1. Run the published image

Use this option when the image is available to you in Docker Hub or another registry. Replace the
example image tag with the release you intend to run.

From the repository root:

```bash
cd ~/ros2_ws/src/robotnik/robotnik_simulation
```

Pull the image:

```bash
docker pull robotnik/simulation-gz:jazzy
```

Launch the simulation:

```bash
ROBOTNIK_SIMULATION_IMAGE=robotnik/simulation-gz:jazzy \
docker compose -f docker/docker-compose.yaml up
```

If you prefer, you can also export `ROBOTNIK_SIMULATION_IMAGE` in the shell before launching.

To stop the published-image run started with `docker compose ... up`, press `Ctrl+C` once to stop the simulation gracefully. If the container does not exit cleanly, press `Ctrl+C` again to force it to stop.

## 2. Build a new image locally

Use this option when you want to generate the image from the current contents of this repository. Any additional repositories that must be part of the image need to be declared in `dependencies/repos/robotnik_simulation.jazzy.repos`.

From the repository root:

```bash
cd ~/ros2_ws/src/robotnik/robotnik_simulation
```

Build the image:

```bash
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose -f docker/docker-compose.yaml build
```

Launch the simulation with the locally built image:

```bash
docker compose -f docker/docker-compose.yaml up
```

You can also build and launch in a single step:

```bash
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose -f docker/docker-compose.yaml up --build
```

## NVIDIA GPU

GPU access and PRIME device selection are separate settings:

1. Expose the NVIDIA devices using both Compose files. The host driver and
   NVIDIA Container Toolkit must already support GPU access from Docker.
2. On hybrid systems, set `USE_NVIDIA_GPU=true` in `env/robot.env` to request
   NVIDIA PRIME rendering for Gazebo. Its default is **false**.

```bash
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.gpu.yaml up
```

For a registry image, prepend the same `ROBOTNIK_SIMULATION_IMAGE` assignment
used above. Use the same pair of `-f` options for subsequent `up`, `build` or
`down` commands for that session.

`USE_NVIDIA_GPU=true` applies PRIME to the Gazebo server and GUI only, including
server-side sensors without a GUI. It does not expose devices, install drivers,
select RViz's GPU or force software rendering when false. See the
[Gazebo rendering guide](../robotnik_gazebo_ignition/README.md#nvidia-prime-rendering).

## Runtime arguments

The entrypoint translates nonempty settings from `env/robot.env`:

| Settings | Launch options |
|---|---|
| `ROBOT_ID`, `ROBOT`, `ROBOT_MODEL`, `ROBOT_XACRO_PATH` | Instance, family, variant and description |
| `FRAME_PREFIX`, `ARM_TYPE`, `USE_SIM_TIME` | Frames/joints, arm type and clock |
| `RUN_WORLD` | Start Gazebo and the clock bridge; false reuses an existing world |
| `RUN_GAZEBO_GUI`, `USE_NVIDIA_GPU` | Gazebo window and optional PRIME rendering |
| `RUN_LOCALIZATION`, `RUN_NAVIGATION`, `RUN_MOVEIT` | Independent modules; defaults true, true, false |
| `RUN_SPAWN_RVIZ`, `SPAWN_RVIZ_CONFIG` | Basic view, omitted when navigation starts |
| `LOW_PERFORMANCE_SIMULATION`, `RUN_MAPPING` | Sensor performance settings and localization mode |
| `WORLD`, `WORLD_PATH`, `X`, `Y`, `Z` | World selection and spawn coordinates |

Empty values omit arguments. `WORLD_PATH` overrides `WORLD`. Navigation and
MoveIt enable their own RViz by default; their visual controls are not part of
the bringup environment interface. To configure them separately, use their
standalone launches. See the [bringup argument table](../common/robotnik_simulation_bringup/README.md#arguments).

Set `RUN_WORLD=false` when this robot must join a world that is already running.
The world owner must supply Gazebo and the `/clock` bridge. Robot processes must
share its ROS domain and Gazebo transport partition. World path, GUI and rendering
settings apply only to the process that starts the world. See the
[multi-robot workflow](../common/robotnik_simulation_bringup/README.md#multiple-robots-in-one-world).

`ROBOTNIK_LAUNCH_ARGS`, when nonempty, **replaces** the automatic translation;
it is not appended. The entrypoint splits it on whitespace, so it is unsuitable
for argument values containing spaces. `ROBOTNIK_LAUNCH_PACKAGE` and
`ROBOTNIK_LAUNCH_FILE` select the entrypoint; supply matching explicit arguments
when selecting a different launch. `RUNTIME_AUTOSTART=false` keeps the container
running without starting simulation.

## 3. Daily workflow

Once the container is running, keep the first terminal attached to:

```bash
docker compose -f docker/docker-compose.yaml up
```

That terminal shows the bringup logs and lets you stop the session with `Ctrl+C`.

If you want to work inside the running container, open a second terminal and enter it as the `robot` user:

```bash
docker exec -it -u robot robotnik_simulation bash
```

Inside that shell you can inspect topics, launch extra nodes or interact with the simulated robot using normal ROS 2 commands such as:

```bash
ros2 topic list
ros2 node list
ros2 topic echo /clock
```

This shell is attached to the runtime container built from the installed workspace in `/opt/robotnik_ws/install`.

If you prefer to leave the simulation running in the background, start it detached:

```bash
docker compose -f docker/docker-compose.yaml up -d
```

Then attach a shell with `docker exec` whenever you need to work inside the container.

To stop the running container without removing it:

```bash
docker stop robotnik_simulation
```

To start that same stopped container again and reattach to its logs:

```bash
docker start -a robotnik_simulation
```

To stop and remove the Compose container completely:

```bash
docker compose -f docker/docker-compose.yaml down
```

To remove the local image:

```bash
docker rmi robotnik_simulation:jazzy
```

If you selected a registry image, remove that exact tag instead, for example
`robotnik/simulation-gz:jazzy`. The default local tag comes from the Compose file.

## Notes

- Changing `../env/robot.env` does not require rebuilding the image.
- Changing source code, dependencies, manifests or `docker/Dockerfile` does require rebuilding the image.
- For NVIDIA systems, use `docker/docker-compose.gpu.yaml` together with the main compose file.

Standalone commands in a `docker exec` shell use CLI arguments, not the file
loaded by the original entrypoint. For example, a separately started world
needs its own `use_nvidia_gpu:=true` argument if PRIME offload is wanted.
Do not start another world/robot bringup while the integrated session is active.
