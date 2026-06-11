project_with_location("findOccludedMeshes")
    usd_optimize_build.use_mesh_tools()
    usd_optimize_build.operation_plugin({ "*.cpp" })
