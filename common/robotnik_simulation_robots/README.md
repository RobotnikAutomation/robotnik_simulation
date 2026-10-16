# Robot-specific simulation profiles

This package stores configurations selected by the simulation launch packages.
It does not start nodes. Robot family and variant are different selectors:

```text
<robot>/
  control/<robot_model>_ros2_control.yaml
  localization/                         # optional
  navigation/                           # optional
  manipulation/                         # optional
```

| Consumer | Selection |
|---|---|
| Spawn controllers | `robot/control/<robot_model>_ros2_control.yaml` |
| Localization | Complete family files under `robot/localization/` |
| Navigation | Complete family files under `robot/navigation/` |
| MoveIt | Family manipulation files plus `<robot_model>.srdf` |

Only standalone localization/navigation with `robot` empty use the generic
configuration in their own packages. Bringup defaults to `rbsummit` and passes
that family explicitly. Spawn and MoveIt also have their own nonempty presets;
omitting `robot` does not select a generic fallback in those entrypoints.
Profiles replace the corresponding generic files; they are not partial overlays.

## Available family profiles

| Family | Control variants | Localization / navigation | Manipulation variant |
|---|---|---|---|
| `rb1` | `rb1` | Present | — |
| `rbcar` | `rbcar` | Present | — |
| `rbfiqus` | `rbfiqus` | Absent | — |
| `rbkairos` | `rbkairos`, `rbkairos_plus` | Present | `rbkairos_plus` |
| `rbrobout` | `rbrobout`, `rbrobout_plus` | Present | `rbrobout_plus` |
| `rbsummit` | `rbsummit` | Present | — |
| `rbsummit_steel` | `rbsummit_steel` | Present | — |
| `rbtheron` | `rbtheron`, `rbtheron_plus` | Present | `rbtheron_plus` |
| `rbvogui` | `rbvogui`, `rbvogui_plus` | Present | `rbvogui_plus` |
| `rbvogui_xl` | `rbvogui_xl` | Present | — |
| `rbwatcher` | `rbwatcher` | Present | — |

This table describes files present in the repository, not full runtime validation.
Bringup skips missing localization/navigation profiles with a warning. Requested
MoveIt profiles must contain the required files or the launch reports an error.

## Frames, clock and topics

ROS parameter files use `$(var frame_prefix)`, `$(var robot_id)` and, where
needed, `$(var use_sim_time)`. The owning launch resolves those substitutions.
The localization scan pipeline is a separate plain YAML schema read directly by
Python; arbitrary launch substitutions are not expanded in that file.

Changing the scan pipeline's output topic also requires updating its AMCL,
SLAM and costmap consumers. The `target_frame` in the scan profile is a suffix:
the launcher adds `frame_prefix`.

See [bringup arguments](../robotnik_simulation_bringup/README.md),
[MoveIt](../robotnik_simulation_moveit/README.md) and the
[configuration map](../../docs/configuration-audit/README.md).

The owning module guides list the launch interfaces and generic defaults:
[localization](../robotnik_simulation_localization/README.md) and
[navigation](../robotnik_simulation_navigation/README.md).
