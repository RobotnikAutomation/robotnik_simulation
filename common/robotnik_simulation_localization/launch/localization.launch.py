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

from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import GroupAction, DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition


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
            description="Optional robot profile used to resolve localization configs"
        ),
        DeclareLaunchArgument(
            "frame_prefix",
            default_value=[LaunchConfiguration("robot_id"), "_"],
            description="Prefix for TF frames"
        ),
        DeclareLaunchArgument(
            "run_mapping",
            default_value="false",
            description="Run mapping instead of localization"
        ),
    ]

    robot_id = LaunchConfiguration("robot_id")
    use_sim_time = LaunchConfiguration("use_sim_time")
    robot = LaunchConfiguration("robot")
    frame_prefix = LaunchConfiguration("frame_prefix")
    run_mapping = LaunchConfiguration("run_mapping")

    localization_scan = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                 FindPackageShare('robotnik_simulation_localization'), 'launch/localization_scan.launch.py'
            ])
        ),
        launch_arguments={
            'robot_id': robot_id,
            'use_sim_time': use_sim_time,
            'robot': robot,
            'frame_prefix': frame_prefix,
        }.items(),
        condition=UnlessCondition(run_mapping)
    )

    localization_2d = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                 FindPackageShare('robotnik_simulation_localization'), 'launch/localization_2d.launch.py'
            ])
        ),
        launch_arguments={
            'robot_id': robot_id,
            'use_sim_time': use_sim_time,
            'robot': robot,
            'frame_prefix': frame_prefix,
        }.items(),
        condition=UnlessCondition(run_mapping)
    )

    mapping_2d = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                 FindPackageShare('robotnik_simulation_localization'), 'launch/mapping_2d.launch.py'
            ])
        ),
        launch_arguments={
            'robot_id': robot_id,
            'use_sim_time': use_sim_time,
            'robot': robot,
            'frame_prefix': frame_prefix,
        }.items(),
        condition=IfCondition(run_mapping)
    )

    group = GroupAction([
        GroupAction([localization_scan], scoped=True),
        GroupAction([localization_2d], scoped=True),
        GroupAction([mapping_2d], scoped=True)
    ])

    return LaunchDescription(declared_arguments + [group])
