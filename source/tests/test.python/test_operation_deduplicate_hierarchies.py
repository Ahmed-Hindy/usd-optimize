# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from pxr import Pcp, Usd

from .test_utils import Test_Operation, _get_context


class Test_Operation_Deduplicate_Hierarchies(Test_Operation):

    OPERATION = "deduplicateHierarchies"

    def assert_is_instance_ref_to(self, prim: Usd.Prim, target_path: str):
        """Assert prim has an internal reference to target_path and is instanceable."""
        self.assertTrue(prim.IsValid(), f"prim not valid: {prim.GetPath()}")
        self.assertTrue(prim.IsInstanceable(), f"prim not instanceable: {prim.GetPath()}")
        self.assertEqual(len(prim.GetAllChildren()), 0, f"prim still has children: {prim.GetPath()}")
        arcs = Usd.PrimCompositionQuery.GetDirectReferences(prim).GetCompositionArcs()
        targets = []
        for arc in arcs:
            if arc.GetArcType() == Pcp.ArcTypeReference:
                targets.append(str(arc.GetTargetPrimPath()))
        self.assertIn(
            target_path, targets, f"prim {prim.GetPath()} missing reference to {target_path}; found {targets}"
        )

    async def test_basic_dedup(self):
        """Three structurally identical sibling Xforms — first stays, other two become refs.

        A fourth structurally-equivalent prim with an *already-authored* reference must be
        excluded from the duplicate group: its existing reference is preserved
        verbatim and we do not author a new one over it.
        """
        stage = self._open_stage("dedupHierarchies_basic.usda")

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({}, context)
        self.assertTrue(ok)

        # Prototype is untouched.
        proto = stage.GetPrimAtPath("/World/Tree_Original")
        self.assertTrue(proto.IsValid())
        self.assertFalse(proto.IsInstanceable())
        self.assertGreater(len(proto.GetAllChildren()), 0)

        # The two duplicates are now instanceable refs to the prototype.
        self.assert_is_instance_ref_to(stage.GetPrimAtPath("/World/Tree_Copy1"), "/World/Tree_Original")
        self.assert_is_instance_ref_to(stage.GetPrimAtPath("/World/Tree_Copy2"), "/World/Tree_Original")

        # The already-referenced fourth tree must keep its authored ref intact.
        # We did not set instanceable on it, did not clear+rewrite its ref list,
        # and did not delete its (empty) child set.
        already = stage.GetPrimAtPath("/World/Tree_Already_Referenced")
        self.assertTrue(already.IsValid())
        self.assertTrue(already.HasAuthoredReferences())
        # The original ref target is /World/Tree_Original — confirm still pointing there.
        arcs = Usd.PrimCompositionQuery.GetDirectReferences(already).GetCompositionArcs()
        targets = [str(a.GetTargetPrimPath()) for a in arcs if a.GetArcType() == Pcp.ArcTypeReference]
        self.assertIn("/World/Tree_Original", targets)
        # And its instanceable bit was not changed by us.
        self.assertFalse(already.IsInstanceable())

        # The standalone Bush is left alone.
        bush = stage.GetPrimAtPath("/World/Bush")
        self.assertTrue(bush.IsValid())
        self.assertFalse(bush.IsInstanceable())

        # Looks scope is left alone (material-related skip).
        looks = stage.GetPrimAtPath("/World/Looks")
        self.assertTrue(looks.IsValid())

    async def test_no_duplicates_is_no_op(self):
        """A stage with structurally distinct prims must be left untouched and succeed."""
        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)
        a = stage.DefinePrim("/World/A", "Xform")
        a.SetDisplayName("Alpha")
        stage.DefinePrim("/World/A/Child1", "Mesh")
        b = stage.DefinePrim("/World/B", "Xform")
        b.SetDisplayName("Beta")
        stage.DefinePrim("/World/B/Child1", "Mesh")
        stage.DefinePrim("/World/B/Child2", "Mesh")

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({}, context)
        self.assertTrue(ok)

        for path in ("/World/A", "/World/B"):
            prim = stage.GetPrimAtPath(path)
            self.assertTrue(prim.IsValid())
            self.assertFalse(prim.IsInstanceable())
            self.assertFalse(prim.HasAuthoredReferences())

    async def test_paths_arg_restricts_subtree(self):
        """When `paths` is set, the BFS starts at children of those subtrees only."""
        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)
        # Subtree A has duplicates we DO want processed.
        stage.DefinePrim("/World/BucketA", "Xform")
        for name in ("Tree_X", "Tree_Y"):
            child = stage.DefinePrim(f"/World/BucketA/{name}", "Xform")
            child.SetDisplayName("Tree")
            stage.DefinePrim(f"/World/BucketA/{name}/Mesh", "Xform")
        # Subtree B also has duplicates but must be untouched.
        stage.DefinePrim("/World/BucketB", "Xform")
        for name in ("Tree_P", "Tree_Q"):
            child = stage.DefinePrim(f"/World/BucketB/{name}", "Xform")
            child.SetDisplayName("Tree")
            stage.DefinePrim(f"/World/BucketB/{name}/Mesh", "Xform")

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"paths": ["/World/BucketA"]}, context)
        self.assertTrue(ok)

        # BucketA's second instance should now be a ref.
        a_dup = stage.GetPrimAtPath("/World/BucketA/Tree_Y")
        self.assertTrue(a_dup.IsInstanceable())
        self.assertTrue(a_dup.HasAuthoredReferences())

        # BucketB must be untouched.
        for name in ("Tree_P", "Tree_Q"):
            prim = stage.GetPrimAtPath(f"/World/BucketB/{name}")
            self.assertFalse(prim.IsInstanceable())
            self.assertFalse(prim.HasAuthoredReferences())

    async def test_no_default_prim_no_paths_is_safe_no_op(self):
        """No default prim and no `paths` argument: emit a warning and succeed without mutating."""
        stage = Usd.Stage.CreateInMemory()
        # Create some content but never SetDefaultPrim -> stage has no default.
        a = stage.DefinePrim("/World/A", "Xform")
        a.SetDisplayName("Tree")
        b = stage.DefinePrim("/World/B", "Xform")
        b.SetDisplayName("Tree")

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({}, context)
        self.assertTrue(ok)
        # No default prim means we never started traversal -> nothing changed.
        for path in ("/World/A", "/World/B"):
            prim = stage.GetPrimAtPath(path)
            self.assertFalse(prim.IsInstanceable())
            self.assertFalse(prim.HasAuthoredReferences())

    async def test_no_default_prim_with_explicit_paths(self):
        """Explicit `paths` works even when the stage has no default prim."""
        stage = Usd.Stage.CreateInMemory()
        # Note: no SetDefaultPrim
        stage.DefinePrim("/Lab/Bucket", "Xform")
        for name in ("Tree_X", "Tree_Y"):
            child = stage.DefinePrim(f"/Lab/Bucket/{name}", "Xform")
            child.SetDisplayName("Tree")
            stage.DefinePrim(f"/Lab/Bucket/{name}/Mesh", "Xform")

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"paths": ["/Lab/Bucket"]}, context)
        self.assertTrue(ok)

        # The second instance is now a ref to the first.
        dup = stage.GetPrimAtPath("/Lab/Bucket/Tree_Y")
        self.assertTrue(dup.IsInstanceable())
        self.assertTrue(dup.HasAuthoredReferences())

    async def test_nested_duplicate_levels(self):
        """BFS recurses into children of *unmatched* prims and globally groups
        structurally-identical prims found at the deeper level — not per-parent.

        Two top-level Cabinets have different subtree shapes so neither matches
        at level 1; their children become level 2. At level 2 the four Screws
        are all (Xform > Mesh) so they form ONE group of size 4 with a single
        prototype, not two per-parent pairs.
        """
        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)
        # Give the cabinets different shapes (different child counts) so they
        # don't match at level 1 — we want the BFS to reach the screws.
        for parent_name, extra_children in (("Cabinet_A", 1), ("Cabinet_B", 2)):
            stage.DefinePrim(f"/World/{parent_name}", "Xform")
            for screw_name in ("Screw_1", "Screw_2"):
                stage.DefinePrim(f"/World/{parent_name}/{screw_name}", "Xform")
                stage.DefinePrim(f"/World/{parent_name}/{screw_name}/Mesh", "Xform")
            for i in range(extra_children):
                stage.DefinePrim(f"/World/{parent_name}/Filler_{i}", "Xform")

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({}, context)
        self.assertTrue(ok)

        # Cabinets themselves are untouched.
        for parent_name in ("Cabinet_A", "Cabinet_B"):
            cab = stage.GetPrimAtPath(f"/World/{parent_name}")
            self.assertFalse(cab.IsInstanceable())
            self.assertFalse(cab.HasAuthoredReferences())

        # Exactly one Screw is the prototype (the first encountered at level 2)
        # and the other three are instanceable refs pointing at it.
        screw_paths = [
            "/World/Cabinet_A/Screw_1",
            "/World/Cabinet_A/Screw_2",
            "/World/Cabinet_B/Screw_1",
            "/World/Cabinet_B/Screw_2",
        ]
        prototype = None
        duplicates = []
        for path in screw_paths:
            prim = stage.GetPrimAtPath(path)
            if prim.IsInstanceable():
                self.assertTrue(prim.HasAuthoredReferences(), f"{path} instanceable but no ref authored")
                duplicates.append(path)
            else:
                self.assertIsNone(
                    prototype,
                    f"more than one non-instanceable Screw "
                    f"({prototype} and {path}); group should have a single prototype",
                )
                prototype = path
        self.assertIsNotNone(prototype, "no prototype Screw found")
        self.assertEqual(
            len(duplicates), 3, f"expected 3 duplicates referencing the prototype, found {len(duplicates)}"
        )
        # All duplicates point at the same prototype.
        for dup_path in duplicates:
            arcs = Usd.PrimCompositionQuery.GetDirectReferences(stage.GetPrimAtPath(dup_path)).GetCompositionArcs()
            targets = [str(a.GetTargetPrimPath()) for a in arcs if a.GetArcType() == Pcp.ArcTypeReference]
            self.assertIn(
                prototype, targets, f"{dup_path} does not reference the prototype {prototype}; targets={targets}"
            )

    async def test_invalid_paths_arg_is_skipped(self):
        """Non-existent or non-absolute entries in `paths` are warned about and skipped;
        the rest of the operation still runs on the valid ones."""
        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)
        stage.DefinePrim("/World/Bucket", "Xform")
        for name in ("Tree_X", "Tree_Y"):
            t = stage.DefinePrim(f"/World/Bucket/{name}", "Xform")
            t.SetDisplayName("Tree")
            stage.DefinePrim(f"/World/Bucket/{name}/Mesh", "Xform")

        context = _get_context(stage, verbose=False)
        # Mix of: non-existent absolute path, relative path (invalid), and a valid one.
        ok, _ = self._execute_command(
            {"paths": ["/Nonexistent", "Bucket", "/World/Bucket"]},
            context,
        )
        self.assertTrue(ok)

        # Valid path's content was processed.
        dup = stage.GetPrimAtPath("/World/Bucket/Tree_Y")
        self.assertTrue(dup.IsInstanceable())

    async def test_structural_hash_matches_same_shape_different_displayname(self):
        """Structurally identical subtrees with different displayNames are
        deduplicated — matching is by subtree shape, not by displayName."""
        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)
        # Two structurally identical Xforms with different displayNames and
        # different prim names.
        for name, dn in (("Bracket_A", "BoltAssembly"), ("Bracket_B", "ScrewAssembly")):
            parent = stage.DefinePrim(f"/World/{name}", "Xform")
            parent.SetDisplayName(dn)
            stage.DefinePrim(f"/World/{name}/Mesh", "Xform")
            stage.DefinePrim(f"/World/{name}/Mesh/Sub", "Xform")

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({}, context)
        self.assertTrue(ok)

        # Bracket_B should now be a ref to Bracket_A.
        a = stage.GetPrimAtPath("/World/Bracket_A")
        b = stage.GetPrimAtPath("/World/Bracket_B")
        self.assertFalse(a.IsInstanceable(), "Bracket_A should remain the prototype")
        self.assertTrue(b.IsInstanceable(), "Bracket_B should be folded as a duplicate by structural hash")
        self.assertTrue(b.HasAuthoredReferences())

    async def test_structural_hash_skips_same_displayname_different_shape(self):
        """Two prims share displayName but have DIFFERENT subtree shapes:
        structural-hash matching correctly leaves them alone."""
        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        # Two siblings sharing displayName='Widget' but with different subtree
        # shapes (one has an extra child).
        a = stage.DefinePrim("/World/Widget_A", "Xform")
        a.SetDisplayName("Widget")
        stage.DefinePrim("/World/Widget_A/Mesh", "Xform")

        b = stage.DefinePrim("/World/Widget_B", "Xform")
        b.SetDisplayName("Widget")
        stage.DefinePrim("/World/Widget_B/Mesh", "Xform")
        stage.DefinePrim("/World/Widget_B/ExtraChild", "Xform")  # extra structural element

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({}, context)
        self.assertTrue(ok)

        for path in ("/World/Widget_A", "/World/Widget_B"):
            prim = stage.GetPrimAtPath(path)
            self.assertFalse(
                prim.IsInstanceable(),
                f"{path} should not be deduped: shapes differ even though displayName matches",
            )
            self.assertFalse(prim.HasAuthoredReferences())

    async def test_same_structure_different_values_not_deduped(self):
        """Two subtrees with identical structure but different attribute values
        (e.g. different mesh points) must NOT be deduplicated."""
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        # Two Xforms with the same subtree structure: each has one Mesh child.
        for name, pts in (
            ("Chair_A", [(0, 0, 0), (1, 0, 0), (0, 1, 0)]),
            ("Chair_B", [(5, 5, 5), (6, 5, 5), (5, 6, 5)]),
        ):
            stage.DefinePrim(f"/World/{name}", "Xform")
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({}, context)
        self.assertTrue(ok)

        # Neither prim should be deduplicated — values differ.
        for path in ("/World/Chair_A", "/World/Chair_B"):
            prim = stage.GetPrimAtPath(path)
            self.assertFalse(prim.IsInstanceable(), f"{path} should NOT be deduped: mesh data differs")
            self.assertFalse(prim.HasAuthoredReferences())

    async def test_same_structure_same_values_are_deduped(self):
        """Two subtrees with identical structure AND identical property values
        must be deduplicated (confirms value comparison passes for true dupes)."""
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        for name in ("Chair_A", "Chair_B"):
            stage.DefinePrim(f"/World/{name}", "Xform")
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({}, context)
        self.assertTrue(ok)

        # Chair_B should now reference Chair_A.
        a = stage.GetPrimAtPath("/World/Chair_A")
        b = stage.GetPrimAtPath("/World/Chair_B")
        self.assertFalse(a.IsInstanceable())
        self.assertTrue(b.IsInstanceable(), "Chair_B should be deduped — values are identical")
        self.assertTrue(b.HasAuthoredReferences())

    async def test_different_xform_same_mesh_still_deduped(self):
        """Prims with different xformOp values but identical mesh data must still
        be deduplicated — transform differences are expected for instances."""
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        for name, translate in (("Inst_A", (0, 0, 0)), ("Inst_B", (10, 0, 0))):
            parent = stage.DefinePrim(f"/World/{name}", "Xform")
            xformable = UsdGeom.Xformable(parent)
            xformable.AddTranslateOp().Set(Gf.Vec3d(*translate))
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({}, context)
        self.assertTrue(ok)

        a = stage.GetPrimAtPath("/World/Inst_A")
        b = stage.GetPrimAtPath("/World/Inst_B")
        self.assertFalse(a.IsInstanceable())
        self.assertTrue(b.IsInstanceable(), "Inst_B should be deduped — only xform differs")
        self.assertTrue(b.HasAuthoredReferences())

    async def test_tolerance_allows_small_vertex_drift(self):
        """With tolerance > 0, subtrees whose float values differ within tolerance
        are still deduplicated."""
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        # Two meshes: identical topology, points differ by 0.0005 per component.
        pts_a = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        pts_b = [(0.0005, 0.0005, 0.0005), (1.0005, 0.0005, 0.0005), (0.0005, 1.0005, 0.0005)]
        for name, pts in (("A", pts_a), ("B", pts_b)):
            stage.DefinePrim(f"/World/{name}", "Xform")
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        # Without tolerance (default=0): should NOT dedup.
        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.0}, context)
        self.assertTrue(ok)
        self.assertFalse(stage.GetPrimAtPath("/World/B").IsInstanceable())

        # Re-open a fresh stage (previous run may have mutated nothing, but be safe).
        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)
        for name, pts in (("A", pts_a), ("B", pts_b)):
            stage.DefinePrim(f"/World/{name}", "Xform")
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        # With tolerance=0.001: should dedup (drift is 0.0005 < 0.001).
        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.001}, context)
        self.assertTrue(ok)
        self.assertTrue(
            stage.GetPrimAtPath("/World/B").IsInstanceable(),
            "B should be deduped: vertex drift is within tolerance",
        )

    async def test_tolerance_does_not_affect_topology(self):
        """Tolerance only applies to float values. Different topology indices
        (integer arrays) must still prevent deduplication even with high tolerance."""
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)]
        for name, indices in (("A", [0, 1, 2]), ("B", [0, 1, 3])):
            stage.DefinePrim(f"/World/{name}", "Xform")
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray(indices))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 100.0}, context)
        self.assertTrue(ok)
        self.assertFalse(
            stage.GetPrimAtPath("/World/B").IsInstanceable(),
            "B should NOT be deduped: topology differs (integer array, not affected by tolerance)",
        )

    async def test_multi_mesh_hierarchy_tolerance_accepts_small_drift(self):
        """A hierarchy with multiple meshes where each mesh has small vertex
        drift (within tolerance) across the two copies should be deduplicated."""
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        base_pts_body = [(0, 0, 0), (2, 0, 0), (1, 2, 0), (0, 0, 1), (2, 0, 1), (1, 2, 1)]
        base_pts_wheel = [(0, 0, 0), (0.5, 0, 0), (0, 0.5, 0)]
        drift = 0.0003

        for idx, name in enumerate(("Car_A", "Car_B")):
            stage.DefinePrim(f"/World/{name}", "Xform")
            body = UsdGeom.Mesh.Define(stage, f"/World/{name}/Body")
            body_pts = [Gf.Vec3f(p[0] + drift * idx, p[1] + drift * idx, p[2] + drift * idx) for p in base_pts_body]
            body.GetPointsAttr().Set(Vt.Vec3fArray(body_pts))
            body.GetFaceVertexCountsAttr().Set(Vt.IntArray([3, 3, 3, 3]))
            body.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2, 3, 4, 5, 0, 3, 5, 1, 4, 2]))

            wheel = UsdGeom.Mesh.Define(stage, f"/World/{name}/Wheel")
            wheel_pts = [Gf.Vec3f(p[0] + drift * idx, p[1] + drift * idx, p[2] + drift * idx) for p in base_pts_wheel]
            wheel.GetPointsAttr().Set(Vt.Vec3fArray(wheel_pts))
            wheel.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            wheel.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.001}, context)
        self.assertTrue(ok)
        self.assertTrue(
            stage.GetPrimAtPath("/World/Car_B").IsInstanceable(),
            "Car_B should be deduped: all mesh drift (0.0003) is within tolerance (0.001)",
        )

    async def test_multi_mesh_hierarchy_tolerance_rejects_large_drift(self):
        """When one mesh in a hierarchy drifts beyond tolerance the whole
        hierarchy must NOT be deduplicated, even if other meshes are fine."""
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        base_pts_body = [(0, 0, 0), (2, 0, 0), (1, 2, 0)]
        base_pts_wheel = [(0, 0, 0), (0.5, 0, 0), (0, 0.5, 0)]

        for idx, name in enumerate(("Car_A", "Car_B")):
            stage.DefinePrim(f"/World/{name}", "Xform")

            body = UsdGeom.Mesh.Define(stage, f"/World/{name}/Body")
            body_pts = [Gf.Vec3f(*p) for p in base_pts_body]
            body.GetPointsAttr().Set(Vt.Vec3fArray(body_pts))
            body.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            body.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

            wheel = UsdGeom.Mesh.Define(stage, f"/World/{name}/Wheel")
            large_drift = 0.01 * idx
            wheel_pts = [Gf.Vec3f(p[0] + large_drift, p[1] + large_drift, p[2] + large_drift) for p in base_pts_wheel]
            wheel.GetPointsAttr().Set(Vt.Vec3fArray(wheel_pts))
            wheel.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            wheel.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.001}, context)
        self.assertTrue(ok)
        self.assertFalse(
            stage.GetPrimAtPath("/World/Car_B").IsInstanceable(),
            "Car_B should NOT be deduped: Wheel drift (0.01) exceeds tolerance (0.001)",
        )

    async def test_descendant_transform_differs_blocks_dedup(self):
        """Two hierarchies that are identical except for a child-level transform
        that differs by MORE than tolerance must NOT be deduplicated — only root
        xformOps are ignored, and a descendant placement difference beyond
        tolerance is a genuine geometric difference."""
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        # Child translate differs by 5 units, far beyond the default tolerance.
        for name, child_translate in (("A", (0, 0, 0)), ("B", (0, 5, 0))):
            stage.DefinePrim(f"/World/{name}", "Xform")
            child = stage.DefinePrim(f"/World/{name}/Part", "Xform")
            xformable = UsdGeom.Xformable(child)
            xformable.AddTranslateOp().Set(Gf.Vec3d(*child_translate))
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Part/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.001}, context)
        self.assertTrue(ok)
        self.assertFalse(
            stage.GetPrimAtPath("/World/B").IsInstanceable(),
            "B should NOT be deduped: descendant Part transform differs by 5 (>> tolerance)",
        )

    async def test_descendant_matrix_transform_drift_within_tolerance_deduped(self):
        """OMPE-96133 (Defect 2 / Bug B): a descendant `xformOp:transform`
        (GfMatrix4d) that differs only by sub-tolerance floating-point drift —
        the kind CAD re-exports introduce — must NOT block deduplication.

        Previously matrix-typed values fell through to an exact-match path
        (tolerance applied only to float/vec arrays and float/double scalars),
        so ~1e-5 drift on a descendant transform split otherwise-identical
        subtrees into singletons and nothing merged.
        """
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        # Two identical subtrees; the descendant Part carries a matrix transform
        # that differs by 1.1e-5 in the translation row — well within tolerance.
        base = Gf.Matrix4d(1.0)
        base.SetTranslateOnly(Gf.Vec3d(0.2270095404519, -0.7948490813588, 0.01125))
        drifted = Gf.Matrix4d(1.0)
        drifted.SetTranslateOnly(Gf.Vec3d(0.2270037334486, -0.7948502101259, 0.01124999992818))
        for name, mtx in (("A", base), ("B", drifted)):
            stage.DefinePrim(f"/World/{name}", "Xform")
            child = stage.DefinePrim(f"/World/{name}/Part", "Xform")
            UsdGeom.Xformable(child).AddTransformOp().Set(mtx)
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Part/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.001}, context)
        self.assertTrue(ok)
        self.assertTrue(
            stage.GetPrimAtPath("/World/B").IsInstanceable(),
            "B should be deduped: descendant matrix transform drift (1.1e-5) is within tolerance",
        )

        # And with tolerance=0 (bitwise-exact) the same drift must block.
        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)
        for name, mtx in (("A", base), ("B", drifted)):
            stage.DefinePrim(f"/World/{name}", "Xform")
            child = stage.DefinePrim(f"/World/{name}/Part", "Xform")
            UsdGeom.Xformable(child).AddTransformOp().Set(mtx)
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Part/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))
        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.0}, context)
        self.assertTrue(ok)
        self.assertFalse(
            stage.GetPrimAtPath("/World/B").IsInstanceable(),
            "B should NOT be deduped at tolerance=0: matrix drift requires bitwise-exact match",
        )

    async def test_declared_valueless_attr_does_not_block_dedup(self):
        """OMPE-96133 (Defect 2 / Bug A): an attribute that is authored
        (declared, so it appears in the structural hash) but carries no authored
        value on either copy — e.g. an indexed primvar's `:indices` declared
        without data — must NOT block deduplication.

        Previously the value comparison demanded an authored value on the other
        side unconditionally, so a declared-but-value-less attribute present on
        every copy made identical subtrees compare unequal -> 0 merges.
        """
        from pxr import Gf, Sdf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        for name in ("Chair_A", "Chair_B"):
            stage.DefinePrim(f"/World/{name}", "Xform")
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))
            # Declare an indexed-primvar indices attribute WITHOUT setting a
            # value on either copy: it is in the authored property names (so it
            # is part of the structural hash and matches across copies) but
            # HasAuthoredValue() is False.
            attr = mesh.GetPrim().CreateAttribute("primvars:normals:indices", Sdf.ValueTypeNames.IntArray)
            self.assertFalse(attr.HasAuthoredValue())
            self.assertIn("primvars:normals:indices", [n for n in mesh.GetPrim().GetAuthoredPropertyNames()])

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({}, context)
        self.assertTrue(ok)

        a = stage.GetPrimAtPath("/World/Chair_A")
        b = stage.GetPrimAtPath("/World/Chair_B")
        self.assertFalse(a.IsInstanceable())
        self.assertTrue(
            b.IsInstanceable(),
            "Chair_B should be deduped: a declared-but-value-less attribute on both copies is not a difference",
        )
        self.assertTrue(b.HasAuthoredReferences())

    async def test_root_xform_differs_descendant_xform_matches_deduped(self):
        """Root prims have different placement transforms, but descendants
        have identical local transforms — should still deduplicate."""
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        child_offset = (0, 2, 0)
        for name, root_translate in (("A", (0, 0, 0)), ("B", (50, 0, 0))):
            parent = stage.DefinePrim(f"/World/{name}", "Xform")
            UsdGeom.Xformable(parent).AddTranslateOp().Set(Gf.Vec3d(*root_translate))
            child = stage.DefinePrim(f"/World/{name}/Part", "Xform")
            UsdGeom.Xformable(child).AddTranslateOp().Set(Gf.Vec3d(*child_offset))
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Part/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({}, context)
        self.assertTrue(ok)
        self.assertTrue(
            stage.GetPrimAtPath("/World/B").IsInstanceable(),
            "B should be deduped: root xforms differ (ignored) but descendant xforms match",
        )

    async def test_deep_hierarchy_mixed_drift_within_tolerance(self):
        """A three-level hierarchy (root > group > mesh) where meshes at
        different depths each have small independent drift. All drift is
        within tolerance, so dedup should succeed."""
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        base_pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)]
        topo_counts = Vt.IntArray([3, 3])
        topo_indices = Vt.IntArray([0, 1, 2, 1, 3, 2])

        for idx, name in enumerate(("Tree_A", "Tree_B")):
            stage.DefinePrim(f"/World/{name}", "Xform")
            for gi, grp in enumerate(("Trunk", "Canopy")):
                stage.DefinePrim(f"/World/{name}/{grp}", "Xform")
                for mi, mname in enumerate(("Mesh0", "Mesh1")):
                    mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/{grp}/{mname}")
                    d = 0.0002 * idx * (gi + 1) * (mi + 1)
                    pts = Vt.Vec3fArray([Gf.Vec3f(p[0] + d, p[1] + d, p[2] + d) for p in base_pts])
                    mesh.GetPointsAttr().Set(pts)
                    mesh.GetFaceVertexCountsAttr().Set(topo_counts)
                    mesh.GetFaceVertexIndicesAttr().Set(topo_indices)

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.001}, context)
        self.assertTrue(ok)
        self.assertTrue(
            stage.GetPrimAtPath("/World/Tree_B").IsInstanceable(),
            "Tree_B should be deduped: max drift (0.0008) is within tolerance (0.001)",
        )

    async def test_deep_hierarchy_one_mesh_exceeds_tolerance(self):
        """Same as above, but one leaf mesh has drift exceeding tolerance.
        The entire hierarchy must be rejected."""
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        base_pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)]
        topo_counts = Vt.IntArray([3, 3])
        topo_indices = Vt.IntArray([0, 1, 2, 1, 3, 2])

        for idx, name in enumerate(("Tree_A", "Tree_B")):
            stage.DefinePrim(f"/World/{name}", "Xform")
            for gi, grp in enumerate(("Trunk", "Canopy")):
                stage.DefinePrim(f"/World/{name}/{grp}", "Xform")
                for mi, mname in enumerate(("Mesh0", "Mesh1")):
                    mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/{grp}/{mname}")
                    d = 0.0002 * idx * (gi + 1) * (mi + 1)
                    if name == "Tree_B" and grp == "Canopy" and mname == "Mesh1":
                        d = 0.05
                    pts = Vt.Vec3fArray([Gf.Vec3f(p[0] + d, p[1] + d, p[2] + d) for p in base_pts])
                    mesh.GetPointsAttr().Set(pts)
                    mesh.GetFaceVertexCountsAttr().Set(topo_counts)
                    mesh.GetFaceVertexIndicesAttr().Set(topo_indices)

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.001}, context)
        self.assertTrue(ok)
        self.assertFalse(
            stage.GetPrimAtPath("/World/Tree_B").IsInstanceable(),
            "Tree_B should NOT be deduped: Canopy/Mesh1 drift (0.05) exceeds tolerance (0.001)",
        )

    async def test_value_variant_group_outlier_sorts_first(self):
        """Defect 1 regression: a structural group with two value-variants
        (a majority of identical copies plus a single outlier) must merge the
        majority regardless of arrival order.

        Previously value refinement compared every member to the *first*
        group member; when the outlier sorted first, all the mutually-identical
        copies were compared to the wrong reference, dropped, and never
        re-grouped — yielding 0 merges. The fix partitions the group into
        value-equivalence classes, so the majority forms its own prototype.
        """
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        majority_pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        outlier_pts = [(0, 0, 0), (1, 0, 0), (0, 9, 0)]  # value-distinct, same topology/shape

        # Name the outlier so it sorts FIRST among siblings ("AA_" prefix),
        # exercising the order-dependence that triggered the original bug.
        members = [("AA_Outlier", outlier_pts)] + [(f"Copy_{i:02d}", majority_pts) for i in range(4)]
        for name, pts in members:
            stage.DefinePrim(f"/World/{name}", "Xform")
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.0}, context)
        self.assertTrue(ok)

        # The outlier must stay distinct (its own un-merged prim).
        outlier = stage.GetPrimAtPath("/World/AA_Outlier")
        self.assertFalse(outlier.IsInstanceable(), "outlier must not merge into the majority variant")
        self.assertFalse(outlier.HasAuthoredReferences())

        # Exactly one of the four majority copies is the prototype; the other
        # three are instanceable references to it.
        copy_paths = [f"/World/Copy_{i:02d}" for i in range(4)]
        prototype = None
        duplicates = []
        for path in copy_paths:
            prim = stage.GetPrimAtPath(path)
            if prim.IsInstanceable():
                self.assertTrue(prim.HasAuthoredReferences(), f"{path} instanceable but no ref authored")
                duplicates.append(path)
            else:
                self.assertIsNone(prototype, f"more than one prototype: {prototype} and {path}")
                prototype = path
        self.assertIsNotNone(prototype, "majority variant produced no prototype — Defect 1 regression")
        self.assertEqual(len(duplicates), 3, f"expected 3 majority duplicates, found {len(duplicates)}")
        for dup_path in duplicates:
            arcs = Usd.PrimCompositionQuery.GetDirectReferences(stage.GetPrimAtPath(dup_path)).GetCompositionArcs()
            targets = [str(a.GetTargetPrimPath()) for a in arcs if a.GetArcType() == Pcp.ArcTypeReference]
            self.assertIn(prototype, targets, f"{dup_path} does not reference prototype {prototype}; targets={targets}")

    async def test_value_variant_group_two_mergeable_variants(self):
        """A structural group with two distinct value-variants, each with
        multiple members, must yield one prototype per variant — not a single
        first-member comparison that drops the rest."""
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        variant_a = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        variant_b = [(0, 0, 0), (1, 0, 0), (0, 5, 0)]
        # Interleave so neither variant is wholly contiguous; sort order mixes them.
        members = [
            ("A0", variant_a),
            ("B0", variant_b),
            ("A1", variant_a),
            ("B1", variant_b),
            ("A2", variant_a),
        ]
        for name, pts in members:
            stage.DefinePrim(f"/World/{name}", "Xform")
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.0}, context)
        self.assertTrue(ok)

        def ref_target(path):
            prim = stage.GetPrimAtPath(path)
            if not prim.IsInstanceable():
                return None
            arcs = Usd.PrimCompositionQuery.GetDirectReferences(prim).GetCompositionArcs()
            targets = [str(a.GetTargetPrimPath()) for a in arcs if a.GetArcType() == Pcp.ArcTypeReference]
            return targets[0] if targets else None

        # Variant A: 3 members -> 1 prototype + 2 dups, all pointing at the same A prototype.
        a_targets = {p: ref_target(f"/World/{p}") for p in ("A0", "A1", "A2")}
        a_prototypes = [p for p, t in a_targets.items() if t is None]
        self.assertEqual(len(a_prototypes), 1, f"variant A should have exactly one prototype; got {a_prototypes}")
        a_proto_path = f"/World/{a_prototypes[0]}"
        for p in ("A0", "A1", "A2"):
            if a_targets[p] is not None:
                self.assertEqual(a_targets[p], a_proto_path)

        # Variant B: 2 members -> 1 prototype + 1 dup.
        b_targets = {p: ref_target(f"/World/{p}") for p in ("B0", "B1")}
        b_prototypes = [p for p, t in b_targets.items() if t is None]
        self.assertEqual(len(b_prototypes), 1, f"variant B should have exactly one prototype; got {b_prototypes}")
        b_proto_path = f"/World/{b_prototypes[0]}"
        for p in ("B0", "B1"):
            if b_targets[p] is not None:
                self.assertEqual(b_targets[p], b_proto_path)

        # The two variants must NOT cross-reference each other.
        self.assertNotEqual(a_proto_path, b_proto_path)

    async def test_nested_duplicates_survive_unmerged_parent_group(self):
        """Defect 2 regression: parents that group structurally but do NOT
        merge (their values differ) must not prune their children — nested
        duplicate subtrees inside them must still be discovered and merged.

        Two trays share the same subtree shape (so they group structurally at
        level 1) but differ in a tray-level attribute value, so neither tray
        merges. Each tray contains two structurally- and value-identical
        modules. Previously the trays were marked 'matched' on the bare
        structural hash and pruned, so the BFS never descended into them and
        the four identical modules were left un-merged.
        """
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        module_pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]

        # Two trays, same shape, but a value-distinct tray-level marker mesh so
        # the trays themselves do not merge.
        for tray_idx, tray_name in enumerate(("Tray_A", "Tray_B")):
            stage.DefinePrim(f"/World/{tray_name}", "Xform")
            marker = UsdGeom.Mesh.Define(stage, f"/World/{tray_name}/Marker")
            # Value-distinct per tray -> trays are NOT value-equivalent.
            marker.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(float(tray_idx), 0, 0)]))
            marker.GetFaceVertexCountsAttr().Set(Vt.IntArray([1]))
            marker.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0]))

            for mod_name in ("Module_1", "Module_2"):
                stage.DefinePrim(f"/World/{tray_name}/{mod_name}", "Xform")
                mesh = UsdGeom.Mesh.Define(stage, f"/World/{tray_name}/{mod_name}/Mesh")
                mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in module_pts]))
                mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
                mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.0}, context)
        self.assertTrue(ok)

        # The trays themselves must NOT merge (their Marker values differ).
        for tray_name in ("Tray_A", "Tray_B"):
            tray = stage.GetPrimAtPath(f"/World/{tray_name}")
            self.assertFalse(tray.IsInstanceable(), f"{tray_name} should not merge — tray values differ")
            self.assertFalse(tray.HasAuthoredReferences())

        # All four modules are structurally + value identical and must form a
        # single group: exactly one prototype, three instanceable refs to it.
        module_paths = [
            "/World/Tray_A/Module_1",
            "/World/Tray_A/Module_2",
            "/World/Tray_B/Module_1",
            "/World/Tray_B/Module_2",
        ]
        prototype = None
        duplicates = []
        for path in module_paths:
            prim = stage.GetPrimAtPath(path)
            if prim.IsInstanceable():
                self.assertTrue(prim.HasAuthoredReferences(), f"{path} instanceable but no ref authored")
                duplicates.append(path)
            else:
                self.assertIsNone(prototype, f"more than one module prototype: {prototype} and {path}")
                prototype = path
        self.assertIsNotNone(prototype, "nested modules were never merged — Defect 2 regression (pruned parent)")
        self.assertEqual(len(duplicates), 3, f"expected 3 nested-module duplicates, found {len(duplicates)}")
        for dup_path in duplicates:
            arcs = Usd.PrimCompositionQuery.GetDirectReferences(stage.GetPrimAtPath(dup_path)).GetCompositionArcs()
            targets = [str(a.GetTargetPrimPath()) for a in arcs if a.GetArcType() == Pcp.ArcTypeReference]
            self.assertIn(prototype, targets, f"{dup_path} does not reference prototype {prototype}; targets={targets}")

    async def test_analysis_mode_returns_duplicates_without_mutating(self):
        """Analysis mode finds duplicates and returns JSON but does NOT author
        references or set instanceable on any prim."""
        stage = self._open_stage("dedupHierarchies_basic.usda")

        context = _get_context(stage, verbose=False)
        context.analysisMode = 1
        ok, result = self._execute_command({}, context)
        self.assertTrue(ok)

        # Stage must be untouched.
        for path in ("/World/Tree_Copy1", "/World/Tree_Copy2"):
            prim = stage.GetPrimAtPath(path)
            self.assertFalse(prim.IsInstanceable(), f"{path} mutated in analysis mode")
            self.assertFalse(prim.HasAuthoredReferences())

        # result[2] is the parsed output dict.
        self.assertIn("analysis", result[2])
        analysis = result[2]["analysis"]
        self.assertIn("/World/Tree_Original", analysis)
        self.assertEqual(sorted(analysis["/World/Tree_Original"]), ["/World/Tree_Copy1", "/World/Tree_Copy2"])

    async def test_nested_instances_within_merged_prototype(self):
        """Nested-instance support: when two assemblies merge at level 1, the
        BFS descends into the surviving prototype and consolidates the
        duplicate children *inside* it into nested instanceable references.
        Every instance of the prototype inherits that nested structure through
        its reference, so shared inner content is deduplicated once.

        Before nested-instance support the prototype was pruned alongside its
        duplicates, so the op stopped one level deep per branch and the inner
        bolts were never consolidated.
        """
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        bolt_pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        # Two structurally + value identical assemblies, each holding two
        # identical bolts.
        for asm in ("Assembly_A", "Assembly_B"):
            stage.DefinePrim(f"/World/{asm}", "Xform")
            for bolt in ("Bolt_1", "Bolt_2"):
                stage.DefinePrim(f"/World/{asm}/{bolt}", "Xform")
                mesh = UsdGeom.Mesh.Define(stage, f"/World/{asm}/{bolt}/Mesh")
                mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in bolt_pts]))
                mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
                mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.0}, context)
        self.assertTrue(ok)

        # One assembly is the prototype (untouched, keeps its children); the
        # other is an instanceable reference to it.
        asm_a = stage.GetPrimAtPath("/World/Assembly_A")
        asm_b = stage.GetPrimAtPath("/World/Assembly_B")
        asm_protos = [p for p in (asm_a, asm_b) if not p.IsInstanceable()]
        asm_dups = [p for p in (asm_a, asm_b) if p.IsInstanceable()]
        self.assertEqual(len(asm_protos), 1, "expected exactly one assembly prototype")
        self.assertEqual(len(asm_dups), 1, "expected exactly one assembly duplicate")
        asm_proto = asm_protos[0]
        self.assert_is_instance_ref_to(asm_dups[0], str(asm_proto.GetPath()))

        # Inside the prototype, the two bolts are now nested instances: one is
        # the bolt prototype, the other an instanceable reference to it.
        bolt_1 = stage.GetPrimAtPath(f"{asm_proto.GetPath()}/Bolt_1")
        bolt_2 = stage.GetPrimAtPath(f"{asm_proto.GetPath()}/Bolt_2")
        bolt_protos = [b for b in (bolt_1, bolt_2) if not b.IsInstanceable()]
        bolt_dups = [b for b in (bolt_1, bolt_2) if b.IsInstanceable()]
        self.assertEqual(len(bolt_protos), 1, "expected one bolt prototype inside the merged assembly prototype")
        self.assertEqual(
            len(bolt_dups),
            1,
            "nested duplicate bolt inside the prototype was not consolidated — prototype descent missing",
        )
        self.assertGreater(len(bolt_protos[0].GetAllChildren()), 0, "bolt prototype lost its Mesh child")
        self.assert_is_instance_ref_to(bolt_dups[0], str(bolt_protos[0].GetPath()))

    async def test_scale_many_value_variants(self):
        """Scale guard for the value partitioning (review concern: a large,
        mostly value-distinct structural group is the worst case for
        `_partitionByValues`, which compares each member against every prior
        class representative). With many distinct variants plus one mergeable
        cluster, the op must still terminate and produce exactly the right
        merges.
        """
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        def _define_part(path, x):
            stage.DefinePrim(path, "Xform")
            mesh = UsdGeom.Mesh.Define(stage, f"{path}/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(float(x), 0, 0), Gf.Vec3f(1, 0, 0), Gf.Vec3f(0, 1, 0)]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        # 150 structurally identical but value-distinct parts -> 150 singleton
        # classes (the quadratic worst case for partitioning).
        n_distinct = 150
        for i in range(n_distinct):
            _define_part(f"/World/Distinct_{i:04d}", i + 1)
        # Plus one cluster of 50 identical copies (shared x=0) -> one prototype
        # + 49 duplicates.
        n_copies = 50
        for j in range(n_copies):
            _define_part(f"/World/Copy_{j:04d}", 0)

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.0}, context)
        self.assertTrue(ok)

        # None of the distinct parts merged.
        for i in range(n_distinct):
            self.assertFalse(
                stage.GetPrimAtPath(f"/World/Distinct_{i:04d}").IsInstanceable(),
                f"Distinct_{i:04d} should not merge — its value is unique",
            )

        # The cluster: exactly one prototype + (n_copies - 1) instanceable refs.
        copy_prototypes = []
        copy_dups = []
        for j in range(n_copies):
            prim = stage.GetPrimAtPath(f"/World/Copy_{j:04d}")
            (copy_dups if prim.IsInstanceable() else copy_prototypes).append(prim)
        self.assertEqual(len(copy_prototypes), 1, f"cluster should have one prototype; got {len(copy_prototypes)}")
        self.assertEqual(len(copy_dups), n_copies - 1, "all but one cluster copy should be instanceable refs")

    async def test_ref_bearing_parent_children_are_deduped(self):
        """Review concern #3 lock: a prim that carries an authored reference is
        itself excluded from merging, but the BFS still descends into its
        children, so nested duplicates beneath it are consolidated into
        internal references. The ref-bearing prim itself is left untouched.
        """
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        # A library prim the container will reference.
        stage.DefinePrim("/World/Lib", "Scope")

        # Container carries an authored internal reference (so it is excluded
        # from the duplicate set) and locally defines two identical widgets.
        container = stage.DefinePrim("/World/Container", "Xform")
        container.GetReferences().AddInternalReference("/World/Lib")
        pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
        for w in ("Widget_1", "Widget_2"):
            stage.DefinePrim(f"/World/Container/{w}", "Xform")
            mesh = UsdGeom.Mesh.Define(stage, f"/World/Container/{w}/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.0}, context)
        self.assertTrue(ok)

        # The ref-bearing container is untouched: not instanceable, ref intact.
        container = stage.GetPrimAtPath("/World/Container")
        self.assertTrue(container.HasAuthoredReferences(), "container's authored reference must be preserved")
        self.assertFalse(container.IsInstanceable(), "ref-bearing container must not be folded as a duplicate")

        # Its two local widget children were deduped: one prototype + one
        # instanceable reference to it.
        w1 = stage.GetPrimAtPath("/World/Container/Widget_1")
        w2 = stage.GetPrimAtPath("/World/Container/Widget_2")
        widget_protos = [w for w in (w1, w2) if not w.IsInstanceable()]
        widget_dups = [w for w in (w1, w2) if w.IsInstanceable()]
        self.assertEqual(len(widget_protos), 1, "expected one widget prototype under the ref-bearing container")
        self.assertEqual(len(widget_dups), 1, "nested duplicate under the ref-bearing parent was not consolidated")
        self.assert_is_instance_ref_to(widget_dups[0], str(widget_protos[0].GetPath()))

    async def test_fingerprint_bucket_refines_within_tolerance(self):
        """The value-fingerprint pre-bucket groups candidates by tolerance-
        independent content (here: identical topology), but the pairwise
        compare must still refine within a bucket. Members that share a bucket
        yet differ beyond tolerance stay distinct; members within tolerance of
        the representative merge.

        This guards the bucketing's correctness in the `tolerance > 0` path,
        which the (tolerance=0) scale test does not exercise.
        """
        from pxr import Gf, UsdGeom, Vt

        stage = Usd.Stage.CreateInMemory()
        world = stage.DefinePrim("/World", "Xform")
        stage.SetDefaultPrim(world)

        # All four share topology (counts/indices), so they land in ONE
        # fingerprint bucket at tolerance>0 (float point values are excluded
        # from the fingerprint, only their array length is). The pairwise pass
        # must then split them by actual value distance.
        variants = {
            "A0": [(0, 0, 0), (1, 0, 0), (0, 1, 0)],  # representative
            "A1": [(0, 0, 0), (1, 0, 0), (0, 1, 0)],  # exact match -> merges
            "B0": [(0, 0, 0), (1, 0, 0), (0, 9, 0)],  # far beyond tolerance
            "A2": [(0.0002, 0, 0), (1, 0, 0), (0, 1, 0)],  # within tolerance
        }
        for name, pts in variants.items():
            stage.DefinePrim(f"/World/{name}", "Xform")
            mesh = UsdGeom.Mesh.Define(stage, f"/World/{name}/Mesh")
            mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
            mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
            mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))

        context = _get_context(stage, verbose=False)
        ok, _ = self._execute_command({"tolerance": 0.001}, context)
        self.assertTrue(ok)

        # A0/A1/A2 are within tolerance of A0 -> one class (A0 prototype).
        self.assertFalse(stage.GetPrimAtPath("/World/A0").IsInstanceable())
        for dup in ("A1", "A2"):
            self.assertTrue(
                stage.GetPrimAtPath(f"/World/{dup}").IsInstanceable(),
                f"{dup} should merge into A0 (within tolerance, same bucket)",
            )
        # B0 shares the bucket but is beyond tolerance -> must stay distinct.
        self.assertFalse(
            stage.GetPrimAtPath("/World/B0").IsInstanceable(),
            "B0 must stay distinct: points differ beyond tolerance despite sharing the fingerprint bucket",
        )

    async def test_max_depth_caps_traversal(self):
        """`maxDepth` caps how many breadth-first levels are descended. Nested
        duplicates below the cap are not consolidated; the default (0) is
        unbounded."""
        from pxr import Gf, UsdGeom, Vt

        def _build():
            stage = Usd.Stage.CreateInMemory()
            world = stage.DefinePrim("/World", "Xform")
            stage.SetDefaultPrim(world)
            # A single parent at level 1 (no sibling -> never merges itself), so
            # the only possible merge is its two identical children at level 2.
            stage.DefinePrim("/World/Parent", "Xform")
            pts = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
            for name in ("Mod_A", "Mod_B"):
                stage.DefinePrim(f"/World/Parent/{name}", "Xform")
                mesh = UsdGeom.Mesh.Define(stage, f"/World/Parent/{name}/Mesh")
                mesh.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*p) for p in pts]))
                mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray([3]))
                mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray([0, 1, 2]))
            return stage

        # maxDepth=1: BFS processes only level 1 (Parent); the level-2 modules
        # are never reached, so they do not merge.
        stage = _build()
        ok, _ = self._execute_command({"maxDepth": 1}, _get_context(stage, verbose=False))
        self.assertTrue(ok)
        self.assertFalse(
            stage.GetPrimAtPath("/World/Parent/Mod_B").IsInstanceable(),
            "Mod_B should NOT merge: level 2 is beyond maxDepth=1",
        )

        # Default (maxDepth=0, unbounded): the modules merge at level 2.
        stage = _build()
        ok, _ = self._execute_command({}, _get_context(stage, verbose=False))
        self.assertTrue(ok)
        self.assertTrue(
            stage.GetPrimAtPath("/World/Parent/Mod_B").IsInstanceable(),
            "Mod_B should merge at level 2 when depth is unbounded",
        )
