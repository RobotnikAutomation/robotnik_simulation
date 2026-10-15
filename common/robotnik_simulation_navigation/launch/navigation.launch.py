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
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.event_handlers import OnShutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile
from launch_ros.substitutions import FindPackageShare


def _launch_rviz(context):
    override = LaunchConfiguration("navigation_rviz_config").perform(context)
    config = ParameterFile(override or PathJoinSubstitution([
        FindPackageShare("robotnik_simulation_navigation"), "config", "navigation.rviz",
    ]), allow_substs=True)
    path = str(config.evaluate(context))
    context.register_event_handler(OnShutdown(
        on_shutdown=lambda event, context: config.cleanup(),
    ))
    robot_id = LaunchConfiguration("robot_id").perform(context)
    return [Node(
        package="rviz2", executable="rviz2", name="navigation_rviz", namespace=robot_id,
        output="screen",
        parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
        arguments=["-d", path, "-t", f"{robot_id} - navigation RViz"],
    )]


def generate_launch_description():
    arguments = [
        DeclareLaunchArgument("robot_id", default_value="robot"),
        DeclareLaunchArgument("robot", default_value="", description="Optional robot profile"),
        DeclareLaunchArgument("frame_prefix", default_value=[LaunchConfiguration("robot_id"), "_"]),
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        DeclareLaunchArgument("run_navigation_rviz", default_value="true"),
        DeclareLaunchArgument("navigation_rviz_config", default_value="", description="Empty selects the package RViz configuration"),
    ]
    common = {name: LaunchConfiguration(name) for name in ("robot_id", "robot", "frame_prefix", "use_sim_time")}
    children = [GroupAction([IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare("robotnik_simulation_navigation"), "launch", filename,
        ])), launch_arguments=common.items(),
    )], scoped=True) for filename in ("nav2_task.launch.py", "nav2_mission.launch.py")]
    return LaunchDescription(arguments + children + [OpaqueFunction(
        function=_launch_rviz, condition=IfCondition(LaunchConfiguration("run_navigation_rviz")),
    )])
