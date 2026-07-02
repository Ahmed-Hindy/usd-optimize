usd_optimize_build = require("tools/premake/usd-optimize-public")

-- Set up the location names for the plugin
local namespace = "usd_optimize/core"
local plugin_source_path = "plugins"


project_with_location("usd_optimize.core")

    -- build the shared library for usd optimize core
    usd_optimize_build.shared_library({
        library_name = "core",
        headers = { "src/**/*.h" },
        sources = { "src/**.cpp" }
    })
    removefiles { "src/UsdOptimizeInterface.cpp", "src/usdOptimize.cpp" }

    local lib_dir = "%{root}/_build/%{cfg.system}-%{cfg.platform}/%{config}/lib"

    -- Copy third-party libs into the lib dir so they will be picked up at runtime.
    repo_build.prebuild_copy {
        {"%{root}/_build/target-deps/autouv-core/%{config}/lib/*", lib_dir},
        {"%{root}/_build/target-deps/omnimesh_ops_usd/%{config}/lib/*", lib_dir},
        {"%{root}/_build/target-deps/mesh_tools/%{config}/lib/*", lib_dir},
        -- Operation name/attribute mapping
        {"config/operation_mapping.json", lib_dir},
    }

    -- Copy USD and Python libs to an extraLibs dir for testing
    local extra_dir = "%{root}/_build/%{cfg.system}-%{cfg.platform}/%{config}/extraLibs"
    repo_build.prebuild_copy{
        {target_deps.."/usd/%{config}/lib/*", extra_dir},
        {target_deps.."/usd/%{config}/lib/usd", extra_dir.."/usd"}
    }

    -- A couple of extra libs that are found in different places on windows
    if os.target() == "windows" then
        repo_build.prebuild_copy{
            {target_deps.."/usd/%{config}/bin/tbb12*.dll", extra_dir},
            {target_deps.."/python/python"..string.gsub(PYTHON_VERSION, "%.", "")..".dll", extra_dir},
        }
    end


project_with_location("core_python")

    dependson( "usd_optimize.core" )

    -- build the python bindings for usd optimize core
    usd_optimize_build.use_python()
    usd_optimize_build.use_usd()
    usd_optimize_build.use_mesh_tools()
    usd_optimize_build.use_omni_mesh()
    usd_optimize_build.use_usd_optimize_core()

    -- `module_name` is set explicitly because the helper's auto-derivation
    -- (`bindings_module_name:gsub("_", ".")`) would split `usd_optimize`
    -- into `usd.optimize` — the package is a single dotted segment.
    usd_optimize_build.python_bindings({
        module_name = "usd_optimize.impl.core",
        bindings_module_name = "usd_optimize_impl_core",
        bindings_sources = "bindings/BindingsPython.cpp",
        python_sources = "python/usd_optimize/impl/core/*.py",
    })

    repo_build.prebuild_copy({
        "python/usd_optimize/bootstrap.py",
        "%{root}/_build/%{cfg.system}-%{cfg.platform}/%{config}/python/usd_optimize",
    })

    usd_optimize_build.symlink_folder({
        target_dir = "python/usd_optimize/core",
        source_dir = "python/usd_optimize/core",
    })

    -- Back-compat shim: `import omni.scene.optimizer.<sub>` is transparently
    -- aliased to `usd_optimize.<sub>` by a sys.meta_path finder installed in
    -- the shim's __init__.py. Drop this symlink once the deprecation window
    -- closes.
    usd_optimize_build.symlink_folder({
        target_dir = "python/omni/scene/optimizer",
        source_dir = "python/omni/scene/optimizer",
    })


-- Build standalone CLI tool
-- Currently this is only built locally, for dev purposes
if not os.getenv("CI_PIPELINE_ID") then

    project_with_location("usdOptimize")

        dependson("usd_optimize.core")

        kind "ConsoleApp"
        staticruntime "Off"

        -- Standard way of building in Omniverse
        exceptionhandling "On"
        rtti "On"
        language "C++"

        -- Define the runtime to match the build configuration
        filter { "configurations:debug" }
            runtime "Debug"
        filter  { "configurations:release" }
            runtime "Release"
        filter {}

        includedirs {
            "%{root}/_build/%{platform}/%{config}/include",
            "%{root}/source/pch"
        }

        externalincludedirs {
            "%{root}/_build/target-deps/usd/%{config}/include",
            "%{root}/_build/target-deps/python/include/python"..PYTHON_VERSION,
        }

        -- Disable manifest generation, so our custom one is used
        -- This enables long path support on windows
        filter { "system:windows" }
        flags {"NoManifest"}
        filter {}

        -- Copy batch file to set environment for execution
        if os.target() == "windows" then
            repo_build.prebuild_copy{
                {"%{root}/source/core/src/usdOptimize.bat", "%{root}/_build/%{cfg.system}-%{cfg.platform}/%{config}"},
            }
        end

        enable_gcov()

        -- source code to compile
        files { "src/UsdOptimizeInterface.cpp", "src/usdOptimize.cpp" }

        repo_build.prebuild_copy {
            {target_deps.."/python/lib/libpython*", extra_dir},
        }

        -- RPATH the lib dir for linux.
        runpathdirs("$OextraLibs")

        -- Use the copied libs to link against as well to ensure we are linking against the
        -- same thing.
        local extra_dir = "%{root}/_build/%{cfg.system}-%{cfg.platform}/%{config}/extraLibs"
        libdirs { extra_dir }

        -- Linux-specific compile information
        filter { "system:linux" }
            exceptionhandling "On"
            removeflags { "UndefinedIdentifiers" }

            -- Use older runpath behavior
            -- Without, some (not all) of the USD libs will not be found
            -- correctly, even though they're in the correct dir.
            linkoptions { "-Wl,--disable-new-dtags" }
        filter {}

        usd_optimize_build.use_python()
        usd_optimize_build.use_usd_optimize_core()

        -- Link against the actual usd optimize shared lib
        links {'usd_optimize.core'}

        add_usd {"ar","vt", "gf", "pcp", "sdf", "arch", "usd", "tf", "js", "trace", "usdUtils", "usdGeom", "usdPhysics", "usdShade", "usdSkel", "work", "kind"}
        add_usd {"usdLux", "plug", "python"}

        filter { "configurations:debug" }
            links {"tbb_debug"}
        filter  { "configurations:release" }
            links {"tbb"}
        filter {}
end