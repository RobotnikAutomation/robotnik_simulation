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

from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node, PushRosNamespace
from launch.actions import DeclareLaunchArgument, GroupAction, OpaqueFunction
from launch_ros.parameter_descriptions import ParameterFile


def _resolve_amcl_config(context):
    robot = LaunchConfiguration("robot").perform(context)
    if robot:
        config_path = os.path.join(
            FindPackageShare("robotnik_simulation_robots").perform(context),
            robot,
            "localization",
            "amcl.yaml",
        )
        if not os.path.isfile(config_path):
            raise FileNotFoundError(
                f"AMCL configuration for robot '{robot}' was not found at {config_path}."
            )
    else:
        config_path = os.path.join(
            FindPackageShare("robotnik_simulation_localization").perform(context),
            "config",
            "amcl.yaml",
        )
    return ParameterFile(config_path, allow_substs=True)

def _launch_setup(context, *_args, **_kwargs):
    robot_id = LaunchConfiguration("robot_id")
    use_sim_time = LaunchConfiguration("use_sim_time")
    frame_prefix = LaunchConfiguration("frame_prefix")

    map_file = PathJoinSubstitution([
        FindPackageShare('robotnik_simulation_localization'),
        'maps/demo_map/demo_map.yaml'
    ])

    amcl_params = _resolve_amcl_config(context)

    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[
            {
                'use_sim_time': use_sim_time,
                'yaml_filename': map_file,
                'frame_id': [frame_prefix, 'map']
            }
        ]
    )
            
    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[
            amcl_params,
            {
                'use_sim_time': use_sim_time,
            }
        ]
    )

    lifecycle_manager_localization = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters = [
            {
                'use_sim_time': use_sim_time,
                'autostart': True,
                'node_names': [
                    'map_server',
                    'amcl'
                ]
            }
        ]
    )

    group = GroupAction([
        PushRosNamespace(robot_id),
        map_server,
        amcl,
        lifecycle_manager_localization,
    ])

    return [group]

def generate_launch_description():

    declared_arguments = [
        DeclareLaunchArgument(
            "robot_id",
            default_value="robot",
            description="Name for launch and config resources"
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use simulation time"
        ),
        DeclareLaunchArgument(
            "robot",
            default_value="",
            description="Optional robot profile used to resolve AMCL config"
        ),
        DeclareLaunchArgument(
            "frame_prefix",
            default_value=[LaunchConfiguration("robot_id"), "_"],
            description="Prefix for TF frames"
        ),
    ]

    group = GroupAction([
        OpaqueFunction(function=_launch_setup),
    ])

    return LaunchDescription(declared_arguments + [group])
