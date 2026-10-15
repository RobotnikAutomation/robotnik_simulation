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
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


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
            'run_moveit_rviz',
            default_value='true',
            description='Run MoveIt RViz for manipulation',
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

    common_args = {
        'robot_id': LaunchConfiguration('robot_id'),
        'robot': LaunchConfiguration('robot'),
        'robot_model': LaunchConfiguration('robot_model'),
        'robot_xacro_path': LaunchConfiguration('robot_xacro_path'),
        'arm_type': LaunchConfiguration('arm_type'),
        'frame_prefix': LaunchConfiguration('frame_prefix'),
        'use_sim_time': LaunchConfiguration('use_sim_time'),
    }

    move_group = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('robotnik_simulation_moveit'), 'launch/move_group.launch.py',
            ])
        ),
        launch_arguments=common_args.items(),
    )

    moveit_rviz = TimerAction(
        period=1.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([
                        FindPackageShare('robotnik_simulation_moveit'), 'launch/moveit_rviz.launch.py',
                    ])
                ),
                launch_arguments={
                    **common_args,
                    'moveit_rviz_config': LaunchConfiguration('moveit_rviz_config'),
                    'use_fixed_frame': LaunchConfiguration('use_fixed_frame'),
                }.items(),
                condition=IfCondition(LaunchConfiguration('run_moveit_rviz')),
            )
        ],
    )

    return LaunchDescription(declared_arguments + [move_group, GroupAction([moveit_rviz], scoped=True)])
