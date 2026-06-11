# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#


import re

from pxr import UsdGeom

from .scripts import standalone
from .test_utils import Test_Operation, _get_context, _get_meshes

# MergePointOption values
MERGE_POINT_DEFAULT = 0  # Use pseudo root prim

# Spatial Mode values
SPATIAL_MODE_BOUNDING = 1
SPATIAL_MODE_VERTEX = 2
SPATIAL_MODE_COINCIDENT_BOUNDARY = 3

# Default arguments for the command
DEFAULT_ARGS = {
    "meshPrimPaths": [],
    "considerMaterials": False,
    "materialAlbedoAsVertexColors": False,
    "originalGeomOption": 1,
    "mergePoint": MERGE_POINT_DEFAULT,
    "rootPath": "",
}


def _parse_report(reportPath):
    """Parse a report and return a dictionary of merged mesh to the meshes that
    were merged in to it"""

    # We really just want to parse out what input meshes ended up in each
    # merged mesh. This is a little ropey, if the report format changes..
    regexOutput = re.compile(r"INFO\|MERGE\|Output Mesh: (.+) contains\s(\d+)$")
    regexMesh = re.compile(r"^INFO\|MERGE\|(.+)$")

    with open(reportPath) as f:
        result = dict()
        lines = f.readlines()

        # Track the current mesh, and also the counter so we know how
        # many lines follow.
        mergedMesh = None
        mergedMeshCounter = 0

        for line in lines:
            match = regexOutput.search(line)
            if match:
                # New output mesh. Adjust the mesh key and reset counter
                mergedMesh = match.group(1)
                mergedMeshCounter = int(match.group(2))
                result[mergedMesh] = list()
            elif mergedMesh and mergedMeshCounter:
                match = regexMesh.search(line)
                if match:
                    # Found a mesh thats part of the current mergedMesh
                    result[mergedMesh].append(match.group(1))
                    mergedMeshCounter -= 1

    return result


class Test_Operation_Merge_Spatial(Test_Operation):

    OPERATION = "merge"

    async def test_spatial_basic(self):
        """Basic spatial merging test on a simple scene"""

        stage = self._open_stage("mergeSpatial.usda")

        # Run merge with spatial settings enabled
        # These settings will cause only a few things to be merged in the test scene
        merge_args = DEFAULT_ARGS.copy()
        merge_args["spatialMode"] = SPATIAL_MODE_BOUNDING
        merge_args["spatialThreshold"] = 20.0
        merge_args["spatialMaxSize"] = 500.0

        # Custom execution context
        context = _get_context(stage, report=True)

        # Verify original mesh count
        meshes = _get_meshes(stage)
        self.assertEqual(len(meshes), 27)

        # Run the merge
        self._execute_command(merge_args, context)

        # Need a report
        self.assertIsNotNone(context.reportPath)

        # Verify expected actual mesh count after spatial merge
        meshes = _get_meshes(stage)
        self.assertEqual(len(meshes), 21)

        # Parse the report. This will extract each merged mesh with a list
        # of the original meshes that were merged in to it. We can use this
        # to verify that the things we expected to spatially merge did so
        # in a more readable form than getting the merged prims and testing
        # their topology.
        merged = _parse_report(context.reportPath)
        self.assertEqual(len(merged.keys()), 3)

        # Verify the expected meshes
        self.assertTrue(stage.GetPrimAtPath("/merged"))
        merged_list = ["/World/Cube_23", "/World/Cube_22", "/World/Cube_20", "/World/Cube_18"]
        self.assertListEqual(merged["/merged"], merged_list)

        self.assertTrue(stage.GetPrimAtPath("/merged_1"))
        merged_1_list = ["/World/Cube_13", "/World/Cube_12", "/World/Cube_11"]
        self.assertListEqual(merged["/merged_1"], merged_1_list)

        self.assertTrue(stage.GetPrimAtPath("/merged_2"))
        merged_2_list = ["/World/Cube_02", "/World/Cube_01"]
        self.assertListEqual(merged["/merged_2"], merged_2_list)

        # Finally check that any of the prims that claim to have been merged
        # are no longer valid.
        for m in merged:
            for p in merged[m]:
                self.assertFalse(stage.GetPrimAtPath(p))

    async def test_spatial_larger_size(self):
        """Basic spatial merging test on a simple scene with larger output size"""

        stage = self._open_stage("mergeSpatial.usda")

        # Run spatial merge
        # This has an increased threshold/max to merge more of the scene
        merge_args = DEFAULT_ARGS.copy()
        merge_args["spatialMode"] = SPATIAL_MODE_BOUNDING
        merge_args["spatialThreshold"] = 100.0
        merge_args["spatialMaxSize"] = 1000.0

        # Custom execution context
        context = _get_context(stage, report=True)

        # Verify original mesh count
        meshes = _get_meshes(stage)
        self.assertEqual(len(meshes), 27)

        # Run the merge
        self._execute_command(merge_args, context)

        # Need a report
        self.assertIsNotNone(context.reportPath)

        # Verify expected actual mesh count after spatial merge
        meshes = _get_meshes(stage)
        self.assertEqual(len(meshes), 11)

        # Parse the report
        merged = _parse_report(context.reportPath)
        self.assertEqual(len(merged.keys()), 5)

        # Then verify the new merge result
        self.assertTrue(stage.GetPrimAtPath("/merged"))
        merged_list = ["/World/Cube_25", "/World/Cube_24"]
        self.assertListEqual(merged["/merged"], merged_list)

        self.assertTrue(stage.GetPrimAtPath("/merged_1"))
        merged_1_list = [
            "/World/Cube_23",
            "/World/Cube_22",
            "/World/Cube_21",
            "/World/Cube_20",
            "/World/Cube_19",
            "/World/Cube_18",
            "/World/Cube_17",
        ]
        self.assertListEqual(merged["/merged_1"], merged_1_list)

        self.assertTrue(stage.GetPrimAtPath("/merged_2"))
        merged_2_list = [
            "/World/Cube_16",
            "/World/Cube_15",
            "/World/Cube_14",
            "/World/Cube_13",
            "/World/Cube_12",
            "/World/Cube_11",
            "/World/Cube_10",
        ]
        self.assertListEqual(merged["/merged_2"], merged_2_list)

        self.assertTrue(stage.GetPrimAtPath("/merged_3"))
        merged_3_list = ["/World/Cube_09", "/World/Cube_07", "/World/Cube_04"]
        self.assertListEqual(merged["/merged_3"], merged_3_list)

        self.assertTrue(stage.GetPrimAtPath("/merged_4"))
        merged_4_list = ["/World/Cube_02", "/World/Cube_01"]
        self.assertListEqual(merged["/merged_4"], merged_4_list)

        # Finally check that any of the prims that claim to have been merged
        # are no longer valid.
        for m in merged:
            for p in merged[m]:
                self.assertFalse(stage.GetPrimAtPath(p))

    async def test_spatial_smaller_threshold(self):
        """Basic spatial merging test on a simple scene with a small threshold"""

        stage = self._open_stage("mergeSpatial.usda")

        # Run spatial merge
        # This has an increased threshold/max to merge more of the scene
        merge_args = DEFAULT_ARGS.copy()
        merge_args["spatialMode"] = SPATIAL_MODE_BOUNDING
        merge_args["spatialThreshold"] = 1.0
        merge_args["spatialMaxSize"] = 1000.0

        # Custom execution context
        context = _get_context(stage, report=True)

        # Verify original mesh count
        meshes = _get_meshes(stage)
        self.assertEqual(len(meshes), 27)

        # Run the merge
        self._execute_command(merge_args, context)

        # Need a report
        self.assertIsNotNone(context.reportPath)

        # Verify expected actual mesh count after spatial merge
        meshes = _get_meshes(stage)
        self.assertEqual(len(meshes), 23)

        # Parse the report
        merged = _parse_report(context.reportPath)
        self.assertEqual(len(merged.keys()), 3)

        # Then verify the new merge result
        self.assertTrue(stage.GetPrimAtPath("/merged"))
        merged_list = ["/World/Cube_23", "/World/Cube_22"]
        self.assertListEqual(merged["/merged"], merged_list)

        self.assertTrue(stage.GetPrimAtPath("/merged_1"))
        merged_1_list = [
            "/World/Cube_13",
            "/World/Cube_12",
            "/World/Cube_11",
        ]
        self.assertListEqual(merged["/merged_1"], merged_1_list)

        self.assertTrue(stage.GetPrimAtPath("/merged_2"))
        merged_2_list = [
            "/World/Cube_02",
            "/World/Cube_01",
        ]
        self.assertListEqual(merged["/merged_2"], merged_2_list)

        # Finally check that any of the prims that claim to have been merged
        # are no longer valid.
        for m in merged:
            for p in merged[m]:
                self.assertFalse(stage.GetPrimAtPath(p))

    def _merge_vertex_with_limit(self, stage, vertex_limit, expected_meshes):
        """Helper function to repeat vertex limit tests"""

        # Run spatial merge with a relatively small max vertices count
        merge_args = DEFAULT_ARGS.copy()
        merge_args["spatialMode"] = SPATIAL_MODE_VERTEX
        merge_args["spatialVertexCount"] = vertex_limit

        # Custom execution context to enable reporting
        context = _get_context(stage, report=True)

        # Run the merge
        self._execute_command(merge_args, context)

        # Assert the expected number of output meshes based on the vertex limit
        merged = _parse_report(context.reportPath)
        self.assertEqual(len(merged.keys()), expected_meshes)

        # Get each "merged*" mesh and verify it has less than the limit
        for prim in stage.Traverse():
            if "merged" in prim.GetName():
                fvc = len(prim.GetAttribute("faceVertexIndices").Get())
                self.assertLess(fvc, vertex_limit)

    async def test_spatial_max_vertex(self):
        """Basic spatial merging test on a simple scene"""

        stage = self._open_stage("mergeSpatial.usda")

        # Verify original mesh count
        meshes = _get_meshes(stage)
        self.assertEqual(len(meshes), 27)

        # Test merging with a max vertex limit of 100
        self._merge_vertex_with_limit(stage, 100, 8)

        # Re-open stage and test again using 250
        stage = self._open_stage("mergeSpatial.usda")
        self._merge_vertex_with_limit(stage, 250, 4)

        # One more test with a much higher limit
        stage = self._open_stage("mergeSpatial.usda")
        self._merge_vertex_with_limit(stage, 10000, 1)

    async def test_spatial_debug_colors(self):
        """Basic spatial merging writing debug colors"""

        stage = self._open_stage("mergeSpatial.usda")

        # 27 meshes
        meshes = [x for x in stage.Traverse() if UsdGeom.Mesh(x)]
        self.assertEqual(len(meshes), 27)

        # None should have a displayColor to start with
        for mesh in meshes:
            papi = UsdGeom.PrimvarsAPI(mesh)
            primvar = papi.GetPrimvar("displayColor")
            self.assertIsNone(primvar.Get())

        # Execute command via JSON, which supports spatialDebug
        json = """[
            {"operation": "merge",
            "meshPrimPaths": [],
            "considerMaterials": false,
            "materialAlbedoAsVertexColors": false,
            "originalGeomOption": 1,
            "mergePoint": 0,
            "rootPath": "",
            "spatialMode": 1,
            "spatialThreshold": 500.0,
            "spatialMaxSize": 1000.0,
            "spatialDebug": true }]"""
        status = standalone.execute_commands_from_json(stage, json)
        self.assertTrue(status)

        # Should be 5 "merged" meshes, and all should now have a displayColor
        meshes = [x for x in stage.Traverse() if UsdGeom.Mesh(x) and "merged" in x.GetName()]
        self.assertEqual(len(meshes), 5)

        for mesh in meshes:
            papi = UsdGeom.PrimvarsAPI(mesh)
            primvar = papi.GetPrimvar("displayColor")
            self.assertIsNotNone(primvar.Get())

    async def test_time_varying_meshes(self):
        """Test merge spatial operation on meshes with authored time varying attributes"""
        # Get a copy of the default arguments for this command
        args = DEFAULT_ARGS.copy()
        # Open the stage
        stage = self._open_stage("time_varying_meshes.usd")
        # run command
        success, result = self._execute_command(args)

        # asserts success of execution
        self.assertTrue(success)

    async def test_coincident_boundary_shared_seam_merges_detached_stays(self):
        """Meshes sharing coincident boundary vertices merge (transitively); a
        detached mesh and a single-corner-touch mesh are left untouched."""

        stage = self._open_stage("mergeCoincidentBoundary.usda")

        merge_args = DEFAULT_ARGS.copy()
        merge_args["spatialMode"] = SPATIAL_MODE_COINCIDENT_BOUNDARY
        merge_args["boundaryTolerance"] = 1e-5

        context = _get_context(stage, report=True)

        # Quad_A, Quad_B, Quad_C, Quad_D, Quad_E
        self.assertEqual(len(_get_meshes(stage)), 5)

        self._execute_command(merge_args, context)
        self.assertIsNotNone(context.reportPath)

        # A, B, C collapse into one merged mesh; D (detached) and E (single shared vertex) remain -> 3 meshes total.
        self.assertEqual(len(_get_meshes(stage)), 3)

        # The transitive component A-B-C forms a single merged prim.
        merged = _parse_report(context.reportPath)
        self.assertEqual(len(merged.keys()), 1)
        self.assertTrue(stage.GetPrimAtPath("/merged"))
        self.assertListEqual(
            sorted(merged["/merged"]),
            ["/World/Quad_A", "/World/Quad_B", "/World/Quad_C"],
        )

        # Merged source meshes are gone; the detached and single-corner-touch meshes survive.
        for source in merged["/merged"]:
            self.assertFalse(stage.GetPrimAtPath(source).IsValid())
        self.assertTrue(stage.GetPrimAtPath("/World/Quad_D").IsValid())
        self.assertTrue(stage.GetPrimAtPath("/World/Quad_E").IsValid())

    async def test_coincident_boundary_min_shared_vertices_of_one_merges_corner_touch(self):
        """Lowering the minimum shared vertex count to 1 pulls a mesh that only
        touches at a single corner vertex into the seam component."""

        stage = self._open_stage("mergeCoincidentBoundary.usda")

        merge_args = DEFAULT_ARGS.copy()
        merge_args["spatialMode"] = SPATIAL_MODE_COINCIDENT_BOUNDARY
        merge_args["boundaryTolerance"] = 1e-5
        merge_args["boundaryMinSharedVertices"] = 1

        context = _get_context(stage, report=True)
        self.assertEqual(len(_get_meshes(stage)), 5)

        self._execute_command(merge_args, context)

        # A-B-C-E now form one component (E shares the single corner vertex with A); only D remains -> 2 meshes.
        self.assertEqual(len(_get_meshes(stage)), 2)
        merged = _parse_report(context.reportPath)
        self.assertEqual(len(merged.keys()), 1)
        self.assertListEqual(
            sorted(merged["/merged"]),
            ["/World/Quad_A", "/World/Quad_B", "/World/Quad_C", "/World/Quad_E"],
        )
        self.assertTrue(stage.GetPrimAtPath("/World/Quad_D").IsValid())

    async def test_coincident_boundary_tolerance_too_small_prevents_merge(self):
        """A non-positive coincidence tolerance finds no shared seams, so
        nothing merges."""

        stage = self._open_stage("mergeCoincidentBoundary.usda")

        merge_args = DEFAULT_ARGS.copy()
        merge_args["spatialMode"] = SPATIAL_MODE_COINCIDENT_BOUNDARY
        # Non-positive tolerance is meaningless for coincidence and must merge nothing.
        merge_args["boundaryTolerance"] = 0.0

        context = _get_context(stage, report=True)
        self.assertEqual(len(_get_meshes(stage)), 5)

        self._execute_command(merge_args, context)

        # No seams detected -> all five meshes remain, none merged.
        self.assertEqual(len(_get_meshes(stage)), 5)
        self.assertFalse(stage.GetPrimAtPath("/merged").IsValid())

    async def test_coincident_boundary_consider_materials_still_applies(self):
        """The seam constraint composes with normal bucketing: only meshes that
        share a seam are eligible, and that subset still merges by default."""

        stage = self._open_stage("mergeCoincidentBoundary.usda")

        merge_args = DEFAULT_ARGS.copy()
        merge_args["spatialMode"] = SPATIAL_MODE_COINCIDENT_BOUNDARY
        merge_args["boundaryTolerance"] = 1e-5
        merge_args["considerMaterials"] = True

        context = _get_context(stage, report=True)
        self._execute_command(merge_args, context)

        # No materials are authored, so A-B-C still merge into one prim; D and E stay -> 3 meshes.
        self.assertEqual(len(_get_meshes(stage)), 3)
        self.assertTrue(stage.GetPrimAtPath("/World/Quad_D").IsValid())
