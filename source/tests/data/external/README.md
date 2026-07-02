# External USD Fixtures

This directory contains tiny third-party USD assets used only for package/runtime smoke tests.

## `openusd_helloworld.usda`

- Source repository: `https://github.com/PixarAnimationStudios/OpenUSD`
- Source file: `extras/usd/tutorials/authoringProperties/HelloWorld.usda`
- Source branch used when imported: `release`
- Raw source URL: `https://raw.githubusercontent.com/PixarAnimationStudios/OpenUSD/release/extras/usd/tutorials/authoringProperties/HelloWorld.usda`
- License: OpenUSD's repository license, the Tomorrow Open Source Technology License 1.0 terms in `LICENSE.txt`.
- Local use: file-backed smoke fixture for the generated Windows prebuilt package.

The fixture is intentionally very small and ASCII `.usda` so CI failures are easy to inspect. It defines `/hello/world`, a single sphere under an xform.
