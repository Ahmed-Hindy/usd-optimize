# Changelog

## [1.0.4] - 2026-06-12
### Added
- Asset Validator parameters API: expose validator rule tuning so checker thresholds (e.g. `OccludedMeshesChecker`, `SmallMeshChecker`) can be configured via parameters.
- `MergeMeshes`: new spatial merge mode that welds coincident boundary vertices across seams.
- `DeduplicateGeometry`: new "Point Instancer" mode.
- `PrunePayloads`: option to avoid pruning unloaded payloads.
- `DeduplicateHierarchies`: support for nested instancing.

### Changed
- Renamed Scene Optimizer to Usd Optimize.
- Validators now register against capability requirements (e.g. `GeometryRequirements`, `HierarchyRequirements`, `MaterialsRequirements`) via the new plugin entry point instead of rule categories.
- Migrated the asset validator dependency to `usd-validation-nvidia`.
- Reduced default logging noise across operations.
- Improved performance of `PruneLeaves`.
- Reverted `repo_usd` pin to 5.0.26 (restores the stock build; the 5.0.34 exchange build trimmed link deps).
- Pin Visual Studio to 2019.
- Auto-generated documentation for Usd Optimize lib.
- Replaced unsafe sudo/rm guidance in validators skill.

### Fixed
- `DeduplicateHierarchies`: fix value variant grouping.
- `DiceMeshes`: fix irregular multi-axis cuts.
- Fix gcc13 build issues from stricter compiler checks (DGX Spark defaults to gcc13).

## [1.0.3] - 2026-05-28
### Fixed
- `FitPrimitive`: no longer incorrectly fits a cube primitive to hollow meshes (e.g. an extruded box). Such meshes are now left unchanged instead of being replaced by a solid cube.
- Remove primvar indices when removing primvars.

### Added
- Accept JSON int literals for `float`/`double` attributes.

### Changed
- Bumped `repo_usd` to 5.0.34.
- Use symlinks for Python files where possible during builds rather than copying them.

## [1.0.2] - 2026-05-27
### Fixed
- Removed `repo_kit_tools` from public facing dependencies

## [1.0.1] - 2026-05-26
### Fixed
- `DeduplicateGeometry`: preserve `MaterialBindingAPI` schemas on instance xforms so material bindings survive deduplication.
- `DeduplicateGeometry`: correct transform/pivot handling, including flipped duplicates.
- `CMakeLists.txt` corrections for consumer-side builds.
- `usd-deps` generation no longer leaves the working tree dirty in git.

### Added
- Test runner supports running individual Python tests; documented in the `testing` skill.

### Removed
- Unused `tests/` directory and `test_skill_docs.py`.

## [1.0.0] - 2026-05-22
### Changed
- Initial version.
