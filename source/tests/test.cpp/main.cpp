// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "TestUtils.h"

// Usd Optimize Core
#include <usd_optimize/core/Core.h>

// carb
#include <carb/logging/ILogging.h>

#define DOCTEST_CONFIG_IMPLEMENT
#include <doctest/doctest.h>


using namespace usd_optimize;

int main(int argc, char** argv)
{
    doctest::Context context(argc, argv);

    // Initialize the Optimizer with all plugins.
    UsdOptimizeCore::getInstance().loadPlugins();

    // Make sure we can get logging inside core.
    UsdOptimizeCore::getInstance().setLoggingInterface(carb::logging::getLogging());

    return context.run();
}
