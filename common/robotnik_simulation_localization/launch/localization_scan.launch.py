import os
import yaml

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, LogInfo, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import ComposableNodeContainer, Node, PushRosNamespace
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def _load_scan_pipeline(context):
    robot = LaunchConfiguration("robot").perform(context)
    if robot:
        config_path = os.path.join(
            FindPackageShare("robotnik_simulation_robots").perform(context),
            robot,
            "localization",
            "localization_scan.yaml",
        )
        if not os.path.isfile(config_path):
            raise FileNotFoundError(
                f"Localization scan configuration for robot '{robot}' was not found at {config_path}."
            )
    else:
        config_path = os.path.join(
            FindPackageShare("robotnik_simulation_localization").perform(context),
            "config",
            "localization_scan.yaml",
        )

    with open(config_path, "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file) or {}, config_path


def _pointcloud_parameters(use_sim_time, frame_prefix, pcl_config):
    target_frame = pcl_config.get("target_frame", "base_link")
    return {
        "use_sim_time": use_sim_time,
        "target_frame": [frame_prefix, target_frame],
        "transform_tolerance": pcl_config.get("transform_tolerance", 0.2),
        "min_height": pcl_config.get("min_height", 0.0),
        "max_height": pcl_config.get("max_height", 1.0),
        "angle_min": pcl_config.get("angle_min", -2.3),
        "angle_max": pcl_config.get("angle_max", 2.3),
        "angle_increment": pcl_config.get("angle_increment", 0.008694),
        "range_min": pcl_config.get("range_min", 0.4),
        "range_max": pcl_config.get("range_max", 30.0),
        "use_inf": pcl_config.get("use_inf", True),
        "inf_epsilon": pcl_config.get("inf_epsilon", 1.0),
    }


def _build_pointcloud_to_laserscan(use_sim_time, frame_prefix, output_topic, pcl_config):
    input_topic = pcl_config.get("input_topic", "top_laser/points")
    parameters = _pointcloud_parameters(use_sim_time, frame_prefix, pcl_config)

    return [
        GroupAction([
            PushRosNamespace(LaunchConfiguration("robot_id")),
            Node(
                package="pointcloud_to_laserscan",
                executable="pointcloud_to_laserscan_node",
                name="localization_pointcloud_to_laserscan",
                output="screen",
                remappings=[
                    ("cloud_in", input_topic),
                    ("scan", output_topic),
                    ("tf", "/tf"),
                    ("tf_static", "/tf_static"),
                ],
                parameters=[parameters],
            )
        ])
    ]


def _build_passthrough(use_sim_time, output_topic, passthrough_config):
    input_topic = passthrough_config.get("input_topic", "front_laser/scan")
    return [
        GroupAction([
            PushRosNamespace(LaunchConfiguration("robot_id")),
            Node(
                package="topic_tools",
                executable="relay",
                name="localization_scan_relay",
                output="screen",
                arguments=[input_topic, output_topic],
                parameters=[{"use_sim_time": use_sim_time}],
                remappings=[
                    ("tf", "/tf"),
                    ("tf_static", "/tf_static"),
                ],
            )
        ])
    ]


def _merge_parameters(use_sim_time, frame_prefix, output_topic, merge_config, merge_inputs):
    target_frame = merge_config.get("target_frame", "base_link")
    return {
        "use_sim_time": use_sim_time,
        "laser_1_topic": merge_inputs[0],
        "laser_2_topic": merge_inputs[1],
        "merged_scan_topic": output_topic,
        "target_frame": [frame_prefix, target_frame],
        "laser_1_x_offset": merge_config.get("laser_1_x_offset", 0.0),
        "laser_1_y_offset": merge_config.get("laser_1_y_offset", 0.0),
        "laser_1_yaw_offset": merge_config.get("laser_1_yaw_offset", 0.0),
        "laser_2_x_offset": merge_config.get("laser_2_x_offset", 0.0),
        "laser_2_y_offset": merge_config.get("laser_2_y_offset", 0.0),
        "laser_2_yaw_offset": merge_config.get("laser_2_yaw_offset", 0.0),
        "tolerance": merge_config.get("tolerance", 0.01),
        "queue_size": merge_config.get("queue_size", 5),
        "publish_rate": merge_config.get("publish_rate", 100),
        "angle_increment": merge_config.get("angle_increment", 0.008694),
        "scan_time": merge_config.get("scan_time", 0.067),
        "range_min": merge_config.get("range_min", 0.05),
        "range_max": merge_config.get("range_max", 30.0),
        "min_height": merge_config.get("min_height", -1.0),
        "max_height": merge_config.get("max_height", 1.0),
        "angle_min": merge_config.get("angle_min", -3.141592654),
        "angle_max": merge_config.get("angle_max", 3.141592654),
        "inf_epsilon": merge_config.get("inf_epsilon", 1.0),
        "use_inf": merge_config.get("use_inf", True),
        "allowed_radius": merge_config.get("allowed_radius", 0.45),
        "enable_shadow_filter": merge_config.get("enable_shadow_filter", True),
        "enable_average_filter": merge_config.get("enable_average_filter", False),
    }


def _build_dual_laser_merge(use_sim_time, frame_prefix, output_topic, merge_config, merge_inputs):
    parameters = _merge_parameters(use_sim_time, frame_prefix, output_topic, merge_config, merge_inputs)

    return [
        GroupAction([
            PushRosNamespace(LaunchConfiguration("robot_id")),
            ComposableNodeContainer(
                name="localization_scan_merge_container",
                namespace="",
                package="rclcpp_components",
                executable="component_container",
                parameters=[{"use_sim_time": use_sim_time}],
                composable_node_descriptions=[
                    ComposableNode(
                        package="dual_laser_merger",
                        plugin="merger_node::MergerNode",
                        name="localization_dual_laser_merger",
                        parameters=[parameters],
                        remappings=[
                            ("tf", "/tf"),
                            ("tf_static", "/tf_static"),
                        ],
                    )
                ],
                output="screen",
            )
        ])
    ]


def _launch_setup(context, *_args, **_kwargs):
    use_sim_time = LaunchConfiguration("use_sim_time")
    frame_prefix = LaunchConfiguration("frame_prefix")
    robot = LaunchConfiguration("robot").perform(context)

    scan_pipeline, config_path = _load_scan_pipeline(context)
    if not scan_pipeline:
        return [
            LogInfo(
                msg=f"No localization scan pipeline configured for robot '{robot}' at {config_path}"
            )
        ]

    mode = scan_pipeline.get("mode")
    output_topic = scan_pipeline.get("output_topic", "localization/scan")

    if mode == "pointcloud_to_laserscan":
        pcl_config = scan_pipeline.get("pointcloud_to_laserscan", {})
        return _build_pointcloud_to_laserscan(use_sim_time, frame_prefix, output_topic, pcl_config)

    if mode == "passthrough":
        passthrough_config = scan_pipeline.get("passthrough", {})
        return _build_passthrough(use_sim_time, output_topic, passthrough_config)

    if mode == "merge":
        merge_config = scan_pipeline.get("merge", {})
        merge_inputs = merge_config.get("input_topics", [])
        if len(merge_inputs) != 2:
            return [
                LogInfo(
                    msg=(
                        f"Localization scan merge for robot '{robot}' requires exactly 2 input "
                        f"topics, got {len(merge_inputs)}."
                    )
                )
            ]
        return _build_dual_laser_merge(use_sim_time, frame_prefix, output_topic, merge_config, merge_inputs)

    return [
        LogInfo(
            msg=f"Unsupported localization scan mode '{mode}' for robot '{robot}'."
        )
    ]


def generate_launch_description():
    declared_arguments = [
        DeclareLaunchArgument(
            "robot_id",
            default_value="robot",
            description="Name for launch and config resources",
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use simulation time",
        ),
        DeclareLaunchArgument(
            "robot",
            default_value="",
            description="Optional robot profile used to resolve localization scan config",
        ),
        DeclareLaunchArgument(
            "frame_prefix",
            default_value=[LaunchConfiguration("robot_id"), "_"],
            description="Prefix for TF frames",
        ),
    ]

    group = GroupAction([
        OpaqueFunction(function=_launch_setup),
    ])

    return LaunchDescription(declared_arguments + [group])
