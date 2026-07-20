Developer Guide
===============

This guide describes how to consume the published **Usd Optimize** package from
your own `packman <https://docs.omniverse.nvidia.com/kit/docs/repo_tools/latest/>`_
and `premake <https://premake.github.io/>`_ based build, so that you can link
against the library and call its C++ API.

To build Usd Optimize itself from source, or to consume a prebuilt binary drop
directly, see the repository ``README.md`` and the install guides under
``docs/install-prebuilt-linux.md`` and ``docs/install-prebuilt-windows.md``.

Linking against the package
---------------------------

1. Update your ``deps/target-deps.packman.xml`` to add a ``usd_optimize``
   dependency with ``linkPath="../_build/target-deps/usd_optimize"``.

2. Add a new file ``deps/usd-optimize-deps.packman.xml`` with the following
   contents:

   .. code-block:: xml

      <project toolsVersion="5.0">
        <import path="../_build/target-deps/usd_optimize/dev/deps/all-deps.packman.xml">
          <filter include="autouv-core" />
          <filter include="omnimesh_ops_usd" />
        </import>

        <dependency name="autouv-core" linkPath="../_build/target-deps/omni_autouv_core" tags="non-redist"/>
        <dependency name="omnimesh_ops_usd" linkPath="../_build/target-deps/omnimesh_ops_usd" tags="non-redist"/>
      </project>

3. Update your ``repo.toml`` to pull the new file. For example:

   .. code-block:: toml

      [repo_build]
      fetch.packman_target_files_to_pull = [
          "${root}/deps/target-deps.packman.xml",
          "${root}/deps/usd-optimize-deps.packman.xml",
      ]

4. Access the ``use_usd_optimize()`` function in your premake by adding the
   following sections.

   .. code-block:: lua

      ...
      usd_optimize_build = require(path.replaceextension(os.matchfiles("_build/target-deps/usd_optimize/*/dev/tools/premake/usd-optimize-public.lua")[1], ""))
      ...
      project "foo_bar"
          usd_optimize_build.use_usd_optimize()
      ...

Calling the API
---------------

Once your project links against Usd Optimize, include the public header and
drive operations through the core singleton:

.. code-block:: cpp

   #include <usd_optimize/core/UsdOptimize.h>

The public C++ interface is documented in the :doc:`../api/api` reference.
The equivalent Python entry points are described in :doc:`python`, and the
operation catalog (with JSON configuration examples that apply equally to the
C++ and Python paths) is in :doc:`operations`.

Extending Usd Optimize
----------------------

New optimizations are added as plugins that subclass ``usd_optimize::Operation``
and register themselves with the core library. The full plugin authoring guide
lives in ``PLUGINS.md`` in the repository root.
