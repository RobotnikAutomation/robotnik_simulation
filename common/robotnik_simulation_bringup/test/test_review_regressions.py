"""Launch/configuration regressions from simulation PR #78 (no ROS processes)."""
import importlib.util
from pathlib import Path

import pytest
import yaml
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
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
            children = action.actions if isinstance(action, TimerAction) else action.get_sub_entities()
            found.extend(includes(children, context))
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


def test_variant_bridge_resolution(tmp_path):
    from robotnik_simulation_robots.profiles import resolve_variant_file
    default = tmp_path / 'family_bridges.yaml'
    default.write_text('bridges: []\n')
    assert resolve_variant_file(tmp_path, 'family', 'variant', '_bridges.yaml') == str(default)
    variant = tmp_path / 'variant_bridges.yaml'
    variant.write_text('bridges: []\n')
    assert resolve_variant_file(tmp_path, 'family', 'variant', '_bridges.yaml') == str(variant)
    with pytest.raises(FileNotFoundError, match='unknown_bridges.yaml.*absent_bridges.yaml'):
        resolve_variant_file(tmp_path, 'absent', 'unknown', '_bridges.yaml')


def test_explicit_family_never_uses_generic_config():
    from robotnik_simulation_robots.profiles import resolve_config
    context = LaunchContext()
    generic = resolve_config(context, '', 'localization', 'amcl.yaml', 'robotnik_simulation_localization')
    assert Path(generic).is_file()
    with pytest.raises(FileNotFoundError, match='nonexistent_family'):
        resolve_config(context, 'nonexistent_family', 'localization', 'amcl.yaml',
                       'robotnik_simulation_localization')


def test_moveit_missing_and_complete_profiles():
    from robotnik_simulation_robots.profiles import has_manipulation, resolve_manipulation_profile
    context = LaunchContext()
    assert not has_manipulation(context, 'rbsummit', 'rbsummit')
    assert has_manipulation(context, 'rbkairos', 'rbkairos_plus')
    directory, srdf = resolve_manipulation_profile(context, 'rbkairos', 'rbkairos_plus')
    assert Path(srdf).parent == Path(directory)
    with pytest.raises(RuntimeError, match='Missing files:'):
        resolve_manipulation_profile(context, 'rbsummit', 'rbsummit')


def test_moveit_incomplete_profile_rejected_before_bringup(monkeypatch, tmp_path):
    (tmp_path / 'family/manipulation').mkdir(parents=True)
    (tmp_path / 'family/manipulation/variant.srdf').write_text('<robot/>')
    original = FindPackageShare.find
    monkeypatch.setattr(FindPackageShare, 'find',
                        lambda self, name: str(tmp_path) if name == 'robotnik_simulation_robots'
                        else original(self, name))
    launch = module('robotnik_simulation_bringup', 'bringup_complete.launch.py')
    context = context_for(launch, robot='family', robot_model='variant', run_moveit='true',
                          run_navigation='false', run_localization='false')
    with pytest.raises(RuntimeError, match='kinematics.yaml'):
        launch._launch_setup(context)


def test_shared_yaml_load_substitutes_and_cleans_up(monkeypatch, tmp_path):
    from robotnik_simulation_robots.profiles import load_config
    context = LaunchContext()
    context.launch_configurations['frame_prefix'] = 'fleet_'
    source = tmp_path / 'kinematics.yaml'
    source.write_text('frame: $(var frame_prefix)base_link\n')
    cleaned = []
    original = ParameterFile.cleanup

    def cleanup(self):
        cleaned.append(True)
        original(self)

    monkeypatch.setattr(ParameterFile, 'cleanup', cleanup)
    assert load_config(context, str(source)) == {'frame': 'fleet_base_link'}
    assert cleaned
    assert '$(var frame_prefix)' in source.read_text()


def test_bringup_checks_mapping_profile_without_requiring_amcl(monkeypatch, tmp_path):
    directory = tmp_path / 'family/localization'
    directory.mkdir(parents=True)
    (directory / 'slam_toolbox.yaml').write_text('{}')
    original = FindPackageShare.find
    monkeypatch.setattr(FindPackageShare, 'find',
                        lambda self, name: str(tmp_path) if name == 'robotnik_simulation_robots'
                        else original(self, name))
    launch = module('robotnik_simulation_bringup', 'bringup_complete.launch.py')
    context = context_for(launch, robot='family', run_mapping='true', run_scan_pipeline='false',
                          run_navigation='false', run_world='false')
    children = includes(launch._launch_setup(context), context)
    assert any(name == 'localization.launch.py' for name, _ in children)


def test_missing_internal_scan_skips_dependent_modules(monkeypatch):
    launch = module('robotnik_simulation_bringup', 'bringup_complete.launch.py')
    original = launch.missing_profile_files
    monkeypatch.setattr(launch, 'missing_profile_files',
                        lambda context, robot, component, files: ['missing scan']
                        if tuple(files) == ('localization_scan.yaml',)
                        else original(context, robot, component, files))
    context = context_for(launch, run_world='false')
    children = includes(launch._launch_setup(context), context)
    assert [name for name, _ in children] == ['spawn_robot.launch.py']


def test_installed_profile_resources_are_preserved():
    from ament_index_python.packages import get_package_share_directory
    installed = Path(get_package_share_directory('robotnik_simulation_robots'))
    source = ROOT / 'common/robotnik_simulation_robots'
    profiles = list(source.glob('*/control/*.yaml')) + list(source.glob('*/localization/*.yaml'))
    assert profiles
    for path in profiles:
        assert (installed / path.relative_to(source)).is_file(), path.relative_to(source)
