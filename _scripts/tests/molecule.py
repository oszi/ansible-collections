#!/usr/bin/env python3
# pylint: disable=line-too-long,missing-function-docstring,missing-module-docstring
# run-tests: opt-in
import os
import shlex
import shutil

from argparse import ArgumentParser, REMAINDER
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import yaml

from testlib import (
    RC,
    Color,
    Output,
    error_code,
    print_hint,
    print_warning,
    run_shell_get_lines,
    run_test_cmd,
    run_tests_parallel,
    success,
)

NAMESPACE = "oszi"
NAMESPACE_PATH = Path("ansible_collections") / NAMESPACE
COLLECTIONS = ("general", "thirdparty", "utils")
SCENARIOS_DIR = Path("extensions") / "molecule"
RELEASE_TAG_GLOB = "[0-9]*.[0-9]*.[0-9]*"

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

Role = Tuple[str, str]  # (collection, role)

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


def git_ls_files(*pathspecs: str) -> List[Path]:
    """Tracked and untracked files matching the pathspecs, excluding ignored files and files deleted in the working tree."""
    specs = " ".join(shlex.quote(f":(glob){pathspec}") for pathspec in pathspecs)
    paths = run_shell_get_lines(f"git ls-files -c -o --exclude-standard --deduplicate -- {specs}", unique=True)
    return [path for path in map(Path, paths) if path.exists()]


@lru_cache(maxsize=None)
def all_roles() -> Tuple[Role, ...]:
    pathspec = f"{NAMESPACE_PATH}/*/roles/*/meta/main.y*ml"
    return tuple((path.parts[2], path.parts[4]) for path in git_ls_files(pathspec) if path.parts[2] in COLLECTIONS)


@lru_cache(maxsize=None)
def collection_scenario_files(collection: str) -> Tuple[Path, ...]:
    pathspec = f"{NAMESPACE_PATH / collection / SCENARIOS_DIR}/*/molecule.y*ml"
    return tuple(sorted(git_ls_files(pathspec)))


@lru_cache(maxsize=None)
def scenario_converged_roles(scenario_path: Path) -> Set[Role]:
    """Roles listed in molecule_converge_roles of a scenario's inventory group_vars; parsed once per scenario."""
    try:
        with scenario_path.open("r", encoding="utf-8") as f:
            molecule_yml = yaml.safe_load(f) or {}
        group_vars = molecule_yml["provisioner"]["inventory"]["group_vars"]
    except (OSError, yaml.YAMLError, KeyError, TypeError):
        return frozenset()

    roles = set()
    for variables in group_vars.values():
        for entry in (variables or {}).get("molecule_converge_roles") or []:
            fqcn = entry.get("name", "") if isinstance(entry, dict) else str(entry)
            role = parse_fqcn(fqcn)
            if role is not None and role[1]:
                roles.add(role)
    return frozenset(roles)


def role_scenarios(role: Role) -> List[Path]:
    """Scenario directories named {role} or {role}-{variant}, plus scenarios converging the role."""
    collection, name = role
    scenarios = []
    for scenario_path in collection_scenario_files(collection):
        scenario = scenario_path.parent.name
        if scenario == name or scenario.startswith(f"{name}-") or role in scenario_converged_roles(scenario_path):
            scenarios.append(scenario_path.parent)
    return scenarios


def parse_fqcn(fqcn: str) -> Optional[Role]:
    """Return (collection, role) for oszi.collection.role, or (collection, '') for oszi.collection."""
    parts = fqcn.split(".")
    if len(parts) not in (2, 3) or parts[0] != NAMESPACE or parts[1] not in COLLECTIONS:
        return None
    return (parts[1], parts[2] if len(parts) == 3 else "")


def role_dependencies(role: Role) -> Set[Role]:
    """Roles listed as dependencies in meta/main.yml."""
    meta_path = NAMESPACE_PATH / role[0] / "roles" / role[1] / "meta" / "main.yml"
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as err:
        print_warning(f"Failed to load {meta_path}: {err}")
        return set()

    dependencies = set()
    for entry in meta.get("dependencies") or []:
        fqcn = entry.get("role", entry.get("name", "")) if isinstance(entry, dict) else str(entry)
        dependency = parse_fqcn(fqcn)
        if dependency is not None and dependency[1]:
            dependencies.add(dependency)
    return dependencies


def dependent_roles(roles: Set[Role]) -> Set[Role]:
    """Transitive closure of the roles depending on the given roles."""
    dependencies = {role: role_dependencies(role) for role in all_roles()}
    result = set(roles)
    while True:
        new_roles = {role for role, deps in dependencies.items() if deps & result} - result
        if not new_roles:
            return result
        result |= new_roles


def previous_release() -> str:
    """The latest release tag; the one before it if HEAD is a release and the working tree is clean."""
    describe = f"git describe --tags --abbrev=0 --match='{RELEASE_TAG_GLOB}'"
    releases = run_shell_get_lines(f"{describe} HEAD 2>/dev/null || true")
    if not releases:
        error_code("No release tag found; use --all or FQCNs.", sys_exit=True)
    head_is_release = run_shell_get_lines(
        f"git describe --tags --exact-match --match='{RELEASE_TAG_GLOB}' HEAD 2>/dev/null || true"
    )
    if head_is_release and not changed_paths("HEAD"):
        releases = run_shell_get_lines(f"{describe} '{releases[0]}^'")
    return releases[0]


def changed_paths(since: str) -> List[str]:
    """Committed changes since the ref, plus staged, unstaged and untracked changes in the working tree."""
    return run_shell_get_lines(
        f"git diff --name-only '{since}' -- ; git ls-files --others --exclude-standard", unique=True
    )


def affected_roles(paths: Iterable[str], ignore_framework: bool = False) -> Tuple[Set[Role], List[str]]:
    """Roles touched by the paths and framework changes; a framework change affects every role unless ignored."""
    roles: Set[Role] = set()
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
            roles.add((collection, name))
        elif kind == "plugins":
            framework_changes.append(path)
        elif kind == "extensions" and name == SCENARIOS_DIR.name and len(parts) > 5:
            if len(parts) == 6:  # The base config.yml (symlinked from utils) or any other collection-wide file.
                framework_changes.append(path)
            else:
                roles.add((collection, parts[5].split("-")[0]))
        elif kind == "playbooks" and (NAMESPACE_PATH / collection / "roles" / Path(name).stem).is_dir():
            roles.add((collection, Path(name).stem))

    if framework_changes and not ignore_framework:
        return all_roles(), framework_changes
    return dependent_roles(roles), framework_changes


def select_roles(app_args) -> Tuple[Set[Role], List[str]]:
    """Roles from the CLI, or the roles affected since the previous release."""
    fqcns = app_args.fqcns
    if "--" in fqcns:
        fqcns = fqcns[: fqcns.index("--")]
    if app_args.all:
        if fqcns:
            error_code("--all cannot be combined with FQCNs.", sys_exit=True)
        return all_roles(), ["Selected all roles."]

    if fqcns:
        available_roles = all_roles()
        roles: Set[Role] = set()
        for fqcn in fqcns:
            parsed = parse_fqcn(fqcn)
            if parsed is None:
                error_code(f"Not a role or collection FQCN in namespace {NAMESPACE}: {fqcn}", sys_exit=True)
            collection, role = parsed
            if role and parsed not in available_roles:
                error_code(f"Role not found: {fqcn}", sys_exit=True)
            roles |= {parsed} if role else {r for r in available_roles if r[0] == collection}
        return roles, [f"Selected {len(roles)} role(s) from the command line."]

    release = previous_release()
    roles, framework_changes = affected_roles(changed_paths(release), app_args.ignore_framework)
    notes = [f"Changes since release {release} affect {len(roles)} role(s)."]
    if framework_changes:
        effect = "are ignored" if app_args.ignore_framework else "affect every role"
        changes = "\n# ".join(framework_changes)
        notes.append(f"Framework changes {effect}.\n# {changes}")
    return roles, notes


def select_scenarios(roles: Iterable[Role]) -> Dict[str, List[Path]]:
    """Scenario directories of the roles by collection, reporting roles without scenarios."""
    scenarios: Dict[str, List[Path]] = {collection: [] for collection in COLLECTIONS}
    untested = []
    for role in sorted(roles):
        role_scenario_paths = role_scenarios(role)
        if not role_scenario_paths:
            untested.append(f"{NAMESPACE}.{role[0]}.{role[1]}")
        for scenario_path in role_scenario_paths:
            if scenario_path not in scenarios[role[0]]:
                scenarios[role[0]].append(scenario_path)
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

    os.chdir(run_shell_get_lines("git rev-parse --show-toplevel")[0])
    roles, notes = select_roles(app_args)
    for note in notes:
        print_hint(note)

    scenarios = select_scenarios(roles)
    if not any(scenarios.values()):
        success("molecule: nothing to test!", sys_exit=True)

    if app_args.list:
        for collection, scenario_paths in scenarios.items():
            for scenario_path in scenario_paths:
                print(f"{NAMESPACE}.{collection}: {scenario_path.name}")
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
