// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

// Usd Optimize Core
#include "usd_optimize/core/Defs.h"

// Carbonite
#include <carb/logging/Log.h>


namespace usd_optimize
{

/// Free function entry point for the USD_OPTIMIZE_LOG_X macros.
///
/// This is intentionally a free function (rather than a static member of Operation) so that
/// lightweight headers such as CudaUtils.h can use the USD_OPTIMIZE_LOG macros without pulling in the
/// full Operation / USD dependency chain.
///
/// @param level The level. See carb::logging::kLevelVerbose etc.
/// @param fmt The format string
USD_OPTIMIZE_EXPORT void usdOptimizeLog(int32_t level, const char* fmt, ...);

} // namespace usd_optimize

#define USD_OPTIMIZE_LOG(level, fmt, ...) usd_optimize::usdOptimizeLog(level, fmt, ##__VA_ARGS__);

#define USD_OPTIMIZE_LOG_VERBOSE(fmt, ...) USD_OPTIMIZE_LOG(carb::logging::kLevelVerbose, fmt, ##__VA_ARGS__)
#define USD_OPTIMIZE_LOG_INFO(fmt, ...) USD_OPTIMIZE_LOG(carb::logging::kLevelInfo, fmt, ##__VA_ARGS__)
#define USD_OPTIMIZE_LOG_WARN(fmt, ...) USD_OPTIMIZE_LOG(carb::logging::kLevelWarn, fmt, ##__VA_ARGS__)
#define USD_OPTIMIZE_LOG_ERROR(fmt, ...) USD_OPTIMIZE_LOG(carb::logging::kLevelError, fmt, ##__VA_ARGS__)
#define USD_OPTIMIZE_LOG_FATAL(fmt, ...) USD_OPTIMIZE_LOG(carb::logging::kLevelFatal, fmt, ##__VA_ARGS__)

namespace usd_optimize
{

/// Log Level
enum class LogLevel
{
    eDebug = 0, // Debug message
    eInfo = 1, // General useful info message
    eWarning = 2, // Warning message
    eError = 3, // Error
};


/// Convert Usd Optimize log level enum to a carb int.
///
/// \param level The Usd Optimize log level
/// \return The carb logging level
inline int32_t carbLevelFromLogLevel(const LogLevel level)
{
    switch (level)
    {
    case LogLevel::eDebug:
        return carb::logging::kLevelVerbose;
    case LogLevel::eInfo:
        return carb::logging::kLevelInfo;
    case LogLevel::eWarning:
        return carb::logging::kLevelWarn;
    case LogLevel::eError:
        return carb::logging::kLevelError;
    }

    // Fall back to the "default" carb level
    return carb::logging::kLevelWarn;
}

} // namespace usd_optimize
