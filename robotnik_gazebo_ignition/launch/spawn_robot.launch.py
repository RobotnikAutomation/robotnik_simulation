# Copyright (c) 2025, Robotnik Automation S.L.L.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Robotnik Automation S.L.L. nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Robotnik Automation S.L.L. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import tempfile
import yaml
import os


from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, OpaqueFunction, TimerAction, RegisterEventHandler
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit
from launch_ros.parameter_descriptions import ParameterValue
from launch.substitutions import LaunchConfiguration
from launch.substitutions import SubstitutionFailure
from launch.substitutions import Command, FindExecutable
from launch.substitutions import PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from robotnik_common.launch import AddArgumentParser, ExtendedArgument


from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Union, Optional
from launch import SomeSubstitutionsType, SomeSubstitutionsType_types_tuple
from launch.frontend.parse_substitution import parse_substitution
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
from launch.utilities.typing_file_path import FilePath
from launch.substitution import Substitution

from launch import LaunchContext
from launch.conditions import IfCondition


# TODO: move this utility class into robotnik_common
class ConfigFile(Substitution):
    """Substitution to get the path of the configuration file."""

    def __init__(
        self,
        param_file: Union[FilePath, SomeSubstitutionsType],
    ) -> None:
        """
        Construct a parameter file description.

        :param param_file: The path to the parameter file or a substitution that resolves to it.
        """
        self.__evaluated_param_file: Optional[Path] = None
        self.__created_tmp_file = False

        self.__param_file = param_file
        if isinstance(param_file, SomeSubstitutionsType_types_tuple):
            self.__param_file = normalize_to_list_of_substitutions(param_file)  # type: ignore

    def perform(self, context: LaunchContext) -> str:
        """Substitute the parameter file path."""
        param_file = self.__param_file
        if isinstance(param_file, list):
            # list of substitutions
            param_file = perform_substitutions(context, self.__param_file)  # type: ignore

        param_file_path: Path = Path(param_file)  # type: ignore
        with open(param_file_path, 'r') as f, NamedTemporaryFile(
                mode='w', prefix='launch_params_', delete=False
            ) as h:
                parsed = perform_substitutions(context, parse_substitution(f.read()))  # type: ignore
                try:
                    yaml.safe_load(parsed)
                except Exception:
                    raise SubstitutionFailure(
                        'The substituted parameter file is not a valid yaml file')
                h.write(parsed)
                param_file_path = Path(h.name)
                self.__created_tmp_file = True
        self.__evaluated_param_file = param_file_path
        return str(param_file_path)

    def cleanup(self) -> None:
        """Remove the temporary file if it was created."""
        if self.__created_tmp_file and self.__evaluated_param_file is not None:
            try:
                self.__evaluated_param_file.unlink()
            except FileNotFoundError:
                # The file may have been deleted already, ignore this error
                pass
            self.__evaluated_param_file = None

    def __del__(self):
        """Clean up the temporary file when the object is deleted."""
        self.cleanup()


def load_yaml(package_path, relative_path):
    full_path = os.path.join(package_path, relative_path)
    with open(full_path, "r") as f:
        return yaml.safe_load(f)

def substitute_param_context(param, context):
    """Resolve a parameter if it is a LaunchConfiguration."""
    if isinstance(param, LaunchConfiguration):
        return param.perform(context)
    return param

def launch_setup(context, params):
    ret = []

    # Required by ros2_control YAML templates that use $(var frame_prefix).
    # Use the frame_prefix parameter passed from parent launch context.
    frame_prefix_value = substitute_param_context(params['frame_prefix'], context)
    context.launch_configurations['frame_prefix'] = frame_prefix_value

    # Robot Description
    ret.append(IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            FindPackageShare('robotnik_description'), '/launch/robot_description.launch.py'
        ]),
        launch_arguments={
            'verbose': 'false',
            'robot_xacro_path': params['robot_xacro_path'],
            'frame_prefix': [params['robot_id'], '_'],
            'namespace': params['robot_id'],
            'gazebo_ignition': 'true',
            'arm_type': params['arm_type'],
            'low_performance_simulation': params['low_performance_simulation']
        }.items(),
    ))

    # Spawner
    ret.append(Node(
        package='ros_gz_sim',
        executable='create',
        namespace=params['robot_id'],
        arguments=[
            '-name', params['robot_id'],
            '-topic', "robot_description",
            '-robot_namespace', params['robot_id'],
            '-x', params['x'],
            '-y', params['y'],
            '-z', params['z'],
        ],
        output='screen',
    ))

    # Gazebo bridge
    def generate_bridge_yaml(params) -> str:
        robot_id = substitute_param_context(params['robot_id'], context)
        bridge_raw = [
            (f"/{robot_id}/imu/data", f"/{robot_id}/imu/data", "sensor_msgs/msg/Imu", "ignition.msgs.IMU", "GZ_TO_ROS"),
            (f"/{robot_id}/gps/data", f"/{robot_id}/gps/fix", "sensor_msgs/msg/NavSatFix", "ignition.msgs.NavSat", "GZ_TO_ROS"),
        ]
        def add_camera(camera_name):
            bridge_raw.extend([
                (f"/{robot_id}/{camera_name}_camera_color/color/camera_info", f"/{robot_id}/{camera_name}_rgbd_camera/color/camera_info", "sensor_msgs/msg/CameraInfo", "gz.msgs.CameraInfo", "GZ_TO_ROS"),
                (f"/{robot_id}/{camera_name}_camera_color/color/image_raw", f"/{robot_id}/{camera_name}_rgbd_camera/color/image_raw", "sensor_msgs/msg/Image", "gz.msgs.Image", "GZ_TO_ROS"),
            ])
        def add_laser(laser_name):
            bridge_raw.extend([
                (f"/{robot_id}/{laser_name}_laser/scan", f"/{robot_id}/{laser_name}_laser/scan", "sensor_msgs/msg/LaserScan", "gz.msgs.LaserScan", "GZ_TO_ROS"),
            ])
        def add_pointcloud(points_name):
            bridge_raw.extend([
                ( f"/{robot_id}/{points_name}_lidar/scan/points", f"/{robot_id}/{points_name}_laser/points", "sensor_msgs/msg/PointCloud2", "gz.msgs.PointCloudPacked", "GZ_TO_ROS"),
            ])

        def add_depth_camera(camera_name):
            bridge_raw.extend([
                (f"/{robot_id}/{camera_name}_camera_depth/depth/camera_info", f"/{robot_id}/{camera_name}_rgbd_camera/depth/camera_info", "sensor_msgs/msg/CameraInfo", "gz.msgs.CameraInfo", "GZ_TO_ROS"),
                (f"/{robot_id}/{camera_name}_camera_depth/depth/image_raw", f"/{robot_id}/{camera_name}_rgbd_camera/depth/image_raw", "sensor_msgs/msg/Image", "gz.msgs.Image", "GZ_TO_ROS"),
            ])

        def add_photoneo_motioncam_cameras():
            """Add Photoneo MotionCam depth and color cameras from arm tool"""
            bridge_raw.extend([
                # Photoneo MotionCam depth camera
                (f"/{robot_id}/arm_tool_photoneo_motioncam_depth/depth/image_raw", f"/{robot_id}/arm_tool_photoneo_motioncam_depth/depth/image_raw", "sensor_msgs/msg/Image", "gz.msgs.Image", "GZ_TO_ROS"),
                (f"/{robot_id}/arm_tool_photoneo_motioncam_depth/depth/camera_info", f"/{robot_id}/arm_tool_photoneo_motioncam_depth/depth/camera_info", "sensor_msgs/msg/CameraInfo", "gz.msgs.CameraInfo", "GZ_TO_ROS"),
                # Photoneo MotionCam color camera
                (f"/{robot_id}/arm_tool_photoneo_motioncam_color/color/image_raw", f"/{robot_id}/arm_tool_photoneo_motioncam_color/color/image_raw", "sensor_msgs/msg/Image", "gz.msgs.Image", "GZ_TO_ROS"),
                (f"/{robot_id}/arm_tool_photoneo_motioncam_color/color/camera_info", f"/{robot_id}/arm_tool_photoneo_motioncam_color/color/camera_info", "sensor_msgs/msg/CameraInfo", "gz.msgs.CameraInfo", "GZ_TO_ROS"),
            ])

        add_camera("front")
        add_camera("rear")
        add_camera("top_ptz")
        add_depth_camera("front")
        add_depth_camera("rear")
        add_laser("front")
        add_laser("rear")
        add_pointcloud("top")
        add_photoneo_motioncam_cameras()

        bridge_config = [{"ros_topic_name": ros, "gz_topic_name": gz, "ros_type_name": ros_type, "gz_type_name": gz_type, "direction": direction} for gz, ros, ros_type, gz_type, direction in bridge_raw]
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            yaml.dump(bridge_config, tmp)
            return tmp.name

    bridge_yaml = generate_bridge_yaml(params)
    ret.append(Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[
            {'config_file': bridge_yaml},
        ],
        namespace=params['robot_id'],
    ))


    def extract_controllers_from_yaml(yaml_path):

        data = {}
        existing_controllers = []
        # Load the YAML file
        with open(yaml_path, 'r') as f:

            # Read the file content
            content = f.read()
            # Remove the string "---\n/**:" if it exists at the beginning
            if content.startswith('---\n/**:'):
                content = content[len('---\n/**:'):]
            # Move file pointer back to start for yaml.safe_load
            f.seek(0)
            f = tempfile.SpooledTemporaryFile(mode='w+')
            f.write(content)
            f.seek(0)

            try:
                data = yaml.safe_load(f)
            except Exception as e:
                raise RuntimeError(f"Failed to parse YAML file '{yaml_path}': {e}")

        for controller in data:
            existing_controllers.append(controller)
        return existing_controllers

    def get_ros2_control_yaml_path(params):
        base_path = (
            Path(FindPackageShare('robotnik_gazebo_ignition').perform(context))
            / 'config'
            / 'profile'
            / substitute_param_context(params['robot'], context)
        )
        robot_model = substitute_param_context(params['robot_model'], context)
        return str(base_path / f'{robot_model}_ros2_control.yaml')

    path = get_ros2_control_yaml_path(params)
    new_controllers = extract_controllers_from_yaml(path)

    # ROS2 control
    controllers = ['joint_state_broadcaster']
    # Replace default joint_state_broadcaster by the one defined in the specific
    # ros2_control.yaml for the robot model
    if 'joint_state_broadcaster' in new_controllers:
        controllers.remove('joint_state_broadcaster')
    controllers.extend(new_controllers)

    # Some arm setups define both trajectory and forward position controllers on the
    # same position interfaces. Spawn forward_position_controller inactive so it is
    # available for switching without conflicting at startup.
    inactive_controllers = []
    if 'joint_trajectory_controller' in controllers and 'forward_position_controller' in controllers:
        controllers.remove('forward_position_controller')
        inactive_controllers.append('forward_position_controller')

    print("Controllers to be spawned:", controllers)
    if inactive_controllers:
        print("Controllers to be spawned inactive:", inactive_controllers)

    # Create ConfigFile substitution (do NOT call perform() - let launch system manage lifecycle)
    robot_controller_config = ConfigFile(path)

    active_controller_args = list(controllers)
    active_controller_args.append('--param-file')
    active_controller_args.append(robot_controller_config)  # Pass substitution directly

    active_spawner = Node(
        package='controller_manager',
        executable='spawner',
        namespace=params['robot_id'],
        arguments=active_controller_args,
        output='screen',
    )

    # Give gz_ros2_control time to initialize controller_manager before spawning.
    ret.append(TimerAction(
        period=8.0,
        actions=[active_spawner],
    ))

    if inactive_controllers:
        inactive_controller_args = list(inactive_controllers)
        inactive_controller_args.append('--inactive')
        inactive_controller_args.append('--param-file')
        inactive_controller_args.append(robot_controller_config)  # Same substitution for inactive

        inactive_spawner = Node(
            package='controller_manager',
            executable='spawner',
            namespace=params['robot_id'],
            arguments=inactive_controller_args,
            output='screen',
        )

        # Start inactive controllers only after active spawner finishes.
        ret.append(RegisterEventHandler(
            OnProcessExit(
                target_action=active_spawner,
                on_exit=[TimerAction(period=1.0, actions=[inactive_spawner])],
            )
        ))

    # Check if rviz config path is modified, if not use default fixed frame
    rviz_config_default = str(
        Path(
            FindPackageShare('robotnik_gazebo_ignition').perform(context)
        )
        / 'config'
        / 'rviz_config.rviz'
    )
    use_fixed_frame = False
    # Determine if fixed frame should be used
    if isinstance(params['rviz_config'], LaunchConfiguration):
        rviz_config_value = params['rviz_config'].perform(context)
        use_fixed_frame = (rviz_config_value == "")
    else:
        use_fixed_frame = (params['rviz_config'] == "")

    if use_fixed_frame:
        params['rviz_config'] = rviz_config_default

    use_sim_time = {"use_sim_time": True}

    # Depth to PointCloud converter for Photoneo MotionCam camera
    ret.append(Node(
        package='robotnik_simulation_bringup',
        executable='depth_to_pointcloud_node.py',
        namespace=params['robot_id'],
        name='depth_to_pointcloud_converter',
        parameters=[use_sim_time],
        remappings=[
            ('depth/image_raw', 'arm_tool_photoneo_motioncam_depth/depth/image_raw'),
            ('depth/camera_info', 'arm_tool_photoneo_motioncam_depth/depth/camera_info'),
            ('depth/points', 'arm_tool_photoneo_motioncam_depth/depth/points'),
        ],
        output='screen',
    ))

    # RViz
    ret.append(Node(
        package="rviz2",
        executable="rviz2",
        namespace=params['robot_id'],
        arguments=[
            # Fixed frame
            ['-f', params['robot_id'], '_odom'] if use_fixed_frame else [],
            # Config file
            '-d', [params['rviz_config']],
            # Window name
            '-t', [params['robot_id'], ' - ', params['robot_model'], ' - navigation RViz'],
        ],
        parameters=[
            use_sim_time,
            ],
        condition=IfCondition(params['run_rviz'])
    ))

    return ret


def generate_launch_description():
    raw_args = [
        ("robot_id", "Unique Robot Identifier", "robot", "ROBOT_ID"),
        ("frame_prefix", "Frame prefix for joint and link names", [LaunchConfiguration('robot_id'), "_"], "FRAME_PREFIX"),
        ("robot", "Robot Model Name", "rbwatcher", "ROBOT"),
        ("robot_model", "Robot Variant or Type", LaunchConfiguration('robot'), "ROBOT_MODEL"),
        ("robot_xacro_path", "Path to Robot Xacro File", [FindPackageShare('robotnik_description'), '/robots/', LaunchConfiguration('robot'), '/', LaunchConfiguration('robot_model'), '.urdf.xacro'], "ROBOT_XACRO_PATH"),
        ("x", "Initial X Coordinate", "0.0", "X"),
        ("y", "Initial Y Coordinate", "0.0", "Y"),
        ("z", "Initial Z Coordinate", "0.0", "Z"),
        ("arm_type", "Type of robotic arm", "ur10e", "ARM_TYPE"),
        ("run_rviz", "Run RViz", "True", "RUN_RVIZ"),
        ("rviz_config", "RViz configuration file", "", "CONFIG_RVIZ"),
        ("use_sim_time", "Use simulation time", "True", "USE_SIM_TIME"),
        ("low_performance_simulation", "Enable Low Performance Simulation", "False", "LOW_PERFORMANCE_SIMULATION"),
    ]

    ld = LaunchDescription()
    add_to_launcher = AddArgumentParser(ld)
    for arg in raw_args:
        extended_arg = ExtendedArgument(
            name=arg[0],
            description=arg[1],
            default_value=arg[2],
            use_env=True,
            environment=arg[3],
        )
        add_to_launcher.add_arg(extended_arg)
    params = add_to_launcher.process_arg()
    ld.add_action(OpaqueFunction(function=launch_setup, args=[params]))
    return ld
