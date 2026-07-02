# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Standalone JSON execution helpers for the public Usd Optimize Python API."""

import json as _json

from usd_optimize.core import ExecutionContext, UsdOptimizeCore

_CONTEXT_KEYS = {"debug", "singleThreaded", "verbose", "generateReport", "captureStats"}
_BOOL_STRINGS = {"true": True, "false": False, "1": True, "0": False}


def _coerce_context_value(value):
    """Convert a JSON value to the type expected by ``ExecutionContext``.

    Booleans and boolean-like strings become ``bool``. Other values are left
    unchanged because ``json.load`` already returns suitable ``int`` and
    ``float`` values.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        mapped = _BOOL_STRINGS.get(value.lower())
        if mapped is not None:
            return mapped
    return value


def execute_commands_from_json(stage, filepath_or_json):
    """Execute operation commands from a JSON file path or JSON string.

    Args:
        stage: The ``pxr.Usd.Stage`` to operate on.
        filepath_or_json: A filesystem path to a JSON command file, or a JSON
            string containing a list of operation descriptors.

    Returns:
        ``True`` when every command succeeds, otherwise ``False``.
    """
    so_core = UsdOptimizeCore.getInstance()

    context = ExecutionContext()
    context.set_stage(stage)

    try:
        with open(filepath_or_json) as json_file:
            operations = _json.load(json_file)
    except (FileNotFoundError, OSError):
        try:
            operations = _json.loads(filepath_or_json)
        except ValueError:
            return False
    except ValueError:
        return False

    if not isinstance(operations, list):
        return False

    result = True
    for operation_config in operations:
        operation_config = dict(operation_config)
        if "operation" not in operation_config:
            result = False
            continue
        operation_name = operation_config.pop("operation")

        if operation_name == "executionContext":
            for key, value in operation_config.items():
                if key in _CONTEXT_KEYS:
                    setattr(context, key, _coerce_context_value(value))
            continue

        success, _error, _warning = so_core.executeOperation(operation_name, context, operation_config)
        if not success:
            result = False

    # Do not call context.remove_stage() here. Removing the stage from the
    # UsdUtils.StageCache can invalidate the caller's stage reference when the
    # stage was opened via an anonymous layer.
    return result


def get_output_paths(operation):
    """Return output paths set by an operation.

    Args:
        operation: The operation to inspect.

    Returns:
        An empty list because standalone mode does not expose output paths.
    """
    return []


def get_output_path_arrays(operation):
    """Return output path arrays set by an operation.

    Args:
        operation: The operation to inspect.

    Returns:
        An empty list because standalone mode does not expose output path arrays.
    """
    return []


def map_config(config):
    """Map an operation configuration through the core rename compatibility layer.

    Args:
        config: A JSON-compatible operation configuration.

    Returns:
        The mapped configuration returned by ``UsdOptimizeCore.mapConfig``.
    """
    so_core = UsdOptimizeCore.getInstance()
    return so_core.mapConfig(config)
