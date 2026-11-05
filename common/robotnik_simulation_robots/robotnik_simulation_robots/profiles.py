"""Find profiles without silently replacing an explicitly selected robot family.

These helpers report missing resources; callers decide whether to skip an
optional component or fail. Only an empty family selects a generic config.
"""
from pathlib import Path

import yaml
from launch_ros.parameter_descriptions import ParameterFile
from launch_ros.substitutions import FindPackageShare


REQUIRED_MANIPULATION_FILES = (
    'kinematics.yaml',
    'joint_limits.yaml',
    'pilz_cartesian_limits.yaml',
    'pilz_industrial_motion_planner_planning.yaml',
    'moveit_controllers.yaml',
)


def profile_directory(context, robot, component):
    """Return the selected family's resource directory, without a fallback."""
    return Path(FindPackageShare('robotnik_simulation_robots').perform(context)) / robot / component


def missing_profile_files(context, robot, component, filenames):
    """Return paths for missing files in an optional component."""
    directory = profile_directory(context, robot, component)
    return [str(directory / name) for name in filenames if not (directory / name).is_file()]


def resolve_config(context, robot, component, filename, default_package):
    """Return a required config path; an empty robot selects the generic file."""
    directory = (profile_directory(context, robot, component) if robot else
                 Path(FindPackageShare(default_package).perform(context)) / 'config')
    path = directory / filename
    if not path.is_file():
        raise FileNotFoundError(f"{component} configuration for robot '{robot}' was not found: {path}")
    return str(path)


def resolve_variant_file(directory, robot, robot_model, suffix):
    """Prefer the model's resource, then the family's default resource."""
    directory = Path(directory)
    candidates = [directory / f'{robot_model}{suffix}', directory / f'{robot}{suffix}']
    for path in candidates:
        if path.is_file():
            return str(path)
    raise FileNotFoundError('No variant profile found. Tried ' + ', '.join(map(str, candidates)))


def has_manipulation(context, robot, robot_model):
    """Whether the variant declares manipulation; incomplete profiles still fail validation."""
    return bool(robot and robot_model and
                (profile_directory(context, robot, 'manipulation') / f'{robot_model}.srdf').is_file())


def resolve_manipulation_profile(context, robot, robot_model):
    """Validate all required manipulation assets before a module starts."""
    directory = profile_directory(context, robot, 'manipulation')
    missing = missing_profile_files(context, robot, 'manipulation',
                                    (f'{robot_model}.srdf', *REQUIRED_MANIPULATION_FILES))
    if missing:
        raise RuntimeError(
            f"No complete MoveIt manipulation profile for robot '{robot}' and model "
            f"'{robot_model}'. Missing files: {', '.join(missing)}"
        )
    return str(directory), str(directory / f'{robot_model}.srdf')


def load_config(context, source_file):
    """Load YAML after launch substitutions, releasing the temporary file even on errors."""
    config = ParameterFile(source_file, allow_substs=True)
    try:
        with open(config.evaluate(context), encoding='utf-8') as stream:
            return yaml.safe_load(stream)
    finally:
        config.cleanup()
