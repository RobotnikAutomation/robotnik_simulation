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

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch.substitutions import Command, FindExecutable
from ament_index_python.packages import get_package_share_directory


def load_yaml(package_path, relative_path):
    full_path = os.path.join(package_path, relative_path)
    with open(full_path, 'r') as f:
        return yaml.safe_load(f)


def launch_setup(context, *args, **kwargs):
    robot_id = LaunchConfiguration('robot_id').perform(context)
    robot_model = LaunchConfiguration('robot_model').perform(context)
    robot_xacro_path = LaunchConfiguration('robot_xacro_path').perform(context)
    moveit_config_name = LaunchConfiguration('moveit_config_name').perform(context)
    arm_type = LaunchConfiguration('arm_type').perform(context)

    moveit_config_pkg = get_package_share_directory(moveit_config_name)

    def resolve_model_name_for_file(extension):
        package_model = moveit_config_name.replace('_moveit_config', '')
        candidates = [robot_model, package_model]
        if robot_model.startswith('centauro_'):
            candidates.append(robot_model[len('centauro_'):])
        if package_model.startswith('centauro_'):
            candidates.append(package_model[len('centauro_'):])

        for candidate in candidates:
            file_path = os.path.join(moveit_config_pkg, 'config', f'{candidate}{extension}')
            if os.path.exists(file_path):
                return file_path

        raise FileNotFoundError(
            f"No model file '*{extension}' found for candidates {candidates} in {moveit_config_pkg}/config"
        )

    srdf_path = resolve_model_name_for_file('.srdf')
    default_moveit_configs = '/opt/ros/jazzy/share/moveit_configs_utils/'

    robot_description = {
        'robot_description': ParameterValue(
            Command([
                FindExecutable(name='xacro'), ' ', robot_xacro_path, ' ',
                f'namespace:={robot_id}', ' ',
                f'prefix:={robot_id}_', ' ',
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
                f'namespace:={robot_id}_',
            ]),
            value_type=str,
        )
    }

    robot_description_kinematics = {
        'robot_description_kinematics': load_yaml(moveit_config_pkg, 'config/kinematics.yaml')
    }

    planning_description_yaml = {
        'robot_description_planning': {
            **load_yaml(moveit_config_pkg, 'config/joint_limits.yaml'),
            **load_yaml(moveit_config_pkg, 'config/pilz_cartesian_limits.yaml'),
        }
    }

    ompl_yaml = {
        'ompl': {
            'planning_plugins': ['ompl_interface/OMPLPlanner'],
            'request_adapters': [
                'default_planning_request_adapters/ResolveConstraintFrames',
                'default_planning_request_adapters/ValidateWorkspaceBounds',
                'default_planning_request_adapters/CheckStartStateBounds',
                'default_planning_request_adapters/CheckStartStateCollision',
            ],
            'response_adapters': [
                'default_planning_response_adapters/AddTimeOptimalParameterization',
            ],
            'start_state_max_bounds_error': 0.1,
            **load_yaml(default_moveit_configs, 'default_configs/ompl_planning.yaml'),
        }
    }

    pilz_industrial_motion_planner_yaml = {
        'pilz_industrial_motion_planner': {
            'default_planner_config': 'PTP',
            **load_yaml(default_moveit_configs, 'default_configs/pilz_industrial_motion_planner_planning.yaml'),
        }
    }

    stomp_yaml = {
        'stomp': {
            **load_yaml(default_moveit_configs, 'default_configs/stomp_planning.yaml'),
        }
    }

    chomp_yaml = {
        'chomp': {
            **load_yaml(default_moveit_configs, 'default_configs/chomp_planning.yaml'),
        }
    }

    planning_pipeline_config = {
        'planning_pipelines': ['ompl', 'chomp', 'pilz_industrial_motion_planner', 'stomp'],
        'default_planning_pipeline': 'pilz_industrial_motion_planner',
    }

    controllers_yaml = load_yaml(moveit_config_pkg, 'config/moveit_controllers.yaml')

    trajectory_execution = {
        'moveit_manage_controllers': False,
        'trajectory_execution.allowed_execution_duration_scaling': 1.2,
        'trajectory_execution.allowed_goal_duration_margin': 0.5,
        'trajectory_execution.allowed_start_tolerance': 0.01,
    }

    planning_scene_monitor_parameters = {
        'publish_planning_scene': True,
        'publish_geometry_updates': True,
        'publish_state_updates': True,
        'publish_transforms_updates': True,
        'publish_robot_description': True,
        'publish_robot_description_semantic': True,
    }

    use_sim_time = {'use_sim_time': True}

    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        namespace=robot_id,
        output='screen',
        parameters=[
            use_sim_time,
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            planning_description_yaml,
            ompl_yaml,
            pilz_industrial_motion_planner_yaml,
            stomp_yaml,
            chomp_yaml,
            controllers_yaml,
            planning_pipeline_config,
            trajectory_execution,
            planning_scene_monitor_parameters,
        ],
    )

    return [move_group_node]


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
            default_value=LaunchConfiguration('robot'),
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
            'moveit_config_name',
            default_value='rbkairos_moveit_config',
            description='MoveIt configuration package name',
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
    ]

    return LaunchDescription(
        declared_arguments + [OpaqueFunction(function=launch_setup)]
    )
