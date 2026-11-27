#!/usr/bin/env python3
# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring
import os
import shlex
import sys

from argparse import ArgumentParser
from functools import lru_cache
from pathlib import Path
from typing import FrozenSet, Iterable, List, NoReturn, Set, Tuple

import yaml

from testlib import (
    ANSIBLE_NO_PROMPT_ENV,
    COLLECTIONS,
    NAMESPACE_PATH,
    Color,
    OutputMode,
    ProjectPath,
    ProjectRoleMeta,
    RC,
    chdir_project,
    error_code,
    nothing_to_test,
    print_debug,
    print_hint,
    print_warning,
    require_commands,
    run_shell_get_lines,
    run_test_cmd,
    run_tests_parallel,
    select_changed_paths,
    select_given_fqcns,
    split_passthrough_args,
)

# Roles of these collections are selected only directly, never as dependents of affected roles.
CLOSURE_EXCLUDED_COLLECTIONS = ("environments",)
SCENARIOS_DIR = Path("extensions") / "molecule"

# Changes to the shared molecule framework, tooling and plugins affect every role.
# oszi.utils.bootstrap and testlib are not part of the framework.
FRAMEWORK_PATTERNS = (
    "_scripts/tests/molecule.py",
    "requirements.txt",
    "requirements.yml",
    f"{NAMESPACE_PATH}/utils/playbooks/molecule/",
    *(f"{NAMESPACE_PATH}/{collection}/plugins/" for collection in COLLECTIONS),
    *(f"{NAMESPACE_PATH}/{collection}/{SCENARIOS_DIR}/*" for collection in COLLECTIONS),
)

MOLECULE_CMD = ["molecule"]
MOLECULE_DEFAULT_ARGS = ["test"]

MOLECULE_INSTANCE_COMMANDS = ("check", "converge", "create", "prepare", "test")
MOLECULE_VALUE_OPTIONS = ("-c", "--base-config", "-e", "--env-file")

BUILD_PLAYBOOK_CMD = ["ansible-playbook", "-i", "localhost,"]
BUILD_PLAYBOOK = "oszi.utils.molecule.build"

INOTIFY_MAX_USER_INSTANCES_PATH = Path("/proc/sys/fs/inotify/max_user_instances")

args_parser = ArgumentParser(
    usage="molecule.py [--help] [--all] [--ignore-framework] [--list] [--workers N] [FQCN ...] [-- MOLECULE_ARGS ...]",
    description="Run molecule scenarios of the roles affected since the previous release, "
    "of the given roles or collections (e.g. oszi.general.shell, oszi.utils), or of everything.",
    epilog="Molecule arguments after -- replace the default 'test', e.g. -- converge. "
    "Images are built once automatically. See MOLECULE.md and README.md.",
)

args_parser.add_argument("--all", help="run the scenarios of all roles", action="store_true")
args_parser.add_argument("--ignore-framework", help="select only the roles touched directly", action="store_true")
args_parser.add_argument("--list", help="list selected scenarios without running anything", action="store_true")
args_parser.add_argument("--workers", help="number of parallel scenarios (<1 for auto)", type=int, default=0)
args_parser.add_argument("fqcns", help="[FQCN ...]", nargs="*")


@lru_cache(maxsize=None)
def _all_roles() -> Tuple[ProjectRoleMeta, ...]:
    """All roles as ProjectRoleMeta in a cached, ordered, immutable tuple."""
    return tuple(ProjectRoleMeta.all_collection_roles())


def _all_roles_fqcn() -> Set[str]:
    """All roles as FQCNs."""
    return {role.fqcn for role in _all_roles()}


@lru_cache(maxsize=None)
def _collection_scenario_files(collection_dir: ProjectPath) -> Tuple[ProjectPath, ...]:
    """All scenario paths (molecule.yml) in a collection as a cached, ordered, immutable tuple."""
    return tuple(sorted((collection_dir / SCENARIOS_DIR).glob("*/molecule.y*ml")))


@lru_cache(maxsize=None)
def _scenario_converged_roles(scenario_path: Path) -> FrozenSet[str]:
    """FQCNs listed in molecule_converge_roles of a scenario's inventory group_vars; parsed once per scenario."""
    try:
        with scenario_path.open("r", encoding="utf-8") as f:
            node = yaml.safe_load(f) or {}
        for key in ("provisioner", "inventory", "group_vars"):
            if not isinstance(node, dict):
                raise ValueError(f"not a mapping above {key}")
            node = node.get(key) or {}
        if not isinstance(node, dict):
            raise ValueError("group_vars is not a mapping")

        roles = set()
        for group, variables in node.items():
            if not isinstance(variables := variables or {}, dict):
                raise ValueError(f"group_vars.{group} is not a mapping")
            if not isinstance(entries := variables.get("molecule_converge_roles") or [], list):
                raise ValueError(f"group_vars.{group}.molecule_converge_roles is not a list")
            for entry in entries:
                name = entry.get("name") if isinstance(entry, dict) else entry
                if not isinstance(name, str):
                    raise ValueError(f"group_vars.{group}.molecule_converge_roles has an entry without a name")
                roles.add(name)

    except (OSError, ValueError, yaml.YAMLError) as err:
        print_warning(f"Ignoring molecule_converge_roles of {scenario_path}: {err}")
        return frozenset()
    return frozenset(roles)


def _role_scenarios(role_meta: ProjectRoleMeta) -> List[ProjectPath]:
    """Directories of scenarios named {role} or {role}-{variant}, plus scenarios converging the role."""
    role, role_fqcn, role_collection_dir = role_meta.role_dir.name, role_meta.fqcn, role_meta.collection_dir
    scenarios = []
    for collection_dir in ProjectPath.all_collections():
        for scenario_path in _collection_scenario_files(collection_dir):
            scenario = scenario_path.parent.name
            if (
                collection_dir == role_collection_dir and (scenario == role or scenario.startswith(f"{role}-"))
            ) or role_fqcn in _scenario_converged_roles(scenario_path):
                scenarios.append(scenario_path.parent)
    return scenarios


def _dependent_roles(roles: Set[str]) -> Set[str]:
    """Transitive closure of the roles depending on the given roles."""
    dependencies = {
        role.fqcn: role.load_dependencies()
        for role in _all_roles()
        if role.collection_dir.name not in CLOSURE_EXCLUDED_COLLECTIONS
    }

    result = set(roles)
    while True:
        new_roles = {role for role, deps in dependencies.items() if deps & result} - result
        if not new_roles:
            return result
        result |= new_roles


def _affected_roles(paths: Iterable[ProjectPath]) -> Set[str]:
    """Roles touched by the paths, and their dependents."""
    roles: Set[str] = set()
    for path in paths:
        if (collection_dir := path.collection_dir) is None:
            continue
        subparts = path.relative_to(collection_dir).parts
        if len(subparts) < 2:
            continue

        if role_fqcn := path.collection_role_fqcn:
            roles.add(role_fqcn)
        # A file in a scenario directory: {role}[-{variant}]
        elif subparts[:2] == SCENARIOS_DIR.parts and len(subparts) > 3:
            roles.add(f"{path.collection_fqcn}.{subparts[2].split('-')[0]}")
        # A playbook name matching a role name.
        elif subparts[0] == "playbooks" and (role_dir := collection_dir / "roles" / Path(subparts[1]).stem).is_dir():
            roles.add(f"{path.collection_fqcn}.{role_dir.name}")
    return _dependent_roles(roles)


def _given_roles(fqcns: Iterable[str]) -> Set[str] | NoReturn:
    """Roles of the given role or collection FQCNs."""
    available_roles = _all_roles_fqcn()
    available_collections = {collection.collection_fqcn for collection in ProjectPath.all_collections()}
    roles: Set[str] = set()
    for fqcn in fqcns:
        if fqcn in available_collections:
            roles.update(name for name in available_roles if name.startswith(f"{fqcn}."))
            continue
        if fqcn not in available_roles:
            error_code(f"Unknown FQCN: {fqcn}", sys_exit=True)
        roles.add(fqcn)
    return roles


def select_roles(app_args) -> Set[str]:
    """Roles from the CLI, the roles affected since the previous release, or all roles."""
    selected_fqcns = select_given_fqcns(app_args.fqcns, app_args.all)
    if selected_fqcns:
        return _given_roles(selected_fqcns)

    selected_paths = (
        select_changed_paths(FRAMEWORK_PATTERNS, app_args.ignore_framework, require_release=True)
        if selected_fqcns == []  # Nothing given.
        else []
    )

    if selected_fqcns is None or selected_paths is None:  # Everything.
        return _all_roles_fqcn()

    roles = _affected_roles(selected_paths)
    if roles:
        print_hint("Affected role(s):", sorted(roles))
    return roles


def select_scenarios(roles: Iterable[str]) -> List[ProjectPath]:
    """Sorted scenario directories of the roles, reporting roles without scenarios."""
    scenarios: Set[ProjectPath] = set()
    untested = []
    for fqcn in sorted(roles):
        role_meta = ProjectRoleMeta.from_fqcn(fqcn)
        role_scenario_paths = _role_scenarios(role_meta)
        if not role_scenario_paths:
            untested.append(role_meta.fqcn)
        scenarios.update(role_scenario_paths)

    if untested:
        print_hint(f"Roles without molecule scenarios: {', '.join(untested)}")
    selected = sorted(scenarios)
    if selected:
        print_debug("Selected scenario(s):", selected)
    return selected


def get_subcommand_arg(molecule_args: List[str]) -> str:
    """The first argument that is neither a global option nor the value of one."""
    skip_value = False
    for arg in molecule_args:
        if skip_value:
            skip_value = False
        elif arg in MOLECULE_VALUE_OPTIONS:
            skip_value = True
        elif not arg.startswith("-"):
            return arg
    return ""


def detect_workers() -> int:
    """Detect the optimal number of workers based on inotify max_user_instances and podman transient store."""
    podman = shlex.quote(os.getenv("MOLECULE_PODMAN_EXECUTABLE") or "podman")
    podman_info = run_shell_get_lines(podman + " info --format='{{.Store.TransientStore}}' || true")
    podman_transient_store = podman_info and podman_info[0].lower() == "true"
    inotify_max_user_instances = (
        int(INOTIFY_MAX_USER_INSTANCES_PATH.read_bytes()) if INOTIFY_MAX_USER_INSTANCES_PATH.exists() else 128
    )

    # See the Findings in MOLECULE.md.
    workers = 6
    notes = []
    if inotify_max_user_instances < 128 * workers:
        notes.append("inotify max_user_instances")
        workers = max(inotify_max_user_instances // 128, 1)
    if not podman_transient_store:
        notes.append("podman transient store")
        workers = min(workers, 2)

    if notes:
        print_hint(f"See MOLECULE.md about {' and '.join(notes)}.")
    print_hint(f"Detected workers: {workers}")
    return workers


def run_build_playbook() -> int:
    env = os.environ.copy()
    env.update(
        {
            **ANSIBLE_NO_PROMPT_ENV,
            "ANSIBLE_BECOME": "False",
            "ANSIBLE_DEPRECATION_WARNINGS": "False",
            "ANSIBLE_PIPELINING": "True",
            "ANSIBLE_PYTHON_INTERPRETER": "auto_silent",
            "ANSIBLE_VERBOSITY": "0",
        }
    )
    return run_test_cmd(BUILD_PLAYBOOK_CMD, [BUILD_PLAYBOOK], BUILD_PLAYBOOK, env=env, output=OutputMode.LIVE_QUIET)


def run_molecule_with_all(molecule_args: List[str], forwarded_args: List[str]) -> int:
    targets = [{"args": ["--all", *forwarded_args], "cwd": collection} for collection in ProjectPath.all_collections()]
    return run_tests_parallel(MOLECULE_CMD + molecule_args, targets, max_workers=1, output=OutputMode.LIVE_WITH_STATUS)


def run_molecule_with_scenarios(
    scenarios: List[ProjectPath], molecule_args: List[str], forwarded_args: List[str], workers: int = 0
) -> int:
    targets = [
        {"args": ["-s", scenario.name, *forwarded_args], "cwd": scenario.collection_dir} for scenario in scenarios
    ]

    if workers < 1:
        workers = detect_workers()

    # Explicitly enable colors for captured output.
    env = os.environ.copy()
    if Color.COLORS_ENABLED:
        env.setdefault("PY_COLORS", "1")
        env.setdefault("ANSIBLE_FORCE_COLOR", "1")

    output = (
        OutputMode.ON_FAILURE_WITH_STATUS
        if get_subcommand_arg(molecule_args) == "test"
        else OutputMode.BUFFERED_WITH_STATUS if workers != 1 and len(targets) > 1 else OutputMode.LIVE_WITH_STATUS
    )

    # With 1 worker, scenarios are executed one by one, continuing after failures;
    # unlike a single run with multiple scenarios that stops on failures.
    return run_tests_parallel(MOLECULE_CMD + molecule_args, targets, max_workers=workers, env=env, output=output)


def main() -> None:
    own_args, molecule_args = split_passthrough_args(sys.argv[1:])
    app_args = args_parser.parse_intermixed_args(own_args)
    molecule_args, forwarded_args = split_passthrough_args(molecule_args, keep_separator=True)
    molecule_args = molecule_args or MOLECULE_DEFAULT_ARGS

    if any(arg.startswith(("--workers", "--parallel")) for arg in molecule_args):
        print_hint("Use molecule.py --workers N")
        error_code("molecule's --workers/--parallel are not supported!", sys_exit=True)

    chdir_project()
    roles = select_roles(app_args)
    scenarios = select_scenarios(roles)
    if not scenarios:
        nothing_to_test(MOLECULE_CMD[0], sys_exit=True)

    if app_args.list:
        for scenario in scenarios:
            print(f"{scenario.collection_fqcn}: {scenario.name}")
        RC.status(RC.OK, sys_exit=True)

    require_commands(MOLECULE_CMD[0], BUILD_PLAYBOOK_CMD[0])
    subcommand = get_subcommand_arg(molecule_args)
    if subcommand in MOLECULE_INSTANCE_COMMANDS:
        if (rc := run_build_playbook()) != RC.OK:
            RC.status(rc, sys_exit=True)

    if app_args.all and subcommand == "reset":
        rc = run_molecule_with_all(molecule_args, forwarded_args)
    else:
        rc = run_molecule_with_scenarios(scenarios, molecule_args, forwarded_args, app_args.workers)
    RC.status(rc, sys_exit=True)


if __name__ == "__main__":
    main()
