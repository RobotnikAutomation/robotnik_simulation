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

from launch_ros.actions import Node
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch_ros.substitutions import FindPackageShare
from launch.actions import DeclareLaunchArgument, GroupAction, OpaqueFunction
from launch_ros.actions import PushRosNamespace
from launch_ros.parameter_descriptions import ParameterFile

def _resolve_slam_toolbox_config(context):
    robot = LaunchConfiguration("robot").perform(context)
    if robot:
        profile_config = os.path.join(
            FindPackageShare("robotnik_simulation_robots").perform(context),
            robot,
            "localization",
            "slam_toolbox.yaml",
        )
        if not os.path.isfile(profile_config):
            raise FileNotFoundError(
                f"SLAM configuration for robot '{robot}' was not found at {profile_config}."
            )
        return profile_config

    return os.path.join(
        FindPackageShare("robotnik_simulation_localization").perform(context),
        "config",
        "slam_toolbox.yaml",
    )

def _launch_setup(context, *_args, **_kwargs):
    robot_id = LaunchConfiguration("robot_id")
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")
    slam_toolbox_config = _resolve_slam_toolbox_config(context)

    slam_toolbox_params = ParameterFile(slam_toolbox_config, allow_substs=True)

    slam_toolbox_mapping = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox_mapping',
        output='screen',
        parameters=[
            slam_toolbox_params,
            {
                'use_sim_time': use_sim_time,
                'use_lifecycle_manager': True,
            }
        ],
        remappings=[
            ('/map', 'map')  # Remap to a relative topic within the robot namespace
        ]
    )

    map_saver = Node(
            package='nav2_map_server',
            executable='map_saver_server',
            name='map_saver',
            output='screen',
            parameters=[
            {
                'use_sim_time': use_sim_time
            }]
        )

    lifecycle_manager_mapping = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_mapping',
        output='screen',
        parameters=[
            {
                'use_sim_time': use_sim_time,
                'autostart': False,
                'node_names': [
                    'slam_toolbox_mapping',
                    'map_saver'
                ],
                'bond_timeout': 4.0
            }
        ]
    )

    group = GroupAction([
        PushRosNamespace(robot_id),
        slam_toolbox_mapping,
        map_saver,
        lifecycle_manager_mapping
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
            description="Optional robot profile used to resolve SLAM config"
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
