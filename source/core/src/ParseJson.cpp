// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usd_optimize/core/ParseJson.h"

// Usd Optimize Core
#include "usd_optimize/core/Core.h"
#include "usd_optimize/core/Log.h"
#include "usd_optimize/core/Operation.h"
#include "usd_optimize/core/Utils.h"

// USD
#include <pxr/base/js/json.h>
#include <pxr/base/js/utils.h>
#include <pxr/usd/usdUtils/stageCache.h>

// C++
#include <fstream>

PXR_NAMESPACE_USING_DIRECTIVE


namespace usd_optimize
{


static int _getIntVal(const JsObject& object, const std::string& arg, int defaultValue = 0)
{
    auto itr = JsFindValue(object, arg);
    if (itr && itr->IsInt())
    {
        return itr->GetInt();
    }

    return defaultValue;
}


bool _parseJson(const UsdStageWeakPtr& usdStage, const std::string& str, ExecutionContext* context)
{
    JsValue document;
    JsParseError error;

    // First check whether the string is a file on disk. If so, read it.
    std::ifstream input_stream;
    input_stream.open(str, std::ifstream::in);

    if (input_stream)
    {
        // Parse it into a Document then release the stream.
        document = JsParseStream(input_stream, &error);
        input_stream.close();
    }
    else
    {
        // If the string is not a file on disk, try and parse it as JSON.
        document = JsParseString(str, &error);
    }

    // Check for any useful parsing error that could be reported back
    if (!error.reason.empty())
    {
        USD_OPTIMIZE_LOG_WARN("Error parsing JSON: %s at line %d, col %d", error.reason.c_str(), error.line, error.column);
        return false;
    }

    // Check at this point that we have a valid document
    if (!document)
    {
        USD_OPTIMIZE_LOG_WARN("Could not read JSON: %s", str.c_str());
        return false;
    }

    return _parseJson(usdStage, document, context);
}


bool _parseJson(const UsdStageWeakPtr& usdStage, const JsValue& document, ExecutionContext* context)
{

    // Always make a new context. We might end up changing it as the commands are parsed from
    // a config, and we don't want to modify the incoming one.
    ExecutionContext _context;
    usd_optimize_execution_context_copy(&_context, context);

    // Exit if the document is not an array of commands.
    if (!document.IsArray())
    {
        USD_OPTIMIZE_LOG_WARN("JSON commands is not an array");
        return false;
    }

    // We need to use a StageCache::Id to pass through the stage. Get the StageCache
    // and check if it has already been cached. If not, we add it, and then make a
    // note to remove it again afterward.
    UsdStageCache& stageCache = UsdUtilsStageCache::Get();
    UsdStageCache::Id stageId = stageCache.GetId(usdStage);

    // If it was not in the stage cache then insert, and track that, so we can remove it later.
    bool insertedStage = false;
    if (!stageId.IsValid())
    {
        stageId = stageCache.Insert(usdStage);
        insertedStage = true;
    }

    // Set the stage id.
    _context.usdStageId = stageId.ToLongInt();

    const JsArray& commands = document.GetJsArray();

    bool rc = true;

    // Iterate each command.
    for (const JsValue& command : commands)
    {

        if (!command.IsObject())
        {
            USD_OPTIMIZE_LOG_WARN("Not an object: %s", JsWriteToString(command).c_str());
            return false;
        }

        const JsObject& _command = command.GetJsObject();

        // Figure out what operation this is
        auto operationItr = JsFindValue(_command, "operation");
        if (!operationItr || !operationItr->IsString())
        {
            USD_OPTIMIZE_LOG_WARN("Invalid or missing operation name: %s", JsWriteToString(command).c_str());
            return false;
        }

        const std::string& operationName = operationItr->GetString();

        // Global configuration
        // Process this before creating a timer, we don't need to time reading a couple of JSON values.
        if (operationName == "executionContext")
        {
            _context.generateReport = _getIntVal(_command, "generateReport", _context.generateReport);
            _context.verbose = _getIntVal(_command, "verbose", _context.verbose);
            _context.singleThreaded = _getIntVal(_command, "singleThreaded", _context.singleThreaded);
            _context.debug = _getIntVal(_command, "debug", _context.debug);

            continue;
        }

        // Found an operation name. Look up the plugin
        auto operation = UsdOptimizeCore::getInstance().getOperation(operationName);
        if (operation == nullptr)
        {
            USD_OPTIMIZE_LOG_WARN("Could not find operation %s", operationName.c_str());
            continue;
        }

        const JsObject mappedCommand = UsdOptimizeCore::getInstance().mapOperation(operation->getName(), _command);

        // Create a scoped timer and run the operation.
        // At this point we only need to pass the arguments on and let the operation class handle processing
        // them.
        std::ostringstream oss;
        oss << "Executed " << operationName;

        if (_context.analysisMode)
        {
            oss << " analysis";
        }

        OperationResult result;
        {
            ScopedTimer _timer(oss.str());
            result = operation->execute(&_context, mappedCommand);
        }

        if (!result.success)
        {
            std::ostringstream ossErr;
            ossErr << "Execution failed";

            if (result.error != nullptr)
            {
                ossErr << ": " << result.error;
            }

            ossErr << " - aborting";
            USD_OPTIMIZE_LOG_WARN("%s", ossErr.str().c_str());

            rc = false;
        }

        usd_optimize_operation_result_free(&result);

        // After cleaning up, break if we set rc to false, to not process any other operations.
        // Then the rest of the cleanup can happen as usual.
        if (!rc)
        {
            break;
        }
    }

    // If we previously inserted the stage, then remove it now.
    if (insertedStage)
    {
        stageCache.Erase(stageId);
    }

    // If we generated a report, we should copy this value back.
    if (context != nullptr)
    {
        if (context->reportPath != nullptr)
        {
            free(context->reportPath);
        }
        context->reportPath = _context.reportPath;

        // Clear out the pointer, so it won't be free'd here, leading to
        // a double free when the caller responsibly cleans up their data..
        _context.reportPath = nullptr;
    }

    // Clean up the context
    usd_optimize_execution_context_free(&_context);

    return rc;
}

} // namespace usd_optimize
