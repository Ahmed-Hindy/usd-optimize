# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


from pxr import Usd, UsdGeom

from .test_utils import Test_Operation, _get_context, _get_meshes, _get_test_data_file_path

DEFAULT_ARGS = {
    "paths": [],
    "mergeVertices": True,
    "tolerance": 0.0,
    "mergeBoundaries": True,
    "mergeNeighbors": True,
    "contractDegenerateEdges": True,
    "removeDegenerateFaces": True,
    "removeIsolatedVertices": True,
    "removeDuplicateFaces": True,
    "makeManifold": False,
}


class Test_Operation_Mesh_Cleanup(Test_Operation):

    OPERATION = "meshCleanup"

    async def test_analysis_zero_extent_meshes_no_crash(self):
        """Regression: omo::checkClean() did an out-of-bounds heap write on fully-degenerate
        zero-extent (all-points-coincident) meshes. Two or more such meshes in a stage crashed
        meshCleanup analysis with an intermittent SIGSEGV (hit in the validate -> --fix ->
        revalidate loop, whose --fix step splits a degenerate mesh into zero-extent parts).
        Analysis must skip such meshes and complete instead of crashing the process.
        """
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Xform.Define(stage, "/World")
        # Two meshes whose points are all coincident (zero-extent) -- the crash trigger.
        for name, base_x in (("A", -50.0), ("B", 50.0)):
            mesh = UsdGeom.Mesh.Define(stage, "/World/{}".format(name))
            mesh.CreateFaceVertexCountsAttr([4])
            mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
            mesh.CreatePointsAttr([(base_x, -50, 50)] * 4)

        context = _get_context(stage, analysis=True)
        # Pre-fix this SIGSEGV'd the process; post-fix it must return a successful analysis result.
        _, result = self._execute_command(DEFAULT_ARGS.copy(), context=context)
        self.assertTrue(result[0])

    async def test_merge_vertices(self):
        """Test merge vertices"""
        stage = self._open_stage("mergeColocatedVertices_input.usd")
        before_meshes = _get_meshes(stage)
        self.assertEqual(len(before_meshes), 2)

        file_path = _get_test_data_file_path("mergeColocatedVertices_output.usd")
        expected_stage = Usd.Stage.Open(file_path)
        after_meshes = _get_meshes(expected_stage)
        self.assertEqual(len(before_meshes), len(after_meshes))

        for i in range(0, len(before_meshes)):
            mesh = UsdGeom.Mesh(before_meshes[i])
            after_mesh = UsdGeom.Mesh(after_meshes[i])
            # before operation, the vertices have not been merged
            self.assertGreaterEqual(len(mesh.GetPointsAttr().Get()), len(after_mesh.GetPointsAttr().Get()))
            # some degenerate faces have been removed, so faces will not match
            self.assertGreaterEqual(
                len(mesh.GetFaceVertexCountsAttr().Get()), len(after_mesh.GetFaceVertexCountsAttr().Get())
            )

        self._execute_json(stage, "cleanup_merge_vertices.json")

        for i in range(0, len(before_meshes)):
            mesh = UsdGeom.Mesh(before_meshes[i])
            after_mesh = UsdGeom.Mesh(after_meshes[i])
            # after operation, colocated vertices have been merged
            self.assertEqual(len(mesh.GetPointsAttr().Get()), len(after_mesh.GetPointsAttr().Get()))
            # face count should remain the same as before
            self.assertEqual(len(mesh.GetFaceVertexCountsAttr().Get()), len(after_mesh.GetFaceVertexCountsAttr().Get()))

    async def test_merge_vertices_negative_tolerance(self):
        stage = self._open_stage("mergeColocatedVertices_input.usd")
        before_meshes = _get_meshes(stage)
        self.assertEqual(len(before_meshes), 2)

        file_path = _get_test_data_file_path("mergeColocatedVertices_input.usd")
        expected_stage = Usd.Stage.Open(file_path)
        after_meshes = _get_meshes(expected_stage)
        self.assertEqual(len(before_meshes), len(after_meshes))

        for i in range(0, len(before_meshes)):
            mesh = UsdGeom.Mesh(before_meshes[i])
            after_mesh = UsdGeom.Mesh(after_meshes[i])
            # before operation, the vertices have not been merged
            self.assertGreaterEqual(len(mesh.GetPointsAttr().Get()), len(after_mesh.GetPointsAttr().Get()))
            # some degenerate faces have been removed, so faces will not match
            self.assertGreaterEqual(
                len(mesh.GetFaceVertexCountsAttr().Get()), len(after_mesh.GetFaceVertexCountsAttr().Get())
            )

        context = _get_context(stage, report=True)

        # Execute the command and assert success
        args = DEFAULT_ARGS.copy()
        args["tolerance"] = -30.0
        success, result = self._execute_command(args, context)
        self.assertTrue(success)

        for i in range(0, len(before_meshes)):
            mesh = UsdGeom.Mesh(before_meshes[i])
            after_mesh = UsdGeom.Mesh(after_meshes[i])
            # after operation, colocated vertices have been merged
            self.assertEqual(len(mesh.GetPointsAttr().Get()), len(after_mesh.GetPointsAttr().Get()))
            # face count should remain the same as before
            self.assertEqual(len(mesh.GetFaceVertexCountsAttr().Get()), len(after_mesh.GetFaceVertexCountsAttr().Get()))

    async def test_merge_vertices_with_path(self):
        stage = self._open_stage("mergeColocatedVertices_input.usd")
        before_meshes = _get_meshes(stage)
        self.assertEqual(len(before_meshes), 2)

        file_path = _get_test_data_file_path("mergeColocatedVertices_output.usd")
        expected_stage = Usd.Stage.Open(file_path)
        after_meshes = _get_meshes(expected_stage)
        self.assertEqual(len(before_meshes), len(after_meshes))

        for i in range(0, len(before_meshes)):
            mesh = UsdGeom.Mesh(before_meshes[i])
            after_mesh = UsdGeom.Mesh(after_meshes[i])
            # before operation, the vertices have not been merged
            self.assertGreaterEqual(len(mesh.GetPointsAttr().Get()), len(after_mesh.GetPointsAttr().Get()))
            # some degenerate faces have been removed, so faces will not match
            self.assertGreaterEqual(
                len(mesh.GetFaceVertexCountsAttr().Get()), len(after_mesh.GetFaceVertexCountsAttr().Get())
            )

        context = _get_context(stage, report=True)

        # Execute the command and assert success
        target_prim_path = "/World/_2858cfbe856f11eba06d005056bc75e0____/Geometry/sourcefile_16777215/CP_SUBTRACT_8424307/shape_2_merged_mesh"
        args = DEFAULT_ARGS.copy()
        args["paths"] = [target_prim_path]
        success, result = self._execute_command(args, context)
        self.assertTrue(success)

        for i in range(0, len(before_meshes)):
            mesh = UsdGeom.Mesh(before_meshes[i])
            after_mesh = UsdGeom.Mesh(after_meshes[i])
            if mesh.GetPath() == target_prim_path:
                # after operation, colocated vertices have been merged
                self.assertEqual(len(mesh.GetPointsAttr().Get()), len(after_mesh.GetPointsAttr().Get()))
                # face count should remain the same as before
                self.assertEqual(
                    len(mesh.GetFaceVertexCountsAttr().Get()), len(after_mesh.GetFaceVertexCountsAttr().Get())
                )
            else:
                self.assertNotEqual(len(mesh.GetPointsAttr().Get()), len(after_mesh.GetPointsAttr().Get()))

    async def test_merge_vertices_no_path(self):
        stage = self._open_stage("mergeColocatedVertices_input.usd")
        before_meshes = _get_meshes(stage)
        self.assertEqual(len(before_meshes), 2)

        # Check vert count before on a selected mesh
        target_prim_path = "/World/_2858cfbe856f11eba06d005056bc75e0____/Geometry/sourcefile_16777215/CP_SUBTRACT_8424307/shape_2_merged_mesh"
        prim = stage.GetPrimAtPath(target_prim_path)
        mesh = UsdGeom.Mesh(prim)
        verts_before = len(mesh.GetPointsAttr().Get())

        context = _get_context(stage, report=True)

        # Execute the command on the toplevel prim
        args = DEFAULT_ARGS.copy()
        args["paths"] = ["/World//"]
        success, result = self._execute_command(args, context)
        self.assertTrue(success)

        # Verify mesh has been reduced even though not explicitly at the exact prim path
        verts_after = len(mesh.GetPointsAttr().Get())
        self.assertNotEqual(verts_before, verts_after)

    async def test_time_varying_mesh(self):
        """Test merge vertices operation on a mesh with authored time varying attributes, the mesh should not be processed"""
        stage = self._open_stage("time_varying_mesh.usd")

        context = _get_context(stage, report=True)

        # copy default args
        args = DEFAULT_ARGS.copy()
        # execute command
        success, result = self._execute_command(args, context)

        # currently skipping time sampled meshes to avoid a crash
        # test to be expanded when time samples are better handled in the operation
        # asserts success of execution
        self.assertTrue(success)

    async def test_analysis(self):
        """Test analysis mode"""

        # Analysis enables every fix (including makeManifold) so checkClean reports all defect categories. makeManifold
        # is excluded from DEFAULT_ARGS only because it conflicts with vertex merging during an actual cleanup; in
        # analysis mode nothing is written, so there is no conflict.
        analysis_args = DEFAULT_ARGS.copy()
        analysis_args["makeManifold"] = True

        # First test scene
        stage = self._open_stage("cubeDegenerateFaces.usda")
        context = _get_context(stage, analysis=True)
        success, result = self._execute_command(analysis_args, context)

        # Assert analysis exists
        self.assertTrue(success)
        self.assertTrue(result[0])
        self.assertTrue("analysis" in result[2])
        analysis = result[2]["analysis"]

        # Assert expected results
        self.assertTrue("meshesWithMergeableVertices" in analysis)
        self.assertTrue("meshesThatAreNonManifolds" in analysis)
        self.assertTrue("meshesWithDegenerateEdges" in analysis)
        self.assertTrue("meshesWithDegenerateFaces" in analysis)
        self.assertTrue("meshesWithIsolatedVertices" in analysis)
        self.assertTrue("meshesWithDuplicateFaces" in analysis)
        self.assertEqual(analysis["meshesWithMergeableVertices"], 0)
        self.assertEqual(analysis["meshesThatAreNonManifolds"], 1)
        self.assertEqual(analysis["meshesWithDegenerateEdges"], 1)
        self.assertEqual(analysis["meshesWithDegenerateFaces"], 1)
        self.assertEqual(analysis["meshesWithIsolatedVertices"], 1)
        self.assertEqual(analysis["meshesWithDuplicateFaces"], 0)

        # The additive per-prim path lists must mirror the counts above so
        # verbose reporting can name the offending prims.
        self._assert_paths_match_counts(analysis)

        # Second test scene
        stage = self._open_stage("mergeColocatedVertices_input.usd")
        context = _get_context(stage, analysis=True)
        success, result = self._execute_command(analysis_args, context)

        # Assert analysis exists
        self.assertTrue(success)
        self.assertTrue(result[0])
        self.assertTrue("analysis" in result[2])
        analysis = result[2]["analysis"]

        # Assert expected results
        self.assertTrue("meshesWithMergeableVertices" in analysis)
        self.assertTrue("meshesThatAreNonManifolds" in analysis)
        self.assertTrue("meshesWithDegenerateEdges" in analysis)
        self.assertTrue("meshesWithDegenerateFaces" in analysis)
        self.assertTrue("meshesWithIsolatedVertices" in analysis)
        self.assertTrue("meshesWithDuplicateFaces" in analysis)
        self.assertEqual(analysis["meshesWithMergeableVertices"], 2)
        self.assertEqual(analysis["meshesThatAreNonManifolds"], 0)
        # Merging colocated vertices welds coincident points, which collapses edges/faces in both meshes; the combined
        # pipeline reports those merge-induced degeneracies (they did not exist in the unmerged input).
        self.assertEqual(analysis["meshesWithDegenerateEdges"], 2)
        self.assertEqual(analysis["meshesWithDegenerateFaces"], 2)
        self.assertEqual(analysis["meshesWithIsolatedVertices"], 0)
        self.assertEqual(analysis["meshesWithDuplicateFaces"], 0)

        self._assert_paths_match_counts(analysis)

    def _assert_paths_match_counts(self, analysis):
        """Each ``*Paths`` list must be present and as long as its counter."""
        for count_key in (
            "meshesWithMergeableVertices",
            "meshesThatAreNonManifolds",
            "meshesWithDegenerateEdges",
            "meshesWithDegenerateFaces",
            "meshesWithIsolatedVertices",
            "meshesWithDuplicateFaces",
        ):
            paths_key = count_key + "Paths"
            self.assertIn(paths_key, analysis)
            self.assertEqual(len(analysis[paths_key]), analysis[count_key])
            # Entries are prim path strings.
            for path in analysis[paths_key]:
                self.assertTrue(str(path).startswith("/"))
