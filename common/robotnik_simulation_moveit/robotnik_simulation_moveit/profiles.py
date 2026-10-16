"""Resolve and validate robot-specific MoveIt profiles."""

import os

from launch_ros.substitutions import FindPackageShare


REQUIRED_MANIPULATION_FILES = (
    "kinematics.yaml",
    "joint_limits.yaml",
    "pilz_cartesian_limits.yaml",
    "pilz_industrial_motion_planner_planning.yaml",
    "moveit_controllers.yaml",
)


def resolve_manipulation_profile(context, robot, robot_model):
    """Return the profile directory and SRDF after validating required assets."""
    profile_dir = os.path.join(
        FindPackageShare("robotnik_simulation_robots").perform(context),
        robot,
        "manipulation",
    )
    srdf_path = os.path.join(profile_dir, f"{robot_model}.srdf")
    required_files = [
        srdf_path,
        *(os.path.join(profile_dir, name) for name in REQUIRED_MANIPULATION_FILES),
    ]
    missing_files = [path for path in required_files if not os.path.isfile(path)]
    if missing_files:
        raise RuntimeError(
            f"No complete MoveIt manipulation profile for robot '{robot}' "
            f"and model '{robot_model}'. Missing files: {', '.join(missing_files)}"
        )

    return profile_dir, srdf_path
