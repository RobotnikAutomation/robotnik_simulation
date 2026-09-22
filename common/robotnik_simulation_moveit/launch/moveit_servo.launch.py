import os
import yaml
import launch
import launch_ros
from ament_index_python.packages import get_package_share_directory
from launch.substitutions import LaunchConfiguration
from moveit_configs_utils import MoveItConfigsBuilder
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import EnvironmentVariable

def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)
    try:
        with open(absolute_file_path) as file:
            return yaml.safe_load(file)
    except OSError:
        return None

def launch_setup(context, *args, **kwargs):
    robot_model = LaunchConfiguration('robot_model').perform(context)
    robot_id = LaunchConfiguration('robot_id').perform(context)
    arm_type = LaunchConfiguration('arm_type').perform(context)
    use_sim_time = LaunchConfiguration('use_sim_time').perform(context).lower() == 'true'
    moveit_manipulation_package_name = LaunchConfiguration('moveit_manipulation_package_name').perform(context)
    moveit_config_pkg = get_package_share_directory(moveit_manipulation_package_name)

    def resolve_model_name_for_file(extension):
        package_model = moveit_manipulation_package_name.replace('_moveit_config', '')
        candidates = [robot_model, package_model]
        if robot_model.startswith('centauro_'):
            candidates.append(robot_model[len('centauro_'):])
        if package_model.startswith('centauro_'):
            candidates.append(package_model[len('centauro_'):])

        for candidate in candidates:
            file_path = os.path.join(moveit_config_pkg, 'config', f'{candidate}{extension}')
            if os.path.exists(file_path):
                return candidate

        raise FileNotFoundError(
            f"No model file '*{extension}' found for candidates {candidates} in {moveit_config_pkg}/config"
        )

    servo_yaml = load_yaml(moveit_manipulation_package_name, "config/ur_servo.yaml")
    if servo_yaml is None:
        print(
            f"[WARN] moveit_servo.launch.py: '{moveit_manipulation_package_name}/config/ur_servo.yaml' not found. "
            "Skipping MoveIt Servo node."
        )
        return []

    resolved_model = resolve_model_name_for_file('.srdf')

    # Match move_group.launch.py's namespace/prefix so joint names line up with /robot/joint_states
    moveit_config = (
        MoveItConfigsBuilder(resolved_model, package_name=moveit_manipulation_package_name)
        .robot_description(
            file_path=f"config/{resolved_model}.urdf.xacro",
            mappings={
                'namespace': robot_id,
                'prefix': f'{robot_id}_',
                'gazebo_ignition': 'true',
                'ur_type': arm_type,
            },
        )
        .robot_description_semantic(file_path=f"config/{resolved_model}.srdf")
        .joint_limits(file_path="config/joint_limits.yaml")
        .to_moveit_configs()
    )

    # Get parameters for the Servo node
    servo_params = {"moveit_servo": servo_yaml}

    # This sets the update rate and planning group name for the acceleration limiting filter.
    acceleration_filter_update_period = {"update_period": 0.01}
    planning_group_name = {"planning_group_name": "arm"}

    # Launch a standalone Servo node.
    servo_node = launch_ros.actions.Node(
        package="moveit_servo",
        executable="servo_node",
        name="moveit_servo_node",
        namespace=robot_id,
        parameters=[
            servo_params,
            acceleration_filter_update_period,
            planning_group_name,
            {"use_sim_time": use_sim_time},
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
        ],
        output="screen",
    )

    return [servo_node]

def generate_launch_description():
    return launch.LaunchDescription([
        DeclareLaunchArgument(
            'moveit_manipulation_package_name',
            default_value=EnvironmentVariable('MOVEIT_MANIPULATION_PACKAGE_NAME', default_value='centauro_rbvogui_plus_moveit_config')
        ),
        DeclareLaunchArgument(
            'robot_model',
            default_value=EnvironmentVariable('ROBOT_MODEL', default_value='centauro_rbvogui_plus'),
        ),
        DeclareLaunchArgument(
            'robot_id',
            default_value='robot',
            description='Unique Robot Identifier',
        ),
        DeclareLaunchArgument(
            'arm_type',
            default_value='ur10e',
            description='Type of robotic arm',
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time',
        ),
        OpaqueFunction(function=launch_setup)
    ])