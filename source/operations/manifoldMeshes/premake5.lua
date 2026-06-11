project_with_location("manifoldMeshes")
    usd_optimize_build.use_omni_mesh()
    usd_optimize_build.operation_plugin({ "*.cpp" })
