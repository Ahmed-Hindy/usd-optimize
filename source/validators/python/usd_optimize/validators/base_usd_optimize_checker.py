# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import logging
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, ClassVar, Dict, List, Mapping, Tuple

from pxr import Usd
from usd_optimize.core import analysis
from usd_validation_nvidia import BaseRuleChecker, ParameterType, ValidationEngine

logger = logging.getLogger(__name__)

# Marker set on the patched ``ValidationEngine.parameters`` getter so a
# subsequent module reload (e.g. Omniverse extension hot-reload) detects the
# already-patched property instead of wrapping it a second time and growing
# the getter chain.
_PARAMETER_PROVIDER_SENTINEL = "_usd_optimize_parameter_provider"


@dataclass(frozen=True)
class Parameter:
    """Declarative spec for a user-tunable rule argument.

    ``default`` is the value the rule uses when no Asset Validator
    user-parameter overrides it. ``op_arg`` is the key under which the value
    is forwarded to the backing Usd Optimize operation.
    """

    default: Any
    op_arg: str


@dataclass(frozen=True)
class _AssetValidatorParameter:
    """Internal shape advertised through ``ValidationEngine.parameters``.

    Matches the structure Asset Validator's parameter mapping expects:
    a display name, type, default-as-assigned-value, and optional enum
    values. Kept private; rule authors use :class:`Parameter` instead.
    """

    display_name: str
    type: ParameterType
    assigned_value: Any
    enum_values: Tuple[str, ...] | None = None


def _parameter_type(value: Any) -> ParameterType | None:
    """Map a Python default value to its Asset Validator ParameterType.

    Non-scalar defaults (lists, dicts, None) return ``None`` so they are
    skipped during parameter advertisement. Strings map to
    ``ParameterType.ENUM`` since Asset Validator has no freeform-string
    type; rules with discrete string choices can later extend
    :class:`Parameter` to supply ``enum_values``.
    """
    if isinstance(value, bool):
        return ParameterType.BOOL
    if isinstance(value, int):
        return ParameterType.INT
    if isinstance(value, float):
        return ParameterType.FLOAT
    if isinstance(value, str):
        return ParameterType.ENUM
    return None


class BaseUsdOptimizeChecker(BaseRuleChecker):
    """Base checker for Usd Optimize analysis

    Handles executing a Usd Optimize operation with analysis mode enabled
    and validating the result.

    The analysis payload can then be passed to a derived Checker to process
    issues specific to that operation.

    Subclasses declare static op arguments in :attr:`OPERATION_ARGS` and
    user-tunable arguments in :attr:`PARAMETERS`. The default
    :meth:`_GetArgs` overlays Asset Validator parameter overrides onto
    OPERATION_ARGS using each :class:`Parameter`'s ``op_arg`` as the
    destination key; subclasses that need custom logic can still override
    ``_GetArgs``.
    """

    OPERATION_NAME: str = None
    # Immutable defaults so subclasses that forget to assign cannot mutate the
    # inherited shared mapping in place. Subclasses override by assigning a new
    # dict (or any Mapping) — the immutability is a footgun guard, not a
    # constraint on subclass declarations.
    OPERATION_ARGS: ClassVar[Mapping[str, Any]] = MappingProxyType({})
    PARAMETERS: ClassVar[Mapping[str, Parameter]] = MappingProxyType({})

    @classmethod
    def get_parameter_definitions(cls) -> List[_AssetValidatorParameter]:
        """Return Asset Validator parameter specs for this rule.

        Each declared :attr:`PARAMETERS` entry produces two definitions: an
        unqualified one (``NAME``) and a qualified one (``ClassName.NAME``)
        so callers can disambiguate when two rules expose the same parameter
        name. Defaults whose Python type doesn't map to a ParameterType
        (e.g. lists) are skipped.
        """
        defs: List[_AssetValidatorParameter] = []
        for name, param in cls.PARAMETERS.items():
            ptype = _parameter_type(param.default)
            if ptype is None:
                continue
            defs.append(_AssetValidatorParameter(name, ptype, param.default))
            defs.append(_AssetValidatorParameter(f"{cls.__name__}.{name}", ptype, param.default))
        return defs

    def _effective_args(self) -> Dict[str, Any]:
        """Build the op-args dict from OPERATION_ARGS + user-overridden PARAMETERS.

        Qualified parameter names (``ClassName.NAME``) win over unqualified
        names when both are supplied. Parameters without a user override fall
        back to :attr:`Parameter.default`.
        """
        args = dict(self.OPERATION_ARGS)
        if not self.PARAMETERS:
            return args

        rule_name = type(self).__name__
        mapping = self.parameters
        for name, param in self.PARAMETERS.items():
            value = param.default

            for lookup in (name, f"{rule_name}.{name}"):
                entry = (
                    mapping.get(lookup) if hasattr(mapping, "get") else (mapping[lookup] if lookup in mapping else None)
                )
                if entry is None or isinstance(entry, _AssetValidatorParameter):
                    continue
                assigned = getattr(entry, "assigned_value", None)
                if assigned is not None:
                    value = assigned

            args[param.op_arg] = value

        return args

    def _GetArgs(self):
        """Get arguments to use in execution.

        Default implementation returns :meth:`_effective_args`. Subclasses
        with bespoke arg-building logic can override.
        """
        return self._effective_args()

    def _AnalyzeStage(self, usdStage: Usd.Stage, operation_name: str, args: Dict = None) -> Tuple:
        """
        Runs Usd Optimize analysis on the given USD stage with the specified operation, reports a failure if found,
        and the returns the analysis result.
        """
        # Implementation error
        if not operation_name:
            self._AddFailedCheck(message="Invalid rule, no operation configured")
            return None

        analysis_result: Dict = analysis.analyze(usdStage, [analysis.OperationConfig(operation_name, args=args)])
        if not analysis_result:
            self._AddFailedCheck(message="Failed to run Usd Optimize analysis with unknown error.")
            return None

        # Extract sets of duplicates from the result
        operation_result: tuple = analysis_result.get(operation_name)
        if not operation_result:
            self._AddFailedCheck(message="Failed to run Usd Optimize analysis with unknown error.")
            return None

        # result should be a 3-tuple
        if len(operation_result) != 3:
            self._AddFailedCheck(message="Usd Optimize analysis returned invalid result.")
            return None

        # did analysis run successfully?
        if operation_result[0] is False:
            self._AddFailedCheck(message=f"Analysis encountered error: {operation_result[1]}")
            return None

        # resolve the suggested operations from the analysis result
        suggested_operations = analysis.create_operations_from_analysis_result(analysis_result)

        return (operation_result[2].get("analysis"), suggested_operations)

    def _CheckStage(self, usdStage: Usd.Stage, analysis: dict):
        """Derived checkers should implement this function.

        Subclasses that need the suggested operations from analysis can access
        them via ``self.suggested_operations``.
        """
        pass

    def CheckStage(self, usdStage: Usd.Stage):
        """Base setup/execution of analysis mode for a usd optimize operation"""
        analysis_result = None
        try:
            result = self._AnalyzeStage(usdStage, self.OPERATION_NAME, args=self._GetArgs())
            if result is not None:
                analysis_result, self.suggested_operations = result
        except Exception as ex:
            print("Failed to analyze stage:", ex)

        if analysis_result:
            # Defer to the derived class to process the result
            self._CheckStage(usdStage, analysis_result)


def _install_parameter_provider() -> None:
    """Teach ``ValidationEngine.parameters`` about declared rule PARAMETERS.

    Wraps the engine's ``parameters`` getter so each rule's declared
    parameters appear in the mapping (with their defaults) when not already
    present from user input. User-supplied entries take precedence because
    they already populate the mapping before the wrapper merges defaults.

    Idempotent across module reloads: a sentinel on the patched getter
    prevents the wrapper chain from growing each time this module is
    re-executed (e.g. Omniverse extension hot-reload).
    """
    parameters_property = ValidationEngine.parameters
    original_getter = parameters_property.fget
    if original_getter is None:
        return
    if getattr(original_getter, _PARAMETER_PROVIDER_SENTINEL, False):
        return

    def parameters(self):
        mapping = original_getter(self)
        for rule in self.rules:
            if not isinstance(rule, type) or not issubclass(rule, BaseUsdOptimizeChecker):
                continue
            for parameter in rule.get_parameter_definitions():
                if parameter.display_name not in mapping:
                    mapping.add(parameter)
        return mapping

    setattr(parameters, _PARAMETER_PROVIDER_SENTINEL, True)
    ValidationEngine.parameters = property(
        parameters,
        parameters_property.fset,
        parameters_property.fdel,
        parameters_property.__doc__,
    )


_install_parameter_provider()
