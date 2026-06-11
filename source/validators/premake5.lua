usd_optimize_build = require("tools/premake/usd-optimize-public")


project_with_location("validators_python")

    kind "Utility"

    usd_optimize_build.symlink_folder({
        target_dir = "python/usd_optimize/validators",
        source_dir = "python/usd_optimize/validators",
    })