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
import os
from pathlib import Path
import tempfile

import yaml

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.event_handlers import OnShutdown
from launch.substitutions import LaunchConfiguration
from launch.substitutions import EqualsSubstitution
from launch.substitutions import Command, FindExecutable
from launch.substitutions import PathJoinSubstitution

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.descriptions import ParameterValue
from launch_ros.parameter_descriptions import ParameterFile

from launch.conditions import IfCondition, UnlessCondition


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

    # Compose the simulator-independent description with Gazebo ros2_control.
    gazebo_robot_xacro = PathJoinSubstitution([
        FindPackageShare('robotnik_description'),
        'simulators',
        'gazebo_ignition',
        'robot.urdf.xacro',
    ])
    robot_description_content = Command([
        FindExecutable(name='xacro'),
        ' ', gazebo_robot_xacro,
        ' robot_xacro_path:=', params['robot_xacro_path'],
        ' robot:=', params['robot'],
        ' namespace:=', params['robot_id'],
        ' prefix:=', params['frame_prefix'],
        ' controller_config:=', params['robot_model'], '_ros2_control.yaml',
        ' gazebo_ignition:=true',
        ' ur_type:=', params['arm_type'],
        ' low_performance:=', params['low_performance_simulation'],
    ])
    robot_description = ParameterValue(robot_description_content, value_type=str)
    ret.append(Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        namespace=params['robot_id'],
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'publish_frequency': 100.0,
            'use_sim_time': params['use_sim_time'],
        }],
    ))

    # Spawner
    ret.append(Node(
        package='ros_gz_sim',
        executable='create',
        namespace=params['robot_id'],
        parameters=[{'use_sim_time': params['use_sim_time']}],
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

    def generate_bridge_yaml(params) -> str:
        robot_id = substitute_param_context(params['robot_id'], context)
        robot = substitute_param_context(params['robot'], context)
        robot_model = substitute_param_context(params['robot_model'], context)
        package_path = FindPackageShare('robotnik_gazebo_ignition').perform(context)

        templates_config = load_yaml(package_path, 'config/bridge_templates.yaml') or {}
        profile_config = load_yaml(
            package_path,
            f'config/profile/{robot}/{robot_model}_bridges.yaml',
        ) or {}

        templates = templates_config.get('templates', {})
        bridge_items = profile_config.get('bridges', [])
        bridge_config = []

        for item in bridge_items:
            template_name = item.get('template')
            if template_name not in templates:
                raise RuntimeError(
                    f"Bridge template '{template_name}' not found for robot '{robot}' "
                    f"and model '{robot_model}'"
                )

            format_values = {
                'robot_id': robot_id,
                'name': item.get('name', ''),
                'gz_topic': item.get('gz_topic', ''),
                'ros_topic': item.get('ros_topic', ''),
            }

            for template_entry in templates[template_name]:
                bridge_config.append({
                    key: value.format(**format_values) if isinstance(value, str) else value
                    for key, value in template_entry.items()
                })

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            yaml.dump(bridge_config, tmp)
            return tmp.name

    bridge_yaml = generate_bridge_yaml(params)
    ret.append(Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[
            {'config_file': bridge_yaml, 'use_sim_time': params['use_sim_time']},
        ],
        namespace=params['robot_id'],
    ))


    def extract_controllers_from_yaml(yaml_path):
        existing_controllers = []
        with open(yaml_path, 'r') as f:
            try:
                data = yaml.safe_load(f) or {}
            except Exception as e:
                raise RuntimeError(f"Failed to parse YAML file '{yaml_path}': {e}")

        root_data = data.get('/**', data)
        ros_parameters = root_data.get('controller_manager', {}).get('ros__parameters', {})

        for controller_name, controller_data in ros_parameters.items():
            if isinstance(controller_data, dict) and 'type' in controller_data:
                existing_controllers.append(controller_name)

        return existing_controllers

    def get_ros2_control_yaml_path(params):
        base_path = (
            Path(FindPackageShare('robotnik_simulation_robots').perform(context))
            / substitute_param_context(params['robot'], context)
            / 'control'
        )
        robot_model = substitute_param_context(params['robot_model'], context)
        return str(base_path / f'{robot_model}_ros2_control.yaml')

    path = get_ros2_control_yaml_path(params)
    new_controllers = extract_controllers_from_yaml(path)

    # ROS2 control
    controllers =  ['--controller-manager-timeout', '60', '--service-call-timeout', '60', 'joint_state_broadcaster']
    # Replace default joint_state_broadcaster by the one defined in the specific
    # ros2_control.yaml for the robot model
    if 'joint_state_broadcaster' in new_controllers:
        controllers.remove('joint_state_broadcaster')
    controllers.extend(new_controllers)
    print("Controllers to be spawned:", controllers)

    # The spawner forwards ROS parameter files to the controllers it loads.
    robot_controller_config = ParameterFile(path, allow_substs=True)

    is_rbcar = EqualsSubstitution(params['robot'], 'rbcar')

    ret.append(Node(
        package='controller_manager',
        executable='spawner',
        namespace=params['robot_id'],
        arguments=controllers,
        parameters=[robot_controller_config, {'use_sim_time': params['use_sim_time']}],
        output='screen',
        condition=UnlessCondition(is_rbcar),
    ))

    rbcar_joint_state_broadcaster = [
        '--controller-manager-timeout', '60',
        '--service-call-timeout', '60',
        'joint_state_broadcaster',
    ]
    ret.append(Node(
        package='controller_manager',
        executable='spawner',
        namespace=params['robot_id'],
        arguments=rbcar_joint_state_broadcaster,
        parameters=[robot_controller_config, {'use_sim_time': params['use_sim_time']}],
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
        parameters=[robot_controller_config, {'use_sim_time': params['use_sim_time']}],
        output='screen',
        condition=IfCondition(is_rbcar),
    ))

    ret.append(OpaqueFunction(
        function=_launch_spawn_rviz, args=[params],
        condition=IfCondition(params['run_spawn_rviz']),
    ))
    return ret


def _launch_spawn_rviz(context, params):
    override = params['spawn_rviz_config'].perform(context)
    config = ParameterFile(override or PathJoinSubstitution([
        FindPackageShare('robotnik_gazebo_ignition'), 'config', 'rviz_config.rviz',
    ]), allow_substs=True)
    path = str(config.evaluate(context))
    context.register_event_handler(OnShutdown(
        on_shutdown=lambda event, context: config.cleanup(),
    ))
    robot_id = params['robot_id'].perform(context)
    model = params['robot_model'].perform(context)
    return [Node(
        package='rviz2', executable='rviz2', name='spawn_rviz', namespace=robot_id,
        arguments=['-d', path, '-t', f'{robot_id} - {model} - basic RViz'],
        parameters=[{'use_sim_time': params['use_sim_time']}],
    )]


def generate_launch_description():
    raw_args = [
        ('robot_id', 'Unique Robot Identifier', 'robot'),
        ('robot', 'Robot Model Name', 'rbwatcher'),
        ('robot_model', 'Robot Variant or Type', LaunchConfiguration('robot')),
        ('robot_xacro_path', 'Path to Robot Xacro File', [FindPackageShare('robotnik_description'), '/robots/', LaunchConfiguration('robot'), '/', LaunchConfiguration('robot_model'), '.urdf.xacro']),
        ('frame_prefix', 'Prefix of each frame', [LaunchConfiguration('robot_id'), '_']),
        ('x', 'Initial X Coordinate', '0.0'),
        ('y', 'Initial Y Coordinate', '0.0'),
        ('z', 'Initial Z Coordinate', '0.0'),
        ('arm_type', 'Type of robotic arm', 'ur10e'),
        ('run_spawn_rviz', 'Run basic RViz', 'true'),
        ('spawn_rviz_config', 'Basic RViz configuration override', ''),
        ('use_sim_time', 'Use simulation time', 'True'),
        ('low_performance_simulation', 'Enable Low Performance Simulation', 'False'),
    ]

    ld = LaunchDescription([
        DeclareLaunchArgument(name, description=description, default_value=default)
        for name, description, default in raw_args
    ])
    params = {name: LaunchConfiguration(name) for name, _, _ in raw_args}
    ld.add_action(OpaqueFunction(function=launch_setup, args=[params]))
    return ld
