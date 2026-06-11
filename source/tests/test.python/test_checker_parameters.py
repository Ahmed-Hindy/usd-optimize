# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

"""Tests for the declarative Usd Optimize checker parameter mechanism.

Exercises the `BaseUsdOptimizeChecker.PARAMETERS` / `_effective_args` path
and the `ValidationEngine.parameters` bridge installed in
`base_usd_optimize_checker`. Synthetic subclasses are used for the
mechanism tests; real checkers (`SmallMeshChecker`, `OccludedMeshesChecker`)
are used for the integration smoke tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock

from pxr import Usd
from usd_optimize.validators import OccludedMeshesChecker, SmallMeshChecker
from usd_optimize.validators.base_usd_optimize_checker import (
    BaseUsdOptimizeChecker,
    Parameter,
    _parameter_type,
)
from usd_validation_nvidia import ParameterMapping, ParameterType, ValidationEngine


@dataclass(frozen=True)
class _TestParameter:
    """Quacks like Asset Validator's UserParameter for ParameterMapping ingestion."""

    display_name: str
    type: ParameterType
    assigned_value: Any
    enum_values: tuple[str, ...] | None = None


def _make_mapping(values: dict[str, Any]) -> ParameterMapping:
    return ParameterMapping(
        _TestParameter(display_name=name, type=_parameter_type(value), assigned_value=value)
        for name, value in values.items()
    )


class _ParameterRule(BaseUsdOptimizeChecker):
    """Synthetic rule exercising mixed OPERATION_ARGS + PARAMETERS."""

    OPERATION_NAME = "parameterRule"
    OPERATION_ARGS = {"static": "fixed"}
    PARAMETERS = {
        "MY_THRESHOLD": Parameter(default=1.0, op_arg="threshold"),
        "ENABLED": Parameter(default=False, op_arg="enabled"),
    }


class _OtherParameterRule(BaseUsdOptimizeChecker):
    """Second synthetic rule, shares the unqualified MY_THRESHOLD name."""

    OPERATION_NAME = "otherParameterRule"
    PARAMETERS = {
        "MY_THRESHOLD": Parameter(default=10.0, op_arg="threshold"),
    }


class TestParameterDefinitions(TestCase):
    """Validate `get_parameter_definitions` advertises both naming forms."""

    def test_includes_unqualified_and_qualified_for_each_parameter(self):
        defs = {d.display_name: d for d in _ParameterRule.get_parameter_definitions()}
        self.assertIn("MY_THRESHOLD", defs)
        self.assertIn("_ParameterRule.MY_THRESHOLD", defs)
        self.assertIn("ENABLED", defs)
        self.assertIn("_ParameterRule.ENABLED", defs)

    def test_advertises_declared_default_as_assigned_value(self):
        defs = {d.display_name: d for d in _ParameterRule.get_parameter_definitions()}
        self.assertEqual(defs["MY_THRESHOLD"].assigned_value, 1.0)
        self.assertEqual(defs["ENABLED"].assigned_value, False)

    def test_maps_python_types_to_asset_validator_parameter_types(self):
        defs = {d.display_name: d for d in _ParameterRule.get_parameter_definitions()}
        self.assertEqual(defs["MY_THRESHOLD"].type, ParameterType.FLOAT)
        self.assertEqual(defs["ENABLED"].type, ParameterType.BOOL)

    def test_rule_without_parameters_advertises_nothing(self):
        class _NoParamsRule(BaseUsdOptimizeChecker):
            OPERATION_NAME = "noParams"

        self.assertEqual(_NoParamsRule.get_parameter_definitions(), [])


class TestEffectiveArgs(TestCase):
    """Validate `_effective_args` overlay semantics for parameter overrides."""

    def test_no_overrides_falls_back_to_declared_defaults(self):
        rule = _ParameterRule()
        self.assertEqual(
            rule._effective_args(),
            {"static": "fixed", "threshold": 1.0, "enabled": False},
        )

    def test_unqualified_override_replaces_default(self):
        rule = _ParameterRule(parameters=_make_mapping({"MY_THRESHOLD": 2.5}))
        args = rule._effective_args()
        self.assertEqual(args["threshold"], 2.5)
        self.assertEqual(args["enabled"], False)
        self.assertEqual(args["static"], "fixed")

    def test_qualified_override_replaces_default(self):
        rule = _ParameterRule(parameters=_make_mapping({"_ParameterRule.MY_THRESHOLD": 3.5}))
        self.assertEqual(rule._effective_args()["threshold"], 3.5)

    def test_qualified_override_wins_over_unqualified(self):
        rule = _ParameterRule(parameters=_make_mapping({"MY_THRESHOLD": 2.5, "_ParameterRule.MY_THRESHOLD": 3.5}))
        self.assertEqual(rule._effective_args()["threshold"], 3.5)

    def test_qualified_override_scoped_to_declaring_rule(self):
        mapping = _make_mapping(
            {
                "_ParameterRule.MY_THRESHOLD": 3.5,
                "_OtherParameterRule.MY_THRESHOLD": 7.5,
            }
        )
        self.assertEqual(_ParameterRule(parameters=mapping)._effective_args()["threshold"], 3.5)
        self.assertEqual(_OtherParameterRule(parameters=mapping)._effective_args()["threshold"], 7.5)

    def test_unknown_parameter_names_are_ignored(self):
        rule = _ParameterRule(
            parameters=_make_mapping(
                {
                    "UNKNOWN": 999.0,
                    "_ParameterRule.UNKNOWN": 999.0,
                    "_OtherParameterRule.MY_THRESHOLD": 7.5,
                }
            )
        )
        self.assertEqual(
            rule._effective_args(),
            {"static": "fixed", "threshold": 1.0, "enabled": False},
        )

    def test_operation_args_preserved_when_no_parameters_overlap(self):
        rule = _ParameterRule(parameters=_make_mapping({"MY_THRESHOLD": 2.5}))
        # The static OPERATION_ARGS key must survive _effective_args unchanged.
        self.assertEqual(rule._effective_args()["static"], "fixed")


class TestValidationEngineIntegration(TestCase):
    """Validate `ValidationEngine.parameters` advertises declared definitions."""

    def test_enabled_rule_exposes_unqualified_and_qualified_parameters(self):
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(_ParameterRule)
        parameters = engine.parameters
        self.assertIn("MY_THRESHOLD", parameters)
        self.assertIn("_ParameterRule.MY_THRESHOLD", parameters)
        self.assertIn("ENABLED", parameters)
        self.assertIn("_ParameterRule.ENABLED", parameters)

    def test_non_declared_parameters_not_added_by_bridge(self):
        engine = ValidationEngine(init_rules=False)
        engine.enable_rule(_ParameterRule)
        self.assertNotIn("UNKNOWN", engine.parameters)


class TestRealCheckerIntegration(TestCase):
    """Smoke-test that the converted real checkers expose the expected knobs."""

    def test_small_mesh_checker_declares_size_threshold(self):
        defs = {d.display_name: d for d in SmallMeshChecker.get_parameter_definitions()}
        self.assertIn("SIZE_THRESHOLD", defs)
        self.assertIn("SmallMeshChecker.SIZE_THRESHOLD", defs)
        self.assertEqual(defs["SIZE_THRESHOLD"].assigned_value, 0.001)
        self.assertEqual(defs["SIZE_THRESHOLD"].type, ParameterType.FLOAT)

    def test_small_mesh_checker_threshold_flows_to_op_arg(self):
        rule = SmallMeshChecker(parameters=_make_mapping({"SIZE_THRESHOLD": 0.5}))
        args = rule._effective_args()
        self.assertEqual(args["threshold"], 0.5)
        self.assertEqual(args["removeMethod"], 1)
        self.assertEqual(args["detectionMethod"], 0)

    def test_small_mesh_warning_message_reflects_threshold_override(self):
        """Guards against regression where the warning text hardcodes the default.

        `_CheckStage` builds the warning message via ``self._effective_args()
        ["threshold"]`` rather than ``self.PARAMETERS["SIZE_THRESHOLD"].default``;
        if a refactor reverts that, this catches it.
        """
        rule = SmallMeshChecker(parameters=_make_mapping({"SIZE_THRESHOLD": 0.3}))
        rule._AddWarning = MagicMock()
        rule.suggested_operations = []
        stage = Usd.Stage.CreateInMemory()

        rule._CheckStage(stage, {"smallGeometry": ["/Geometry/Mesh"]})

        stage_warning = next(
            call for call in rule._AddWarning.call_args_list if "below size threshold" in call.kwargs.get("message", "")
        )
        self.assertIn("0.3", stage_warning.kwargs["message"])

    def test_occluded_meshes_checker_declares_all_five_parameters(self):
        defs = {d.display_name: d for d in OccludedMeshesChecker.get_parameter_definitions()}
        for name, expected_default, expected_type in (
            ("USE_GPU", False, ParameterType.BOOL),
            ("CHECK_TRANSPARENCY", True, ParameterType.BOOL),
            ("CLUSTERED", True, ParameterType.BOOL),
            ("MINIMUM_GAP_SIZE", 0.01, ParameterType.FLOAT),
            ("MAXIMUM_GRID_RESOLUTION", 500.0, ParameterType.FLOAT),
        ):
            with self.subTest(parameter=name):
                self.assertIn(name, defs)
                self.assertIn(f"OccludedMeshesChecker.{name}", defs)
                self.assertEqual(defs[name].assigned_value, expected_default)
                self.assertEqual(defs[name].type, expected_type)

    def test_occluded_meshes_checker_overrides_flow_to_op_args(self):
        rule = OccludedMeshesChecker(
            parameters=_make_mapping(
                {
                    "USE_GPU": True,
                    "MINIMUM_GAP_SIZE": 0.5,
                    "OccludedMeshesChecker.MAXIMUM_GRID_RESOLUTION": 1000.0,
                }
            )
        )
        args = rule._effective_args()
        self.assertEqual(args["useGpu"], True)
        self.assertEqual(args["checkTransparency"], True)  # untouched default
        self.assertEqual(args["clustered"], True)  # untouched default
        self.assertEqual(args["minimumGapSize"], 0.5)
        self.assertEqual(args["maximumGridResolution"], 1000.0)
