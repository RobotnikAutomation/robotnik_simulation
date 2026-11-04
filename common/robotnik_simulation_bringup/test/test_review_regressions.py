"""Launch/configuration regressions from simulation PR #78 (no ROS processes)."""
import importlib.util
from pathlib import Path

import pytest
import yaml
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile
from launch_ros.substitutions import FindPackageShare

ROOT = Path(__file__).resolve().parents[3]


def module(package, filename):
    directory = ROOT / ('common' if package != 'robotnik_gazebo_ignition' else '') / package
    path = directory / 'launch' / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.fixture(autouse=True)
def package_shares(monkeypatch, tmp_path):
    original = FindPackageShare.find

    def find(self, name):
        path = ROOT / 'common' / name
        if not path.is_dir():
            path = ROOT / name
        return str(path) if path.is_dir() else original(self, name)

    monkeypatch.setattr(FindPackageShare, 'find', find)
    monkeypatch.setenv('ROS_LOG_DIR', str(tmp_path / 'log'))


def context_for(launch, **overrides):
    context = LaunchContext()
    context.launch_configurations.update(overrides)
    for action in launch.generate_launch_description().entities:
        if isinstance(action, DeclareLaunchArgument):
            action.execute(context)
    return context


def includes(actions, context):
    found = []
    for action in actions:
        if action.condition and not action.condition.evaluate(context):
            continue
        if isinstance(action, IncludeLaunchDescription):
            action.launch_description_source.get_launch_description(context)
            path = action.launch_description_source.location
            args = {key: perform_substitutions(context, normalize_to_list_of_substitutions(value)) for key, value in action.launch_arguments}
            found.append((Path(path).name, args))
        else:
            found.extend(includes(action.get_sub_entities(), context))
    return found


@pytest.mark.parametrize('localization,navigation,mapping,internal,expected', [
    ('true', 'true', 'false', 'true', 1),
    ('true', 'true', 'true', 'true', 1),
    ('false', 'true', 'false', 'true', 1),
    ('true', 'false', 'true', 'true', 1),
    ('false', 'false', 'false', 'true', 0),
    ('true', 'true', 'true', 'false', 0),
    ('false', 'true', 'false', 'false', 0),
])
def test_bringup_scan_ownership(localization, navigation, mapping, internal, expected):
    launch = module('robotnik_simulation_bringup', 'bringup_complete.launch.py')
    context = context_for(launch, run_localization=localization, run_navigation=navigation,
                          run_mapping=mapping, run_scan_pipeline=internal, run_world='false')
    children = includes(launch._launch_setup(context), context)
    assert sum(name == 'localization_scan.launch.py' for name, _ in children) == expected
    for name, args in children:
        if name in ('localization.launch.py', 'navigation.launch.py'):
            assert args['run_scan_pipeline'] == 'false'
        if name == 'localization.launch.py':
            assert args['mapping_autostart'] == 'true'


@pytest.mark.parametrize('mapping', ['true', 'false'])
@pytest.mark.parametrize('internal', ['true', 'false'])
def test_standalone_localization_scan(mapping, internal):
    launch = module('robotnik_simulation_localization', 'localization.launch.py')
    context = context_for(launch, run_mapping=mapping, run_scan_pipeline=internal)
    children = includes(launch.generate_launch_description().entities, context)
    assert sum(name == 'localization_scan.launch.py' for name, _ in children) == (internal == 'true')
    assert sum(name == 'mapping_2d.launch.py' for name, _ in children) == (mapping == 'true')
    assert sum(name == 'localization_2d.launch.py' for name, _ in children) == (mapping == 'false')


@pytest.mark.parametrize('internal', ['true', 'false'])
def test_standalone_navigation_scan(internal):
    launch = module('robotnik_simulation_navigation', 'navigation.launch.py')
    context = context_for(launch, run_scan_pipeline=internal, run_navigation_rviz='false')
    children = includes(launch.generate_launch_description().entities, context)
    assert sum(name == 'localization_scan.launch.py' for name, _ in children) == (internal == 'true')


@pytest.mark.parametrize('robot,pipeline', [('rbsummit', 'pointcloud'), ('rb1', 'relay'), ('rbvogui', 'merge')])
def test_scan_modes_construct(robot, pipeline):
    launch = module('robotnik_simulation_localization', 'localization_scan.launch.py')
    context = context_for(launch, robot=robot, robot_id='fleet_beta', frame_prefix='custom_')
    actions = launch._launch_setup(context)
    assert actions
    def nodes(actions):
        for action in actions:
            if isinstance(action, Node):
                yield action
            else:
                yield from nodes(action.get_sub_entities())
    assert len(list(nodes(actions))) == 1


@pytest.mark.parametrize('mapping_autostart', ['true', 'false'])
def test_mapping_lifecycle_autostart(mapping_autostart):
    launch = module('robotnik_simulation_localization', 'mapping_2d.launch.py')
    context = context_for(launch, robot='rbsummit', mapping_autostart=mapping_autostart)
    group, = launch._launch_setup(context)
    nodes = [a for a in group.get_sub_entities() if isinstance(a, Node)]
    from launch_ros.utilities import evaluate_parameters
    params = [evaluate_parameters(context, node._Node__parameters) for node in nodes]
    manager = next(p for p in params if any(isinstance(x, dict) and 'autostart' in x for x in p))
    assert next(x['autostart'] for x in manager if isinstance(x, dict) and 'autostart' in x) == (mapping_autostart == 'true')


@pytest.mark.parametrize('custom', [False, True])
def test_spawn_rviz_default_and_override(custom, tmp_path):
    launch = module('robotnik_gazebo_ignition', 'spawn_robot.launch.py')
    override = tmp_path / 'custom.rviz'
    override.write_text('Visualization Manager:\n  Global Options:\n    Fixed Frame: $(var frame_prefix)odom\n')
    context = context_for(launch, robot_id='fleet_beta', frame_prefix='custom_',
                          spawn_rviz_config=str(override) if custom else '')
    from launch.substitutions import LaunchConfiguration
    params = {key: LaunchConfiguration(key) for key in context.launch_configurations}
    node, = launch._launch_spawn_rviz(context, params)
    args = [perform_substitutions(context, normalize_to_list_of_substitutions(x)) for x in node._Node__arguments]
    path = Path(args[args.index('-d') + 1])
    try:
        data = yaml.safe_load(path.read_text())
        assert data['Visualization Manager']['Global Options']['Fixed Frame'] == 'custom_odom'
    finally:
        path.unlink()


def test_spawn_rviz_missing_override(tmp_path):
    launch = module('robotnik_gazebo_ignition', 'spawn_robot.launch.py')
    context = context_for(launch, spawn_rviz_config=str(tmp_path / 'absent.rviz'))
    from launch.substitutions import LaunchConfiguration
    with pytest.raises(FileNotFoundError, match='Spawn RViz'):
        launch._launch_spawn_rviz(context, {k: LaunchConfiguration(k) for k in context.launch_configurations})


def test_navigation_rviz_custom_namespace():
    context = LaunchContext()
    context.launch_configurations.update(robot_id='fleet_beta', frame_prefix='custom_')
    config = ParameterFile(str(ROOT / 'common/robotnik_simulation_navigation/config/navigation.rviz'), allow_substs=True)
    try:
        data = yaml.safe_load(Path(config.evaluate(context)).read_text())
        assert data['Visualization Manager']['Global Options']['Fixed Frame'] == 'custom_map'
        teleop = next(p for p in data['Panels'] if p['Class'] == 'teleop_panel/Teleop')
        assert teleop['Topic'] == '/fleet_beta/robotnik_base_control/cmd_vel_unstamped'
    finally:
        config.cleanup()


def test_profile_scan_consumers_match():
    for path in (ROOT / 'common/robotnik_simulation_robots').glob('*/localization/localization_scan.yaml'):
        output = yaml.safe_load(path.read_text())['output_topic']
        for filename in ('amcl.yaml', 'slam_toolbox.yaml'):
            data = yaml.safe_load((path.parent / filename).read_text())['/**']
            assert all(node['ros__parameters']['scan_topic'] == output for node in data.values())
