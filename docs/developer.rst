Developer Guide
===============

1. Update your `deps/target-deps.packman.xml` to add an `usd_optimize` dependency with `linkPath="../_build/target-deps/usd_optimize"`

2. Add a new file `deps/usd-optimize-deps.packman.xml` with the following contents:

.. code-block:: xml

   <project toolsVersion="5.0">
     <import path="../_build/target-deps/usd_optimize/dev/deps/all-deps.packman.xml">
       <filter include="autouv-core" />
       <filter include="omnimesh_ops_usd" />
     </import>

     <dependency name="autouv-core" linkPath="../_build/target-deps/omni_autouv_core" tags="non-redist"/>
     <dependency name="omnimesh_ops_usd" linkPath="../_build/target-deps/omnimesh_ops_usd" tags="non-redist"/>
   </project>

3. Update your `repo.toml` to pull the new file. For example:

.. code-block:: toml

   [repo_build]
   fetch.packman_target_files_to_pull = [
       "${root}/deps/target-deps.packman.xml",
       "${root}/deps/usd-optimize-deps.packman.xml",
   ]

4. Access the `use_usd_optimize()` function in your premake by adding the following sections.

.. code-block:: lua

   ...
   usd_optimize_build = require(path.replaceextension(os.matchfiles("_build/target-deps/usd_optimize/*/dev/tools/premake/usd-optimize-public.lua")[1], ""))
   ...
   project "foo_bar"
       usd_optimize_build.use_usd_optimize()
   ...
