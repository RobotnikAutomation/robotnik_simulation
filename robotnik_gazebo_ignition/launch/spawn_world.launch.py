# Copyright (c) 2022, Robotnik Automation S.L.L.
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
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    arguments = [
        DeclareLaunchArgument("world", default_value="demo", description="Built-in Gazebo world name"),
        DeclareLaunchArgument("world_path", default_value=[
            FindPackageShare("robotnik_gazebo_ignition"), "/worlds/", LaunchConfiguration("world"), ".world",
        ], description="World file override"),
        DeclareLaunchArgument("run_gazebo_gui", default_value="true"),
        DeclareLaunchArgument(
            "use_nvidia_gpu", default_value="false",
            description="Request NVIDIA PRIME render offload for Gazebo server and GUI",
        ),
    ]
    def source():
        # LaunchDescriptionSource caches actions; server and GUI need distinct instances.
        return PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py",
        ]))

    server = IncludeLaunchDescription(source(), launch_arguments={
        "gz_args": ["-r -s ", LaunchConfiguration("world_path")],
        "on_exit_shutdown": "true",
    }.items())
    gui = IncludeLaunchDescription(source(), launch_arguments={
        "gz_args": "-g", "on_exit_shutdown": "true",
    }.items())
    clock = Node(
        package="ros_gz_bridge", executable="parameter_bridge", name="gz_clock_bridge",
        output="screen", arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
    )
    return LaunchDescription(arguments + [
        GroupAction([
            SetEnvironmentVariable(
                "__NV_PRIME_RENDER_OFFLOAD", "1",
                condition=IfCondition(LaunchConfiguration("use_nvidia_gpu")),
            ),
            SetEnvironmentVariable(
                "__GLX_VENDOR_LIBRARY_NAME", "nvidia",
                condition=IfCondition(LaunchConfiguration("use_nvidia_gpu")),
            ),
            GroupAction([server], scoped=True),
            GroupAction([gui], scoped=True, condition=IfCondition(LaunchConfiguration("run_gazebo_gui"))),
        ], scoped=True),
        clock,
    ])
