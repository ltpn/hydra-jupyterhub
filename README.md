# Hydra JupyterHub notebook image

A standalone Linux **amd64** notebook environment, published as
`ghcr.io/ltpn/hydra-jupyterhub`. Source and CI live together on `main`.
It does not depend on, fetch files from, or deploy `nedoqs-tutorials`.

## Included software

- Latest stable `quay.io/jupyter/julia-notebook`, with a readable Julia tag and
  a pinned base-image digest in the Dockerfile.
- The upstream Python/Jupyter environment; no `requirements.txt`, Qiskit
  environment, tutorial notebooks, or custom scientific Python requirements.
- `jupyter-vscode-proxy` and `code-server` for the `/vscode` entry point. Their
  installation freezes existing conda packages. No user extensions are seeded.
  `CODE_EXTENSIONSDIR=/home/jovyan/.local/share/code-server/extensions` places
  user extensions on the persistent home volume instead of conda's default
  `/opt/conda/share/code-server/extensions` location.
- All Julia dependencies in `Project.toml`, plus the upstream HDF5/IJulia/Pluto
  functionality. The Project contains no version constraints.
- CUDA runtime **and compiler** preferences at **12.9**, for Hydra's Pascal GPU.
  This toolchain choice is separate from Julia package version constraints.

The default Julia environment is computed from the running Julia version:
`/opt/julia/environments/v<major>.<minor>/`. Project and LocalPreferences are
copied there, and any inherited Manifest for that environment is removed before
resolution. This preserves the global-environment approach used by JupyterLab,
without hardcoding `v1.12`.

Each build resolves the newest **mutually compatible registered releases**.
Unpinned does not mean every dependency can independently use its newest version:
upstream packages still impose their own compatibility constraints. The resolved
Manifest is retained inside the image, not committed to this repository.

## Julia kernel and CPU targeting

Select **Julia (Hydra)**, kernel ID `julia-hydra`. The exact displayed Julia
version follows the base. Its kernelspec uses `/usr/local/bin/julia`, explicitly
activates the current default global environment, and lives under
`/opt/conda/share/jupyter/kernels`, outside the notebook home PVC.
The current-version `julia-<major>.<minor>` kernel is also registered.
The stable `julia-hydra` ID is preferable in saved notebooks across Julia updates.

We use the portable amd64 CPU target sequence used by upstream Jupyter Docker
Stacks, not `native` or a CPU model inferred from a GitHub runner/arm64 laptop.
Native specialization may make compiled caches unusable on another host and
would require rebuilding when hardware changes. Ordinary JIT compilation can
still optimize code for the runtime CPU.

## Build and verification

```bash
bash scripts/build.sh
```

The script always uses `--platform linux/amd64`, pulls the digest-pinned base,
and disables install-layer caching so scheduled builds actually refresh Julia
packages. Do not omit `--no-cache` when using `docker build` directly.
An arm64 laptop needs amd64 emulation; CI uses native amd64 Ubuntu runners.

Before publication, the build runs:

- Python and Julia kernels through the Jupyter messaging protocol.
- Julia execution/imports in a fresh directory and a directory whose local
  Manifest points to an unavailable IJulia tree (the observed crash scenario).
- A repeat with a mounted notebook home, ensuring the system kernelspec remains
  available when a PVC hides the image's home directory.
- Installation of a tiny local test extension and user settings, followed by
  verification in a recreated container using the same home volume. This fixture
  is used only in disposable tests, not preinstalled in the published image.
- CPU-only imports of CUDA, plotting, tensor, ODE, and notebook packages.
- Architecture and metadata/tag checks.

These tests do **not** demonstrate GPU execution on the physical GTX 1070 Ti.
GitHub-hosted runners have no NVIDIA GPU; the Hydra cluster is not accessed or
changed by this repository's workflows. Test actual GPU computation separately
before a deployment migration.

The upstream image also supplies its own `jupyterhub-singleuser` version.
Current base metadata includes **JupyterHub 6.0.1**, whereas the previously
documented Hydra Hub is 5.4.3. Keep Hub/single-user versions compatible and test
that pairing before switching images. This project does not modify Hydra or
downgrade the upstream Python stack to conceal the difference.

## Automation

- Main-branch changes build, test, then publish. PRs build/test without publishing.
- A weekly scheduled build resolves fresh Julia releases even if source has not
  changed; manual `workflow_dispatch` is available.
- Dependabot checks Docker daily for stable `julia-*` tag/digest updates, including
  patch and minor versions, and opens PRs. GitHub Actions dependencies are checked
  weekly. The Julia tag family keeps unrelated `hub-*`/`python-*` versions out of
  base-image selection.
- Update PRs are reviewed/merged normally. No automatic merge or workflow
  permission to approve PR reviews is configured.
- `main` is the only long-lived branch. Bot PR branches are temporary and are
  automatically deleted after merge.

## Tags and installed-package metadata

The publisher reads the **built image's** Manifest/runtime metadata and creates
tags such as `julia-1.13.1`, `hub-6.0.1`, `lab-4.6.4`, `python-3.13.15`,
`python-3.13`, `ubuntu-26.04`, and direct Julia package tags such as
`quantumtoolbox-<resolved-version>` and `cuda-<resolved-version>`.
Those examples describe tag families; inspect metadata for exact package versions.
`+` in a JLL build suffix is encoded as `_` to make a valid Docker tag.

`latest`, `amd64`, and software-version tags are moving aliases. The
`build-<run-id>-<attempt>` and `sha-<commit>-<run-id>-<attempt>` tags identify the
tested snapshot; use its immutable registry digest for a reproducible deployment.
The same commit may resolve different packages on later scheduled builds.

Every image contains:

```text
/usr/local/share/hydra-jupyterhub/versions.json
/usr/local/share/hydra-jupyterhub/Project.toml
/usr/local/share/hydra-jupyterhub/LocalPreferences.toml
/usr/local/share/hydra-jupyterhub/Manifest.toml
```

`versions.json` contains all resolved Julia packages/UUIDs/versions, flags direct
dependencies, records Python distributions, software/OS versions, Julia environment,
CPU targets, CUDA preferences, base tag/digest, source commit, and Manifest SHA256.
OCI labels contain direct Julia versions as JSON, software versions as JSON, the
Manifest hash, base provenance, and the metadata-file path.

```bash
docker run --rm --platform linux/amd64 --entrypoint cat \
  ghcr.io/ltpn/hydra-jupyterhub:latest \
  /usr/local/share/hydra-jupyterhub/versions.json
docker inspect ghcr.io/ltpn/hydra-jupyterhub:latest \
  --format '{{json .Config.Labels}}'
```

The complete resolved environment is also uploaded as the
`resolved-environment-amd64` Actions artifact. No credentials are required for
CI: publication uses the repository-scoped `GITHUB_TOKEN`.

## Kernel-crash investigation

The existing amd64 `nedoqs-tutorials:docker` image was tested read-only locally
at digest `sha256:0dd0d0038cd7a2c3294f95f6ab66a9364b6497d2b578682c727defe51c51d6ec`.
Its Julia 1.12.6 IJulia kernel successfully executed `1+1`, both without and
with an empty local Project. The user subsequently authorized read-only notebook
diagnostics, which identified the actual failure:

- The shipped kernel starts with `--project=@.`, selecting a nearby local Project.
- The cloned tutorial project's Manifest records IJulia **1.34.2** and tree
  `d9ea0eeac84e4a7397858847c8b5f1d4ef515ded`.
- The image's populated global environment and package depot contain IJulia
  **1.34.4**, tree `102656c4efc9737f892e1bca7e66ae374c650740`.
- The kernel stderr repeatedly reports that the required IJulia is not installed,
  then the Jupyter kernel restarter gives up.

This establishes an uninstantiated local Manifest/environment mismatch in the
tutorial-directory launch context, not evidence that Julia 1.12.6 itself crashes.
A subsequent read-only `Base.find_package("IJulia")` check finds the installed
package from `/home/jovyan` but returns `nothing` from the tutorial directory.
A new notebook can inherit an existing project's environment; a new `.ipynb`
does not instantiate that project. A separate failure from the fresh home-level
context has not been reproduced and should be revisited after image testing.
Plain terminal Julia selects the global environment, and VS Code/terminal Julia
startup does not necessarily import IJulia at all.

The new kernels explicitly use the populated global `@v<major>.<minor>` project
for startup, matching the user's desired default-environment approach. The smoke
test includes a local Project/Manifest with an unavailable IJulia tree and checks
that startup still succeeds. Users can explicitly `Pkg.activate` another project
after the kernel starts. A truly project-specific IJulia kernel requires that
project's dependencies to be instantiated; the global default is not a substitute
for instantiating an explicitly activated project.

Only logs and relevant dependency/kernel metadata were inspected on Hydra. No
user files, running notebooks, source repository, or deployment were modified.

## Scope of the VS Code alternative

Dynamic per-user installation of Microsoft's VS Code Server was requested for
evaluation only. It is **not implemented** here. Moving binaries to a PVC is not
necessary to persist settings/extensions, and downloading Microsoft binaries at
runtime does not itself settle Server/Marketplace licensing. The image retains
the standard conda code-server/proxy integration. The user approved the minimal
extension-directory persistence fix, implemented through `CODE_EXTENSIONSDIR`;
the editor binary remains in the image. Settings normally live in
`~/.local/share/code-server` and `~/.config/code-server`, on the persistent home.
See [VSCODE-EVALUATION.md](VSCODE-EVALUATION.md) for the comparison and sources.

## Sources

- [Upstream stack and tags](https://jupyter-docker-stacks.readthedocs.io/en/latest/using/selecting.html)
- [Upstream Julia setup](https://github.com/jupyter/docker-stacks/blob/main/images/minimal-notebook/setup-scripts/setup-julia-packages.bash)
- [CUDA preferences](https://cuda.juliagpu.org/stable/installation/overview/)
- [IJulia troubleshooting](https://ijulia.org/stable/manual/troubleshooting/)
- [Dependabot Docker tag comparison](https://github.com/dependabot/dependabot-core/blob/main/docker/lib/dependabot/docker/tag.rb)

This repository's source is MIT-licensed; upstream software retains its own
licenses. The reference Project/Docker conventions originated in LTPN's
MIT-licensed `nedoqs-tutorials`; that repository is not modified or used at build
time. Implementation decisions and validation status are tracked in `PLAN.md`.
