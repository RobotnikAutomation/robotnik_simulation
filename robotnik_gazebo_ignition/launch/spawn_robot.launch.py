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

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import EqualsSubstitution
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
from launch.conditions import IfCondition, UnlessCondition

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterFile

from robotnik_common.launch import AddArgumentParser, ExtendedArgument

from pathlib import Path

def generate_rviz_config(context, rviz_config_path, robot_id, frame_prefix):
    """Generate an RViz config adapted to the current robot instance.

    The default RViz config is stored with topics under /robot/ and frames using
    the robot_ prefix. When spawning robots with a different robot_id or
    frame_prefix, create a temporary RViz config pointing to the correct topics
    and TF frames.
    """
    robot_id_value = perform_substitutions(
        context,
        normalize_to_list_of_substitutions(robot_id),
    )
    frame_prefix_value = perform_substitutions(
        context,
        normalize_to_list_of_substitutions(frame_prefix),
    )

    with open(rviz_config_path, 'r') as f:
        content = f.read()
    # Replace only the default robot namespace and frame prefix used by the
    # template RViz config.
    robot_ns_placeholder = '__ROBOT_NAMESPACE_PLACEHOLDER__'
    robot_description_placeholder = '__ROBOT_DESCRIPTION_PLACEHOLDER__'

    # Protect values that must not be affected by the frame-prefix replacement.
    content = content.replace('/robot/', f'/{robot_ns_placeholder}/')
    content = content.replace('robot_description', robot_description_placeholder)

    # Replace the default frame prefix used by the RViz config.
    content = content.replace('robot_', frame_prefix_value)

    # Restore protected values with the current robot namespace.
    content = content.replace(f'/{robot_ns_placeholder}/', f'/{robot_id_value}/')
    content = content.replace(robot_description_placeholder, 'robot_description')

    with tempfile.NamedTemporaryFile(
        mode='w',
        prefix='rviz_config_',
        suffix='.rviz',
        delete=False,
    ) as tmp:
        tmp.write(content)
        return tmp.name

def substitute_param_context(param, context):
    """Resolve a parameter if it is a LaunchConfiguration."""
    if isinstance(param, LaunchConfiguration):
        return param.perform(context)
    return param

def launch_setup(context, params):
    ret = []

    # Robot Description
    ret.append(IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            FindPackageShare('robotnik_description'), '/launch/robot_description.launch.py'
        ]),
        launch_arguments={
            'verbose': 'false',
            'robot_xacro_path': params['robot_xacro_path'],
            'frame_prefix': params['frame_prefix'],
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
        robot_model = substitute_param_context(params['robot_model'], context)
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

        if robot_model == "rbwatcher":
            # rbwatcher equips these streams; avoid bridges for sensors that
            # are not present in its Gazebo model.
            add_camera("front")
            add_camera("top_ptz")
            add_depth_camera("top_ptz")
            add_pointcloud("top")
        else:
            # Preserve the legacy generic profile for the other models.
            add_camera("front")
            add_camera("rear")
            add_camera("top_ptz")
            if robot_model != "rbcar":
                add_laser("front")
            add_laser("rear")
            add_pointcloud("top")

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
    controllers =  ['--controller-manager-timeout', '60',
                    '--service-call-timeout', '60',
                    '--unload-on-kill',
                    'joint_state_broadcaster']
    # Replace default joint_state_broadcaster by the one defined in the specific
    # ros2_control.yaml for the robot model
    if 'joint_state_broadcaster' in new_controllers:
        controllers.remove('joint_state_broadcaster')
    controllers.extend(new_controllers)
    print("Controllers to be spawned:", controllers)

    robot_controller_config = ParameterFile(path, allow_substs=True)

    # RB-CAR uses the standard Ackermann controller and requires controller-specific
    # ROS argument remaps. Spawn it separately so these remaps are applied only to
    # robotnik_base_control.
    is_rbcar = EqualsSubstitution(params['robot'], 'rbcar')

    ret.append(Node(
        package='controller_manager',
        executable='spawner',
        namespace=params['robot_id'],
        arguments=controllers,
        parameters=[robot_controller_config],
        output='screen',
        condition=UnlessCondition(is_rbcar),
    ))

    rbcar_joint_state_broadcaster = [
        '--controller-manager-timeout', '60',
        '--service-call-timeout', '60',
        '--unload-on-kill',
        'joint_state_broadcaster',
    ]
    ret.append(Node(
        package='controller_manager',
        executable='spawner',
        namespace=params['robot_id'],
        arguments=rbcar_joint_state_broadcaster,
        parameters=[robot_controller_config],
        output='screen',
        condition=IfCondition(is_rbcar),
    ))

    rbcar_ackermann_controller = [
        '--controller-manager-timeout', '60',
        '--service-call-timeout', '60',
        'robotnik_base_control',
        '--controller-ros-args', '--ros-args -r ~/tf_odometry:=/tf -r ~/odometry:=~/odom -r ~/reference:=~/cmd_vel',
    ]
    ret.append(Node(
        package='controller_manager',
        executable='spawner',
        namespace=params['robot_id'],
        arguments=rbcar_ackermann_controller,
        parameters=[robot_controller_config],
        output='screen',
        condition=IfCondition(is_rbcar),
    ))

    # If no custom RViz config is provided, adapt the default RViz config to the
    # current robot namespace and frame prefix. The default config is authored for
    # robot_id="robot" and frame_prefix="robot_".
    rviz_config_default = str(
        Path(
            FindPackageShare('robotnik_gazebo_ignition').perform(context)
        )
        / 'config'
        / 'rviz_config.rviz'
    )

    if isinstance(params['rviz_config'], LaunchConfiguration):
        rviz_config_value = params['rviz_config'].perform(context)
        use_default_rviz_config = (rviz_config_value == "")
    else:
        use_default_rviz_config = (params['rviz_config'] == "")

    if use_default_rviz_config:
        params['rviz_config'] = generate_rviz_config(
            context,
            rviz_config_default,
            params['robot_id'],
            params['frame_prefix'],
    )

    use_sim_time = {"use_sim_time": True}

    # RViz
    ret.append(Node(
        package="rviz2",
        executable="rviz2",
        namespace=params['robot_id'],
        arguments=[
            # Fixed frame
            ['-f', params['frame_prefix'], 'odom'] if use_default_rviz_config else [],
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
        ("robot", "Robot Model Name", "rbwatcher", "ROBOT"),
        ("robot_model", "Robot Variant or Type", LaunchConfiguration('robot'), "ROBOT_MODEL"),
        ("frame_prefix", "Frame prefix", [LaunchConfiguration('robot_id'), '_'], "FRAME_PREFIX"),
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
