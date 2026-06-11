project_with_location("generateAtlasUVs")
    -- system includedirs. Filtered so we can exclude warnings from them.
    externalincludedirs {
        target_deps.."/autouv-core/include",
    }

    -- External libraries to link against
    -- AutoUV
    links {"autouv-core"}

    libdirs {
        target_deps.."/autouv-core/%{config}/lib",
    }

    usd_optimize_build.operation_plugin({ "*.cpp" })
