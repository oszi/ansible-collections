#!/usr/bin/env python3
# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring
# run-tests: opt-in
import os
import shlex
import shutil

from argparse import ArgumentParser, REMAINDER
from functools import lru_cache
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Set, Tuple

import yaml

from testlib import (
    NAMESPACE_PATH,
    Color,
    Output,
    RC,
    RoleMeta,
    error_code,
    git_chdir,
    git_changed_paths,
    git_previous_release_tag,
    print_hint,
    print_success,
    run_shell_get_lines,
    run_test_cmd,
    run_tests_parallel,
)

COLLECTIONS = ("general", "thirdparty", "utils")
SCENARIOS_DIR = Path("extensions") / "molecule"

# Changes to the shared molecule framework and tooling affect every role.
FRAMEWORK_PATHS = (
    "_scripts/tests/molecule.py",
    "requirements.txt",
    "requirements.yml",
    f"{NAMESPACE_PATH}/utils/playbooks/molecule/",
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

args_parser.add_argument("--all", help="run the scenarios of all roles", action="store_true", default=False)
args_parser.add_argument("--ignore-framework", help="select only the roles touched directly", action="store_true")
args_parser.add_argument("--list", help="list selected scenarios without running anything", action="store_true")
args_parser.add_argument("--workers", help="number of parallel scenarios (<1 for auto)", type=int, default=0)
args_parser.add_argument("fqcns", help="[FQCN ...] [-- MOLECULE_ARGS ...]", nargs=REMAINDER)


def _all_roles() -> List[RoleMeta]:
    """All roles as RoleMeta. Called once in all code paths."""
    return [role for role in RoleMeta.from_glob() if role.collection.name in COLLECTIONS]


def _all_roles_fqcn() -> Set[str]:
    """All roles as FQCNs. Called once in all code paths."""
    return {role.fqcn for role in _all_roles()}


@lru_cache(maxsize=None)
def _collection_scenario_files(collection: str) -> Tuple[Path, ...]:
    """All scenario paths (molecule.yml) in a collection as a cached, ordered, immutable tuple."""
    scenarios_path = NAMESPACE_PATH / collection / SCENARIOS_DIR
    return tuple(sorted(scenarios_path.glob("*/molecule.y*ml")))


@lru_cache(maxsize=None)
def _scenario_converged_roles(scenario_path: Path) -> FrozenSet[str]:
    """FQCNs listed in molecule_converge_roles of a scenario's inventory group_vars; parsed once per scenario."""
    try:
        with scenario_path.open("r", encoding="utf-8") as f:
            molecule_yml = yaml.safe_load(f) or {}
        group_vars = molecule_yml["provisioner"]["inventory"]["group_vars"]
    except (OSError, yaml.YAMLError, KeyError, TypeError):
        return frozenset()

    roles = set()
    for variables in group_vars.values():
        for entry in (variables or {}).get("molecule_converge_roles") or []:
            roles.add(entry.get("name", "") if isinstance(entry, dict) else str(entry))
    return frozenset(roles)


def _role_scenarios(role_meta: RoleMeta) -> List[Path]:
    """Scenario directories named {role} or {role}-{variant}, plus scenarios converging the role."""
    scenarios = []
    for scenario_path in _collection_scenario_files(role_meta.collection.name):
        scenario = scenario_path.parent.name
        if (
            scenario == role_meta.role.name
            or scenario.startswith(f"{role_meta.role.name}-")
            or role_meta.fqcn in _scenario_converged_roles(scenario_path)
        ):
            scenarios.append(scenario_path.parent)
    return scenarios


def _role_dependencies(role_meta: RoleMeta) -> Set[str]:
    """Roles listed as dependencies in meta/main.yml. Called once per role in dependent_roles."""
    meta = role_meta.load(raise_errors=False)
    return {
        entry.get("role", entry.get("name", "")) if isinstance(entry, dict) else str(entry)
        for entry in meta.get("dependencies") or []
    }


def _dependent_roles(roles: Set[str]) -> Set[str]:
    """Transitive closure of the roles depending on the given roles. Called once in affected_roles."""
    dependencies = {role.fqcn: _role_dependencies(role) for role in _all_roles()}
    result = set(roles)
    while True:
        new_roles = {role for role, deps in dependencies.items() if deps & result} - result
        if not new_roles:
            return result
        result |= new_roles


def _affected_roles(paths: Iterable[str], ignore_framework: bool = False) -> Tuple[Set[str], List[str]]:
    """Roles touched by the paths and framework changes; a framework change affects every role unless ignored."""
    namespace = NAMESPACE_PATH.name
    roles: Set[str] = set()
    framework_changes = []
    for path in paths:
        if path.startswith(FRAMEWORK_PATHS):
            framework_changes.append(path)
            continue

        parts = Path(path).parts
        if parts[:2] != NAMESPACE_PATH.parts or len(parts) < 5 or parts[2] not in COLLECTIONS:
            continue

        collection, kind, name = parts[2], parts[3], parts[4]
        if kind == "roles":
            roles.add(f"{namespace}.{collection}.{name}")
        elif kind == "plugins":
            framework_changes.append(path)
        elif kind == "extensions" and name == SCENARIOS_DIR.name and len(parts) > 5:
            if len(parts) == 6:  # The base config.yml (symlinked from utils) or any other collection-wide file.
                framework_changes.append(path)
            else:
                roles.add(f"{namespace}.{collection}.{parts[5].split('-')[0]}")
        elif kind == "playbooks" and (NAMESPACE_PATH / collection / "roles" / Path(name).stem).is_dir():
            roles.add(f"{namespace}.{collection}.{Path(name).stem}")

    if framework_changes and not ignore_framework:
        return _all_roles_fqcn(), framework_changes
    return _dependent_roles(roles), framework_changes


def select_roles(app_args) -> Tuple[Set[str], List[str]]:
    """Roles from the CLI, or the roles affected since the previous release."""
    fqcns = app_args.fqcns
    if "--" in fqcns:
        fqcns = fqcns[: fqcns.index("--")]
    if app_args.all:
        if fqcns:
            error_code("--all cannot be combined with FQCNs.", sys_exit=True)
        return _all_roles_fqcn(), ["Selected all roles."]

    if fqcns:
        namespace = NAMESPACE_PATH.name
        available_roles = _all_roles_fqcn()
        roles: Set[str] = set()
        for fqcn in fqcns:
            if fqcn in {f"{namespace}.{collection}" for collection in COLLECTIONS}:
                roles.update(name for name in available_roles if name.startswith(f"{fqcn}."))
                continue
            try:
                role = RoleMeta.from_fqcn(fqcn)
                if role.collection.name not in COLLECTIONS or not fqcn.split(".")[-1]:
                    raise ValueError(fqcn)
            except ValueError:
                error_code(f"Not a role or collection FQCN in namespace {namespace}: {fqcn}", sys_exit=True)
            if fqcn not in available_roles:
                error_code(f"Role not found: {fqcn}", sys_exit=True)
            roles.add(fqcn)
        return roles, [f"Selected {len(roles)} role(s) from the command line."]

    release = git_previous_release_tag()
    if release is None:
        error_code("No release tag found. Wrong repository?", sys_exit=True)

    roles, framework_changes = _affected_roles(git_changed_paths(release), app_args.ignore_framework)
    notes = [f"Changes since release {release} affect {len(roles)} role(s)."]
    if framework_changes:
        effect = "are ignored" if app_args.ignore_framework else "affect every role"
        changes = "\n# ".join(framework_changes)
        notes.append(f"Framework changes {effect}.\n# {changes}")
    return roles, notes


def select_scenarios(roles: Iterable[str]) -> Dict[str, List[Path]]:
    """Scenario directories of the roles by collection, reporting roles without scenarios."""
    scenarios: Dict[str, List[Path]] = {collection: [] for collection in COLLECTIONS}
    untested = []
    for fqcn in sorted(roles):
        role_meta = RoleMeta.from_fqcn(fqcn)
        role_scenario_paths = _role_scenarios(role_meta)
        if not role_scenario_paths:
            untested.append(role_meta.fqcn)
        for scenario_path in role_scenario_paths:
            if scenario_path not in scenarios[role_meta.collection.name]:
                scenarios[role_meta.collection.name].append(scenario_path)
    if untested:
        print_hint(f"Roles without molecule scenarios: {', '.join(untested)}")
    return scenarios


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
            "ANSIBLE_ASK_PASS": "False",
            "ANSIBLE_ASK_VAULT_PASS": "False",
            "ANSIBLE_BECOME": "False",
            "ANSIBLE_BECOME_ASK_PASS": "False",
            "ANSIBLE_DEPRECATION_WARNINGS": "False",
            "ANSIBLE_PIPELINING": "True",
            "ANSIBLE_PYTHON_INTERPRETER": "auto_silent",
            "ANSIBLE_VERBOSITY": "0",
        }
    )
    return run_test_cmd(BUILD_PLAYBOOK_CMD, [BUILD_PLAYBOOK], BUILD_PLAYBOOK, env=env, output=Output.LIVE_QUIET)


def run_molecule(scenarios: Dict[str, List[Path]], molecule_args: List[str], app_args_all: bool, workers: int) -> int:
    subcommand = get_subcommand_arg(molecule_args)
    if app_args_all and subcommand == "reset":
        targets = [{"args": ["--all"], "cwd": NAMESPACE_PATH / collection} for collection in COLLECTIONS]
        workers = 1
    else:
        targets = []
        for collection, scenario_paths in scenarios.items():
            for scenario_path in scenario_paths:
                targets.append({"args": ["-s", scenario_path.name], "cwd": NAMESPACE_PATH / collection})

    if workers < 1:
        workers = detect_workers()

    env = os.environ.copy()
    if Color.COLORS_ENABLED:
        env.setdefault("PY_COLORS", "1")
        env.setdefault("ANSIBLE_FORCE_COLOR", "1")

    output = (
        Output.ON_FAILURE_WITH_STATUS
        if subcommand == "test"
        else Output.BUFFERED_WITH_STATUS if workers != 1 and len(targets) > 1 else Output.LIVE_WITH_STATUS
    )

    # With 1 worker, scenarios are executed one by one, continuing after failures;
    # unlike a single run with multiple scenarios that stops on failures.
    rc = run_tests_parallel(MOLECULE_CMD + molecule_args, targets, max_workers=workers, env=env, output=output)
    if RC.is_signal(rc):
        print_hint("Use molecule.py --all -- reset")
    return rc


def main() -> None:
    app_args = args_parser.parse_args()
    molecule_args = app_args.fqcns[app_args.fqcns.index("--") + 1 :] if "--" in app_args.fqcns else []
    molecule_args = molecule_args or MOLECULE_DEFAULT_ARGS

    if any(arg.startswith("--workers") or arg.startswith("--parallel") for arg in molecule_args):
        print_hint("Use molecule.py --workers N")
        error_code("molecule's --workers/--parallel are not supported!", sys_exit=True)

    git_chdir()
    roles, notes = select_roles(app_args)
    for note in notes:
        print_hint(note)

    scenarios = select_scenarios(roles)
    if not any(scenarios.values()):
        print_success("molecule: nothing to test!")
        RC.status(RC.OK, sys_exit=True)

    if app_args.list:
        for collection, scenario_paths in scenarios.items():
            for scenario_path in scenario_paths:
                print(f"{NAMESPACE_PATH.name}.{collection}: {scenario_path.name}")
        RC.status(RC.OK, sys_exit=True)

    if shutil.which(MOLECULE_CMD[0]) is None:
        error_code("molecule not found! `source venv/bin/activate`", sys_exit=True)

    if get_subcommand_arg(molecule_args) in MOLECULE_INSTANCE_COMMANDS:
        rc = run_build_playbook()
        if rc != RC.OK:
            RC.status(rc, sys_exit=True)

    rc = run_molecule(scenarios, molecule_args, app_args.all, app_args.workers)
    RC.status(rc, sys_exit=True)


if __name__ == "__main__":
    main()
