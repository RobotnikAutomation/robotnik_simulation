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
import yaml
import tempfile
import xml.etree.ElementTree as ET

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.event_handlers import OnShutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile, ParameterValue
from launch.substitutions import Command, FindExecutable
from robotnik_simulation_moveit.profiles import resolve_manipulation_profile


def load_yaml(package_path, relative_path):
    full_path = os.path.join(package_path, relative_path)
    with open(full_path, 'r') as f:
        return yaml.safe_load(f)


def load_config(context, source_file):
    config_file = ParameterFile(source_file, allow_substs=True)
    try:
        with open(config_file.evaluate(context), 'r') as config_stream:
            return yaml.safe_load(config_stream)
    finally:
        config_file.cleanup()


def launch_setup(context, *args, **kwargs):
    robot_id = LaunchConfiguration('robot_id').perform(context)
    robot = LaunchConfiguration('robot').perform(context)
    robot_model = LaunchConfiguration('robot_model').perform(context)
    robot_xacro_path = LaunchConfiguration('robot_xacro_path').perform(context)
    arm_type = LaunchConfiguration('arm_type').perform(context)
    moveit_rviz_config = LaunchConfiguration('moveit_rviz_config').perform(context)
    use_fixed_frame_str = LaunchConfiguration('use_fixed_frame').perform(context)
    frame_prefix = LaunchConfiguration('frame_prefix').perform(context)
    use_sim_time = LaunchConfiguration('use_sim_time').perform(context)
    use_fixed_frame = use_fixed_frame_str.strip().lower() in ('true', '1', 'yes', 'on')

    manipulation_config_dir, srdf_path = resolve_manipulation_profile(
        context, robot, robot_model
    )
    custom_rviz_config = bool(moveit_rviz_config)
    if not custom_rviz_config:
        moveit_rviz_config = os.path.join(
            FindPackageShare('robotnik_simulation_moveit').perform(context), 'config', 'moveit.rviz',
        )
    if not os.path.isfile(moveit_rviz_config):
        raise RuntimeError(
            f"MoveIt RViz configuration was not found: {moveit_rviz_config}"
        )

    default_moveit_configs = FindPackageShare('moveit_configs_utils').perform(context)

    robot_description = {
        'robot_description': ParameterValue(
            Command([
                FindExecutable(name='xacro'), ' ', robot_xacro_path, ' ',
                f'namespace:={robot_id}', ' ',
                f'prefix:={frame_prefix}', ' ',
                'gazebo_ignition:=true', ' ',
                f'ur_type:={arm_type}',
            ]),
            value_type=str,
        )
    }

    robot_description_semantic = {
        'robot_description_semantic': ParameterValue(
            Command([
                FindExecutable(name='xacro'), ' ', srdf_path, ' ',
                f'prefix:={frame_prefix}',
            ]),
            value_type=str,
        )
    }

    robot_description_kinematics_raw = load_config(
        context,
        os.path.join(manipulation_config_dir, 'kinematics.yaml'),
    )
    joint_limits = {
        'robot_description_planning': {
            **load_config(
                context,
                os.path.join(manipulation_config_dir, 'joint_limits.yaml'),
            ),
            **load_config(
                context,
                os.path.join(manipulation_config_dir, 'pilz_cartesian_limits.yaml'),
            ),
        }
    }
    planning_pipelines = {
        'planning_pipelines': ['ompl', 'chomp', 'pilz_industrial_motion_planner', 'stomp'],
        'default_planning_pipeline': 'pilz_industrial_motion_planner',
        'ompl': {
            **load_yaml(default_moveit_configs, 'default_configs/ompl_planning.yaml'),
        },
        'pilz_industrial_motion_planner': {
            **load_config(
                context,
                os.path.join(manipulation_config_dir, 'pilz_industrial_motion_planner_planning.yaml'),
            ),
        },
        'stomp': {
            **load_yaml(default_moveit_configs, 'default_configs/stomp_planning.yaml'),
        },
        'chomp': {
            **load_yaml(default_moveit_configs, 'default_configs/chomp_planning.yaml'),
        },
    }

    # RViz-safe kinematics: keep only solver plugin names to avoid Jazzy
    # parameter type conflicts seen with numeric kinematics fields.
    rviz_robot_description_kinematics = {'robot_description_kinematics': {}}
    for group_name, group_cfg in robot_description_kinematics_raw.items():
        if isinstance(group_cfg, dict) and 'kinematics_solver' in group_cfg:
            rviz_robot_description_kinematics['robot_description_kinematics'][group_name] = {
                'kinematics_solver': group_cfg['kinematics_solver']
            }

    use_sim_time = {'use_sim_time': use_sim_time.strip().lower() in ('true', '1', 'yes', 'on')}

    # RViz consumes a CLI path; keep the resolved file alive until shutdown.
    rviz_config = ParameterFile(moveit_rviz_config, allow_substs=True)
    rviz_config_path = str(rviz_config.evaluate(context))
    # Resolve the existing semantic description for this view; do not alter the SRDF
    # or any configuration passed to move_group.
    semantic_xml = robot_description_semantic['robot_description_semantic'].evaluate(context)
    groups = [group.attrib['name'] for group in ET.fromstring(semantic_xml).findall('group')]
    if not groups:
        rviz_config.cleanup()
        raise RuntimeError(f"MoveIt RViz requires at least one planning group in {srdf_path}")
    generated_config_path = None
    if not custom_rviz_config:
        with open(rviz_config_path, encoding='utf-8') as stream:
            view = yaml.safe_load(stream)
        for display in view['Visualization Manager']['Displays']:
            if display.get('Class') == 'moveit_rviz_plugin/MotionPlanning':
                request = display.setdefault('Planning Request', {})
                if len(groups) == 1:
                    request['Planning Group'] = groups[0]
                else:
                    request.pop('Planning Group', None)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rviz', delete=False) as stream:
            yaml.safe_dump(view, stream, sort_keys=False)
            generated_config_path = stream.name
        rviz_config_path = generated_config_path

    def cleanup(event, context):
        rviz_config.cleanup()
        if generated_config_path and os.path.exists(generated_config_path):
            os.unlink(generated_config_path)

    context.register_event_handler(OnShutdown(
        on_shutdown=cleanup,
    ))

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='moveit_rviz',
        arguments=[
            *(['-f', f'{frame_prefix}odom'] if use_fixed_frame else []),
            '-d', rviz_config_path,
            '-t', f'{robot_id} - {robot_model} - manipulation RViz',
        ],
        parameters=[
            use_sim_time,
            robot_description,
            robot_description_semantic,
            rviz_robot_description_kinematics,
            joint_limits,
            planning_pipelines,
        ],
    )

    return [rviz_node]


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument(
            'robot_id',
            default_value='robot',
            description='Unique Robot Identifier',
        ),
        DeclareLaunchArgument(
            'robot',
            default_value='rbkairos',
            description='Robot Model Name',
        ),
        DeclareLaunchArgument(
            'robot_model',
            default_value='rbkairos_plus',
            description='Robot Variant or Type',
        ),
        DeclareLaunchArgument(
            'robot_xacro_path',
            default_value=[
                FindPackageShare('robotnik_description'), '/robots/',
                LaunchConfiguration('robot'), '/', LaunchConfiguration('robot_model'), '.urdf.xacro',
            ],
            description='Path to Robot Xacro File',
        ),
        DeclareLaunchArgument(
            'arm_type',
            default_value='ur10e',
            description='Type of robotic arm',
        ),
        DeclareLaunchArgument(
            'frame_prefix',
            default_value=[LaunchConfiguration('robot_id'), '_'],
            description='Prefix for TF frames and joint names',
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time',
        ),
        DeclareLaunchArgument(
            'moveit_rviz_config',
            default_value='',
            description='RViz override; empty selects the package generic view',
        ),
        DeclareLaunchArgument(
            'use_fixed_frame',
            default_value='false',
            description='Use fixed frame (-f <robot_id>_odom) for RViz',
        ),
    ]

    return LaunchDescription(
        declared_arguments + [OpaqueFunction(function=launch_setup)]
    )
