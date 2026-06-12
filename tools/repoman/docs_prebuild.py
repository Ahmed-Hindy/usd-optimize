"""Pre-build step for the documentation.

This script runs *before* the built-in ``repo docs`` command (via the
``./repo.sh docs_gen`` wrapper defined in ``docs_gen.py``). Put any
documentation generation that must happen ahead of Sphinx here.

Importing the ``usd_optimize`` Python API requires the built libraries to be on
``PYTHONPATH`` and the native loader path (``LD_LIBRARY_PATH`` on Linux,
``DYLD_LIBRARY_PATH`` on macOS). Because the native loader reads those variables
at process startup, they cannot be set after this process is already running. So
this script *re-runs itself* under the build's bundled Python interpreter (spawned
as a child process, waited on, and its exit code propagated) with the environment
configured up front (guarded by a sentinel env var to avoid infinite recursion).
Both the ``docs_gen`` wrapper and a direct ``python tools/repoman/docs_prebuild.py``
invocation go through the same bootstrap.

On Windows the dependent-DLL search differs: since Python 3.8 the loader ignores
``PATH`` for an extension module's dependencies and uses directories registered
via ``os.add_dll_directory()`` instead. So the library directories are also
registered that way (see ``_register_dll_directories``) right before the import.

The runtime paths mirror ``[repo_docs] library_paths`` / ``python_paths`` /
``python_path`` in ``repo.toml`` — keep them in sync if those change.
"""

import os
import platform
import subprocess
import sys

# Sentinel: set once we've re-execed into the configured bundled interpreter.
_BOOTSTRAP_ENV = "USD_OPTIMIZE_DOCS_PREBUILD_BOOTSTRAPPED"
# Config can be overridden (e.g. by docs_gen) to match the `docs` --config.
_CONFIG_ENV = "USD_OPTIMIZE_DOCS_CONFIG"

_DEFAULT_CONFIG = "release"


def _host_platform() -> str:
    """Return the repo build platform token, e.g. ``linux-x86_64``."""
    system = {"Linux": "linux", "Windows": "windows", "Darwin": "macos"}.get(
        platform.system(), platform.system().lower()
    )
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "arm64": "aarch64"}.get(machine, machine)
    return f"{system}-{arch}"


def _config() -> str:
    return os.environ.get(_CONFIG_ENV, _DEFAULT_CONFIG)


def _bundled_python(root: str) -> str:
    exe = "python.exe" if sys.platform == "win32" else "python"
    return os.path.join(root, "_build", "target-deps", "python", exe)


def _runtime_paths(root: str):
    """Return (python_paths, library_paths) for importing ``usd_optimize``.

    Mirrors ``[repo_docs]`` ``python_paths`` / ``library_paths`` in repo.toml.
    """
    plat = _host_platform()
    config = _config()
    build = os.path.join(root, "_build", plat, config)
    usd = os.path.join(root, "_build", "target-deps", "usd", config)

    python_paths = [
        os.path.join(build, "python"),
        os.path.join(usd, "lib", "python"),
    ]
    library_paths = [
        os.path.join(build, "lib"),
        os.path.join(build, "extraLibs"),
        os.path.join(usd, "lib"),
    ]
    return python_paths, library_paths


def _native_lib_env_var() -> str:
    if sys.platform == "win32":
        return "PATH"
    return "LD_LIBRARY_PATH"


def _build_env(root: str) -> dict:
    """Return a copy of os.environ with runtime paths prepended."""
    python_paths, library_paths = _runtime_paths(root)
    env = dict(os.environ)

    def prepend(var: str, paths):
        existing = env.get(var, "")
        parts = [p for p in paths if p]
        if existing:
            parts.append(existing)
        env[var] = os.pathsep.join(parts)

    prepend("PYTHONPATH", python_paths)
    prepend(_native_lib_env_var(), library_paths)
    env[_BOOTSTRAP_ENV] = "1"
    return env


def _register_dll_directories(root: str) -> None:
    """Make ``usd_optimize``'s dependent DLLs resolvable on Windows.

    Since Python 3.8, ``PATH`` is no longer searched when resolving the
    dependent DLLs of an extension module (``.pyd``); the loader uses the
    directories registered via ``os.add_dll_directory()`` instead. Prepending to
    ``PATH`` (see ``_build_env``) is therefore not enough on Windows — without
    this the ``usd_optimize.core`` import fails with a cryptic "DLL load failed".
    No-op on non-Windows, where ``LD_LIBRARY_PATH`` already covers this.
    """
    if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
        return
    _, library_paths = _runtime_paths(root)
    for path in library_paths:
        if path and os.path.isdir(path):
            os.add_dll_directory(path)


def _bootstrap(root: str) -> None:
    """Re-run under the bundled interpreter with the runtime env configured.

    No-op if we are already in the bootstrapped subprocess. Otherwise spawns the
    bundled interpreter as a child process (with the native loader path set up
    front), waits for it, and exits with its return code — so this function never
    returns in the parent process.

    We use ``subprocess`` rather than ``os.execve`` because ``execve`` does not
    behave like a POSIX exec on Windows: instead of replacing the current
    process, it spawns a *detached* child and the original process returns/exits
    immediately. The launching process would then terminate while the real work
    ran independently, making the job look like it had finished (or failed)
    before docs generation completed. ``subprocess.run`` + propagating the exit
    code works consistently across platforms.
    """
    if os.environ.get(_BOOTSTRAP_ENV):
        return

    python = _bundled_python(root)
    if not os.path.isfile(python):
        raise FileNotFoundError(
            f"Bundled Python not found at {python}. Run `./repo.sh build` first "
            "so the usd_optimize libraries and interpreter are available."
        )

    env = _build_env(root)
    # Spawn the bundled interpreter so the native loader picks up the new library
    # path from the start, wait for it, and mirror its exit code.
    result = subprocess.run([python, os.path.abspath(__file__), root], env=env)
    sys.exit(result.returncode)


def _gen_operations_docs():
    # we're going to use usd_optimize core python apis to generate documentation
    # for operations
    from usd_optimize.core import UsdOptimizeCore
    uo_core = UsdOptimizeCore.getInstance()

    # we need to do a first pass to gather all the information we need
    op_names = []
    op_info = {}
    for op_key in uo_core.getOperations():
        # we key info off the actual operation display name so we can make sure
        # they're alphabetically sorted in the docs
        op_display_name = uo_core.getOperationDisplayName(op_key)
        op_names.append(op_display_name)

        # build out the info for the operation args
        arg_info = []
        args = uo_core.getOperationArguments(op_key)
        for arg in args:
            # groups can be skipped in the docs since they're for UI
            if "group" in arg:
                continue
            # get the metadata of this arg so we can check if its visible, since
            # invisible args should be skipped in the docs
            arg_metadata = arg.get("metadata", {})
            if arg_metadata.get("visible", True) is False or "group" in arg_metadata:
                continue
            # resolve name
            arg_name = f"{arg['name']}"
            # resolve the default value (and the type from this)
            arg_default_value = arg.get("defaultValue", "")
            arg_type = type(arg_default_value)
            # if this is a list, we want to find the type of list
            if arg_type == list:
                arg_array_type = arg.get("arrayType", 0)
                if arg_array_type == 1:
                    arg_type = "[int]"
                elif arg_array_type == 2:
                    arg_type = "[string]"
                elif arg_array_type == 3 or arg_array_type == 4:
                    arg_type = "[float]"
                else:
                    arg_type = "list"
            # otherwise just use the name of the python type
            else:
                arg_type = arg_type.__name__
            # clean up the default value for display in the docs.
            if isinstance(arg_default_value, str):
                cleaned_default_value = arg_default_value.replace("\n", " ")
                arg_default_value = f'"{cleaned_default_value}"'
            elif isinstance(arg_default_value, float):
                arg_default_value = f"{arg_default_value:.6g}"
            # build out the info
            arg_info.append({
                "name": arg_name,
                "displayName": arg["displayName"],
                "type": arg_type,
                "defaultValue": arg_default_value,
                "enums": arg.get("enums", None),
                "min": arg_metadata.get("min", None),
                "max": arg_metadata.get("max", None),
                "description": arg.get("description", ""),
            })

        # build the info for this operation
        op_info[op_display_name] = {
            "key": op_key,
            "description": uo_core.getOperationDescription(op_key),
            "documentation": uo_core.getOperationDocumentation(op_key),
            "visible": uo_core.getOperationVisible(op_key),
            "args": arg_info,
        }

    # sort the operation names alphabetically for display in the docs
    op_names.sort()

    indent = "    "
    summary_sep = f"{indent}====================================================================== ============================================================================================"

    # first generate the main and developer table of contents and table for the
    # operations overview
    toc_tree = f".. toctree::\n{indent}:hidden:\n{indent}:maxdepth: 1\n{indent}:caption: Operations\n\n"
    summary_table = f".. table::\n    :widths: 30 70\n\n{summary_sep}\n{indent}Operation                                                              Description\n{summary_sep}\n"
    for op_name in op_names:
        op = op_info[op_name]
        op_key = op["key"]
        # generate toc tree entry
        toc_entry = f"{indent}{op_name} <operations/{op_key}>\n"
        # hidden operations should be added to the developer toc, but not the
        # main one or summary table
        if not op["visible"]:
            op_name += " [Developer]"
        toc_tree += toc_entry
        table_name = f":doc:`{op_name}<operations/{op_key}>`"
        summary_table += f"{indent}{table_name: <70} {op['description']}\n"
    summary_table += f"{summary_sep}\n\n"

    # now generate a page for each operation
    op_docs = {}
    for op_name in op_names:
        op = op_info[op_name]
        op_key = op["key"]
        op_doc = ".. AUTO GENERATED FILE - DO NOT EDIT\n\n"
        # write the title
        op_doc += f"{'=' * len(op_name)}\n{op_name}\n{'=' * len(op_name)}\n\n"
        # write the key
        op_doc += f"**Key**: ``{op_key}``\n\n"
        # is this a developer operation?
        if not op["visible"]:
            op_doc += f".. Caution:: **Developer Operation**: This operation is intended for developer use.\n\n"
        # write the documentation
        op_doc += f"{op['documentation']}\n\n"
        # write arguments
        if op["args"]:
            op_doc += "Arguments\n---------\n\n"
            for arg in op["args"]:
                op_doc += f"{arg['displayName']}\n{'^' * len(arg['displayName'])}\n\n"
                op_doc += f"{arg['description']}\n\n"
                op_doc += f"{indent}- Name: ``{arg['name']}``\n"
                op_doc += f"{indent}- Type: ``{arg['type']}``\n"
                op_doc += f"{indent}- Default Value: ``{arg['defaultValue']}``\n"
                if arg.get("enums") is not None:
                    op_doc += f"{indent}- Enum Values:\n"
                    for enum in arg["enums"]:
                        op_doc += f"{indent}{indent}- ``{enum[1]}: {enum[0]}``\n"
                if arg.get("min") is not None:
                    op_doc += f"{indent}- Min Value: ``{arg['min']}``\n"
                if arg.get("max") is not None:
                    op_doc += f"{indent}- Max Value: ``{arg['max']}``\n"
                op_doc += "\n"
        op_docs[op_key] = op_doc

    return (toc_tree, summary_table, op_docs)


def run(root: str) -> None:
    """Execute the documentation pre-build step.

    Must run inside the bootstrapped environment (see module docstring) so the
    ``usd_optimize`` import resolves. Call via ``main()`` / ``docs_gen``, or run
    this file directly — both bootstrap first.

    Args:
        root: Absolute path to the repository root.
    """
    docs_dir = os.path.join(root, "docs")
    generated_overview = ""

    # On Windows the native loader ignores PATH for dependent DLLs (Python 3.8+),
    # so register the library directories before importing usd_optimize.
    _register_dll_directories(root)

    # first perform doc generation
    (toc_tree, summary_table, op_docs) = _gen_operations_docs()

    # open the operations.rst and find the GENERATED_DOCS_BEGIN / END markers
    begin_marker = ".. GENERATED_DOCS_BEGIN"
    end_marker = ".. GENERATED_DOCS_END"
    in_generated_section = False
    with open(os.path.join(docs_dir, "operations.rst"), "r") as f:
        lines = f.readlines()
        for line in lines:
            # end marker?
            if line.strip().startswith(end_marker):
                in_generated_section = False
            # write the line if we're not in the generated section
            if not in_generated_section:
                generated_overview += line
            # begin marker?
            if line.strip().startswith(begin_marker):
                in_generated_section = True
                # generate the operations section of the docs
                generated_overview += toc_tree + "\n\n" + summary_table + "\n"

    # now write the operations.rst back out with the generated content
    with open(os.path.join(docs_dir, "operations.rst"), "w") as f:
        f.write(generated_overview)

    # write out the individual operation docs
    for op_key, op_doc in op_docs.items():
        with open(os.path.join(docs_dir, "operations", f"{op_key}.rst"), "w") as f:
            f.write(op_doc)


def main() -> int:
    # tools/repoman/docs_prebuild.py -> repo root is two levels up.
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    try:
        _bootstrap(root)  # spawns bundled python and exits; returns here only when bootstrapped
    except Exception as e:
        print(f"[docs_prebuild] Bootstrap failed with exception: {e}")
        raise
    try:
        run(root)
    except Exception as e:
        print(f"[docs_prebuild] Pre-build step failed with exception: {e}")
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
