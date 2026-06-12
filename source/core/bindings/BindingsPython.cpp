// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

// Usd Optimize Core
#include "usd_optimize/core/UsdIncludes.h"

#include <usd_optimize/core/Core.h>
#include <usd_optimize/core/Defs.h>
#include <usd_optimize/core/Operation.h>
#include <usd_optimize/core/PybindUtils.h>
#include <usd_optimize/core/Utils.h>

// Usd
#include <pxr/base/js/json.h>
#include <pxr/base/js/value.h>

// Pybind
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

// C++
#include <mutex>


using namespace usd_optimize;


// Simple helper that can be used in a unique_ptr that will do nothing when its deleted
template <typename T>
struct BlankDeleter
{
    void operator()(T* inst) const
    {
    }
};


// C-callable trampoline for Py_AtExit. Drains the UsdOptimizeCore's
// shutdown-callback queue (registered by ops via registerShutdownCallback)
// during Py_Finalize, *before* C++ static destructors run — so callbacks
// can safely free CUDA buffers etc. while their host runtimes are still
// alive. std::atexit is unsuitable here because it interleaves LIFO with
// the CUDA driver's own atexit, which can leave us running after the
// driver has torn down.
static void _runUsdOptimizeCoreShutdownCallbacks()
{
    UsdOptimizeCore::getInstance().runShutdownCallbacks();
}


// wrapper function for UsdOptimizeCore::getInstance that ensures the singleton is initialized before we try to use
// it in Python.
static UsdOptimizeCore& _getInitializedUsdOptimizeCore()
{
    // Ensure the core is initialized before we return it
    static std::once_flag initFlag;
    std::call_once(initFlag,
                   []()
                   {
                       auto& core = UsdOptimizeCore::getInstance();
                       if (!core.isInitialized())
                       {
                           core.loadPlugins();
                       }
                       // Hook the shutdown-callback queue to Python's exit
                       // path. Operations that need cleanup before driver
                       // teardown (CUDA, etc.) register via
                       // UsdOptimizeCore::registerShutdownCallback; this
                       // single Py_AtExit drives them all.
                       Py_AtExit(_runUsdOptimizeCoreShutdownCallbacks);
                   });
    return UsdOptimizeCore::getInstance();
}


static const char* _UsdOptimizeCore_getOperationDisplayName_docString =
    "Returns the display name of the given operation, or an empty string if the operation doesn't exist.";
static std::string _UsdOptimizeCore_getOperationDisplayName(UsdOptimizeCore& core, const std::string& operationName)
{
    const OperationUPtr operation = core.getOperation(operationName);
    if (operation == nullptr)
    {
        return "";
    }

    return operation->getDisplayName();
}


static const char* _UsdOptimizeCore_getOperationDisplayGroup_docString =
    "Returns the display group of the given operation, or an empty string if the operation doesn't exist.";
static std::string _UsdOptimizeCore_getOperationDisplayGroup(UsdOptimizeCore& core, const std::string& operationName)
{
    const OperationUPtr operation = core.getOperation(operationName);
    if (operation == nullptr)
    {
        return "";
    }

    return operation->getDisplayGroup();
}


static const char* _UsdOptimizeCore_getOperationDescription_docString =
    "Returns the description of the given operation, or an empty string if the operation doesn't exist.";
static std::string _UsdOptimizeCore_getOperationDescription(UsdOptimizeCore& core, const std::string& operationName)
{
    const OperationUPtr operation = core.getOperation(operationName);
    if (operation == nullptr)
    {
        return "";
    }

    return operation->getDescription();
}


static const char* _UsdOptimizeCore_getOperationDocumentation_docString =
    "Returns the full documentation for this operation. If this is not overridden by the plugin, it will return the same string as getOperationDescription().";
static std::string _UsdOptimizeCore_getOperationDocumentation(UsdOptimizeCore& core, const std::string& operationName)
{
    const OperationUPtr operation = core.getOperation(operationName);
    if (operation == nullptr)
    {
        return "";
    }

    return operation->getDocumentation();
}


static const char* _UsdOptimizeCore_getOperationArguments_docString =
    "Returns the arguments of the given operation as JSON list, or an empty list if the operation doesn't exist.";
static pybind11::object _UsdOptimizeCore_getOperationArguments(UsdOptimizeCore& core, const std::string& operationName)
{
    PXR_NS::JsArray args;

    const OperationUPtr operation = core.getOperation(operationName);
    if (operation != nullptr)
    {
        // Create a JSON array and append the JSON object for each argument
        for (const Argument* argument : operation->getArgs())
        {
            args.push_back(argument->toJson());
        }
    }

    return _jsonValueToPybindObject(args);
}


static const char* _UsdOptimizeCore_getOperationAuthor_docString =
    "Returns the author of the given operation, or an empty string if the operation doesn't exist.";
static std::string _UsdOptimizeCore_getOperationAuthor(UsdOptimizeCore& core, const std::string& operationName)
{
    const OperationUPtr operation = core.getOperation(operationName);
    if (operation == nullptr)
    {
        return "";
    }

    return operation->getAuthor();
}

/// Returns the version of the given operation, or (-1, -1, -1) if the operation doesn't exist.
static const char* _UsdOptimizeCore_getOperationVersion_docString =
    "Returns the version of the given operation, or (-1, -1, -1) if the operation doesn't exist.";
static UsdOptimizePluginVersion _UsdOptimizeCore_getOperationVersion(UsdOptimizeCore& core,
                                                                     const std::string& operationName)
{
    const OperationUPtr operation = core.getOperation(operationName);
    if (operation == nullptr)
    {
        return UsdOptimizePluginVersion{ -1, -1, -1 };
    }

    return operation->getVersion();
}


static const char* _UsdOptimizeCore_getOperationVisible_docString =
    "Returns if the given operation is visible, or False if the operation doesn't exist.";
static bool _UsdOptimizeCore_getOperationVisible(UsdOptimizeCore& core, const std::string& operationName)
{
    const OperationUPtr operation = core.getOperation(operationName);
    if (operation == nullptr)
    {
        return false;
    }

    return operation->getVisible();
}


static const char* _UsdOptimizeCore_getOperationSupportsAnalysis_docString =
    "Returns if the given operation supports analysis, or False if the operation doesn't exist.";
static bool _UsdOptimizeCore_getOperationSupportsAnalysis(UsdOptimizeCore& core, const std::string& operationName)
{
    const OperationUPtr operation = core.getOperation(operationName);
    if (operation == nullptr)
    {
        return false;
    }

    return operation->getSupportsAnalysis();
}


// wrapper function for UsdOptimizeCore::ExecuteOperation that handles the ExecutionContext in its Python wrapper
// form, converts the args from a Python dict to a JSON string, and converts the OperationResult to a Python tuple.
static pybind11::tuple _UsdOptimizeCore_executeOperation(UsdOptimizeCore& core,
                                                         const std::string& operationName,
                                                         pybind11::object context,
                                                         pybind11::object args)
{
    // get the python args as a json string
    pybind11::module_ pyJson = pybind11::module_::import("json");
    pybind11::object pyJsonArgs = pyJson.attr("dumps")(args);

    // execute the operation
    OperationResult result =
        core.executeOperation(operationName, _getExecutionContextFromPyWrapper(context), pyJsonArgs.cast<std::string>());

    // convert result to a python tuple
    pybind11::tuple _result = _operationResultToPybindTuple(result);

    // Free the operation result
    usd_optimize_operation_result_free(&result);

    return _result;
}


// wrapper function for UsdOptimizeCore::executeConfig that accepts a Python list of dicts,
// serializes to a JSON string, executes the config, and returns a list of (success, error, output) tuples.
static pybind11::list _UsdOptimizeCore_executeConfig(UsdOptimizeCore& core,
                                                     pybind11::object context,
                                                     pybind11::object config)
{
    pybind11::module_ pyJson = pybind11::module_::import("json");
    pybind11::object pyJsonConfig = pyJson.attr("dumps")(config);

    std::vector<OperationResult> results =
        core.executeConfig(_getExecutionContextFromPyWrapper(context), pyJsonConfig.cast<std::string>());

    pybind11::list pyResults;
    for (auto& result : results)
    {
        pyResults.append(_operationResultToPybindTuple(result));
        usd_optimize_operation_result_free(&result);
    }

    return pyResults;
}


static pybind11::object _UsdOptimizeCore_mapConfig(UsdOptimizeCore& core, const std::string& config)
{
    PXR_NS::JsValue document = PXR_NS::JsParseString(config);
    if (document.IsNull())
    {
        throw pybind11::value_error("mapConfig: failed to parse JSON string");
    }
    if (!document.IsArray())
    {
        throw pybind11::type_error("mapConfig: expected a JSON array");
    }

    PXR_NS::JsArray mapped = core.mapConfig(document.GetJsArray());
    std::string result = PXR_NS::JsWriteToString(PXR_NS::JsValue(mapped));
    return pybind11::str(result);
}


PYBIND11_MODULE(_usd_optimize_impl_core, m)
{
    // Global execution context/options
    pybind11::class_<ExecutionContext>(m,
                                       "_ExecutionContextImpl",
                                       R"(
A struct describing the context in which a Scene Optimization should be performed.

This is accepted by all Usd Optimize Operation Commands.

:param int usdStageId: The stage on which to perform the operation
:param int generateReport: If true, a report will be generated that can be viewed via the Usd Optimize UI
:param int verbose: If true, log extended information (may result in slower performance)
:param int singleThreaded: If true, run operation single threaded
:param int captureStats: If true, capture and report on the contents of the stage before and after the operations run
:param str reportPath: File path where the report will be written, if undefined a path will be generated on execute
        )")
        .def(pybind11::init<>())
        .def_readwrite("usdStageId", &ExecutionContext::usdStageId)
        .def_readwrite("generateReport", &ExecutionContext::generateReport)
        .def_readwrite("verbose", &ExecutionContext::verbose)
        .def_readwrite("singleThreaded", &ExecutionContext::singleThreaded)
        .def_readwrite("debug", &ExecutionContext::debug)
        .def_readwrite("captureStats", &ExecutionContext::captureStats)
        .def_readwrite("analysisMode", &ExecutionContext::analysisMode)
        // reportPath is a char* owned by C++ (malloc/free). def_readwrite would let pybind11's
        // char* caster store a pointer into a temporary std::string, which dangles after the
        // setter returns. Use def_property so we copy on assign and own the buffer.
        .def_property(
            "reportPath",
            [](const ExecutionContext& self) -> pybind11::object
            {
                if (self.reportPath == nullptr)
                {
                    return pybind11::none();
                }
                return pybind11::str(self.reportPath);
            },
            [](ExecutionContext& self, pybind11::object value)
            {
                if (value.is_none())
                {
                    if (self.reportPath != nullptr)
                    {
                        free(self.reportPath);
                        self.reportPath = nullptr;
                    }
                    return;
                }
                // Cast first so a bad value throws before we free the existing buffer.
                std::string newPath = value.cast<std::string>();
                if (self.reportPath != nullptr)
                {
                    free(self.reportPath);
                    self.reportPath = nullptr;
                }
                self.reportPath = getCStr(newPath);
            })
        // ExecutionContext is a POD-ish C struct (no destructor — kept that way for Carbonite).
        // Without a finalizer here, reportPath leaks every time Python GCs the wrapper.
        .def("__del__", [](ExecutionContext& self) { usd_optimize_execution_context_free(&self); });

    pybind11::class_<UsdOptimizePluginVersion>(m,
                                               "UsdOptimizePluginVersion",
                                               R"(
Semantic version for plugins

:param int major: The major version number
:param int minor: The minor version number
:param int rev: The revision number
    )")
        .def(pybind11::init<>())
        .def_readwrite("major", &UsdOptimizePluginVersion::major)
        .def_readwrite("minor", &UsdOptimizePluginVersion::minor)
        .def_readwrite("rev", &UsdOptimizePluginVersion::rev);

    // Usd Optimize Core is not publicly constructible or destructible - so we wrap it in a unique_ptr with a blank
    // deleter to prevent pybind from trying to manage its lifetime
    pybind11::class_<UsdOptimizeCore, std::unique_ptr<UsdOptimizeCore, BlankDeleter<UsdOptimizeCore>>>(m,
                                                                                                       "UsdOptimizeCore",
                                                                                                       R"(
Singleton object that manages loading of Usd Optimize plugins and execution of operations.
        )")
        .def_static("getInstance", &_getInitializedUsdOptimizeCore, pybind11::return_value_policy::reference)
        .def("isInitialized", &UsdOptimizeCore::isInitialized)
        .def("getOperations", &UsdOptimizeCore::getOperations)
        .def("getOperationDisplayName",
             &_UsdOptimizeCore_getOperationDisplayName,
             _UsdOptimizeCore_getOperationDisplayName_docString)
        .def("getOperationDisplayGroup",
             &_UsdOptimizeCore_getOperationDisplayGroup,
             _UsdOptimizeCore_getOperationDisplayGroup_docString)
        .def("getOperationDescription",
             &_UsdOptimizeCore_getOperationDescription,
             _UsdOptimizeCore_getOperationDescription_docString)
        .def("getOperationDocumentation",
             &_UsdOptimizeCore_getOperationDocumentation,
             _UsdOptimizeCore_getOperationDocumentation_docString)
        .def("getOperationArguments",
             &_UsdOptimizeCore_getOperationArguments,
             _UsdOptimizeCore_getOperationArguments_docString)
        .def("getOperationAuthor", &_UsdOptimizeCore_getOperationAuthor, _UsdOptimizeCore_getOperationAuthor_docString)
        .def("getOperationVersion", &_UsdOptimizeCore_getOperationVersion, _UsdOptimizeCore_getOperationVersion_docString)
        .def("getOperationVisible", &_UsdOptimizeCore_getOperationVisible, _UsdOptimizeCore_getOperationVisible_docString)
        .def("getOperationSupportsAnalysis",
             &_UsdOptimizeCore_getOperationSupportsAnalysis,
             _UsdOptimizeCore_getOperationSupportsAnalysis_docString)
        .def("deregisterOperation", &UsdOptimizeCore::deregisterOperation)
        .def("loadPlugin", &UsdOptimizeCore::loadPlugin)
        .def("loadPluginsFromPath", &UsdOptimizeCore::loadPluginsFromPath)
        .def("loadPlugins", &UsdOptimizeCore::loadPlugins)
        .def("executeOperation", &_UsdOptimizeCore_executeOperation)
        .def("executeConfig",
             &_UsdOptimizeCore_executeConfig,
             R"(Execute a JSON configuration containing a sequence of operations.

The config is a list of dicts, where each dict has an "operation" key identifying the
operation to run, plus any operation-specific argument keys. An entry with
"operation": "executionContext" can be used to override context settings for subsequent
operations.

Operations are executed in order. Execution stops on the first failure.

:param context: The ExecutionContext to run the operations in.
:param config: A list of dicts, each describing an operation and its arguments.
:returns: A list of (success, error, output) tuples, one per executed operation
          (excluding executionContext entries).
)")
        .def("mapConfig",
             &_UsdOptimizeCore_mapConfig,
             R"(Map a JSON configuration to update renamed operations and arguments.

Takes a JSON string containing a Usd Optimize config (a JSON array of
operation dicts) and returns a JSON string with operation and argument names
updated to their current equivalents.

:param config: A JSON string representing the array of operation dicts.
:returns: A JSON string with the mapped configuration.
)");
}
