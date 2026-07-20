"""Custom ``repo`` command: ``docs_gen``.

Runs the documentation pre-build step (``docs_prebuild.run``) and then invokes
the built-in ``repo docs`` command. Any arguments passed after ``docs_gen`` are
forwarded verbatim to ``docs``::

    ./repo.sh docs_gen                  # pre-build, then `repo docs`
    ./repo.sh docs_gen --config debug   # forwards `--config debug` to `repo docs`
    ./repo.sh docs_gen --autogen_only   # run only the pre-build (doc autogen) step

The built-in ``docs`` tool exposes no pre-build hook, so this wrapper exists to
guarantee the Python pre-step always runs first.

``--autogen_only`` is consumed by this wrapper (not forwarded to ``docs``) and
stops after the pre-build step, skipping the full Sphinx/doxygen ``repo docs``
build.
"""

import argparse
import os
import subprocess
import sys
from typing import Callable, Dict

import omni.repo.man


def setup_repo_tool(parser: argparse.ArgumentParser, config: Dict) -> Callable:
    parser.description = (
        "Run the documentation pre-build step and then the built-in `docs` command. "
        "Arguments after `docs_gen` are forwarded to `docs`."
    )
    parser.add_argument(
        "--autogen_only",
        action="store_true",
        help="Run only the doc autogen pre-build step; skip the full `repo docs` build.",
    )
    parser.add_argument(
        "docs_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded verbatim to the built-in `repo docs` command.",
    )

    def run_repo_tool(options, config: Dict):
        root = omni.repo.man.resolve_tokens("$root")

        forwarded = list(options.docs_args or [])
        # argparse.REMAINDER keeps a leading "--" if the user typed one; drop it.
        if forwarded and forwarded[0] == "--":
            forwarded = forwarded[1:]

        # `--autogen_only` runs only the pre-build (doc autogen) step and skips the
        # full `repo docs` build below.
        autogen_only = options.autogen_only

        # Keep the pre-build config aligned with the `docs` --config (default
        # release, matching [repo_docs] in repo.toml).
        docs_config = "release"
        if "--config" in forwarded:
            i = forwarded.index("--config")
            if i + 1 < len(forwarded):
                docs_config = forwarded[i + 1]

        # 1. Pre-build step. Run it as a subprocess: docs_prebuild bootstraps the
        #    runtime environment and re-execs under the build's bundled Python so
        #    the native usd_optimize libraries import correctly. (Setting
        #    LD_LIBRARY_PATH in this already-running process would not work.)
        prebuild_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs_prebuild.py")
        prebuild_env = dict(os.environ, USD_OPTIMIZE_DOCS_CONFIG=docs_config)
        omni.repo.man.logger.info(f"[docs_gen] running pre-build step (config={docs_config})")
        result = subprocess.run([sys.executable, prebuild_script, root], cwd=root, env=prebuild_env, capture_output=True, text=True)
        print(result.stderr)
        print(result.stdout)
        if result.returncode != 0:
            print(f"[docs_gen] pre-build step failed with exit code {result.returncode}")
            raise SystemExit(result.returncode)

        if autogen_only:
            omni.repo.man.logger.info("[docs_gen] --autogen_only set; skipping `repo docs` build")
            return

        # 2. Invoke the built-in `docs` command via the repo entry script so it
        #    runs with the same bootstrapping as a normal `./repo.sh docs` call.
        shell_ext = ".bat" if sys.platform == "win32" else ".sh"
        repo_script = os.path.join(root, f"repo{shell_ext}")

        cmd = [repo_script, "docs", *forwarded]
        omni.repo.man.logger.info(f"[docs_gen] invoking: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=root)
        if result.returncode != 0:
            raise SystemExit(result.returncode)

    return run_repo_tool
