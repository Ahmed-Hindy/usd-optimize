# Usd Optimize

Usd Optimize is a scene optimization library for [OpenUSD](https://openusd.org): a broad set of
operations for processing and optimizing USD stages — geometry, materials, hierarchy, and analysis.
It ships as a standalone C++ library with Python bindings, so you can embed scene optimization in
your own applications and pipelines **without installing Omniverse Kit**.

This `usd-optimize` wheel provides the precompiled Python package. It also registers a set of
performance validators for [`usd-validation-nvidia`](https://pypi.org/project/usd-validation-nvidia/),
which `nvidia_usd_validate` discovers automatically once this package is installed.

## Requirements

- **Python 3.12** — the wheel is built for CPython 3.12 (`cp312`).
- **Windows: the [Microsoft Visual C++ 2015–2022 Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe)** must be installed. The USD runtime DLLs import `MSVCP140.dll` / `VCRUNTIME140.dll` / `VCRUNTIME140_1.dll`, which are not bundled. It is widely present but not part of a base Windows install; install it with `winget install --id Microsoft.VCRedist.2015+.x64` if `import pxr` fails with `DLL load failed while importing _tf`. (A python.org interpreter ships the `VCRUNTIME140` DLLs but not `MSVCP140`, so the redistributable is still required.)

## Documentation

- [GitHub repository](https://github.com/NVIDIA-Omniverse/usd-optimize)

## License

Licensed under the [Apache License 2.0](https://github.com/NVIDIA-Omniverse/usd-optimize/blob/main/LICENSE).
