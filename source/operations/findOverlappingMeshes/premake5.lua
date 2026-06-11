project_with_location("findOverlappingMeshes")
    usd_optimize_build.use_omni_mesh()
    usd_optimize_build.use_mesh_tools()
    usd_optimize_build.operation_plugin({ "*.cpp" })
