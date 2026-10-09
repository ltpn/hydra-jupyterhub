# Hydra JupyterHub image implementation plan

## Scope and boundaries

- New standalone repository: `ltpn/hydra-jupyterhub`.
- New container: `ghcr.io/ltpn/hydra-jupyterhub`, Linux amd64 only.
- One long-lived `main` branch; update bots necessarily use temporary PR branches.
- Inspect `ltpn/nedoqs-tutorials` read-only. Never push to it.
- Do not change, deploy to, or run image tests on the Hydra cluster. User later
  authorized read-only notebook diagnostics (kernel logs/specs) on 2026-10-09.
  This exception does not authorize restarting a pod or modifying user files.
- Do not change existing Hydra configuration, workflows, secrets, or applications.
- All implementation files belong to this new directory/repository.

## Initial evidence (2026-10-09)

- Reference main: `de1b3f61cfc2d3b48f4827f184e7cdbfb446ca39`.
- Reference docker: `975815cc99015b2d85efb9a8bdf93b16d9b732b2`.
- Old Dockerfile starts from `julia-1.12.6`, copies files across branches,
  creates a separate Python 3.12/Qiskit environment, and hardcodes the Julia
  environment directory to `v1.12`.
- Original Project contains 15 direct dependencies with exact compat pins.
- Original LocalPreferences selects CUDA 13.2. The previously documented Hydra
  GPU is Pascal (GTX 1070 Ti), which needs a CUDA 12.x toolchain. Verify current
  CUDA.jl support before choosing the new runtime preferences.
- Julia running in a terminal does not establish that the registered IJulia
  kernelspec points to an existing binary and a project containing IJulia.
  Investigate this distinction with real kernel execution, not imports alone.
- GitHub CLI authentication works with network access; sandboxed auth checks
  misleadingly reported an invalid token.
- Docker Desktop was stopped; startup requested for local image diagnostics.

## Decisions to implement and verify

1. Determine newest stable upstream Julia notebook tag and amd64 digest.
   Interpret the user's `12.6 -> 12.7` as Julia `1.12.6 -> 1.12.7`; track stable
   patch and minor updates, excluding prereleases.
2. Keep a readable version tag plus digest pin. Automate PRs when upstream Julia
   changes and when an updated base digest is available. Do not blindly move a
   deployment tag before the new image passes tests.
3. Resolve Julia packages afresh on each build with no source Manifest or compat
   pins; retain the resolved Manifest inside each image for reproducibility.
4. Keep standard Julia CPU targeting portable across amd64 machines rather than
   compile for the GitHub runner or arm64 laptop's native CPU.
5. Remove summer-school requirements, Qiskit environment, tutorial files, and
   cross-branch build machinery. User confirmed retaining the small VS Code/
   code-server integration beyond the upstream Python environment.
6. Build and test natively on an amd64 GitHub-hosted runner. Use emulated local
   amd64 Docker only for focused diagnostics if practical.
7. Test Jupyter Python and IJulia kernel execution, Julia imports, clean/mounted
   notebook homes, and metadata/tag correctness before publication.
8. Export the full resolved Julia package list and direct-dependency versions
   as JSON plus Manifest.toml inside the image and as CI artifacts. Generate
   container tags and labels from actual runtime versions, not Project guesses.
9. Preserve meaningful upstream software-version tag families using installed
   versions, and add Julia direct-dependency tags. Record the actual base digest.
10. User confirmed public repository and image. Repository created successfully.

## Confirmed implementation decisions and observations

- Latest registry base: Julia 1.13.1, index digest
  `sha256:930f69277b2589b3dd671d1b4c1a0b554a811388b3400c7bfca6c6d5986f48dd`.
- User clarified that Project/LocalPreferences must populate the default global
  environment and CUDA must remain 12.9. Directory is computed dynamically.
- CUDA runtime and compiler preferences both set to 12.9, with no Project compat.
- Fresh resolution/precompilation per build; Manifest retained in image/artifact.
- Portable upstream amd64 multitarget CPU settings; no native specialization.
- Native GitHub-hosted amd64 CI chosen. Docker Desktop also started locally.
- Auto-review rejected granting workflow PR-review approval permissions. That
  change was not executed. Built-in Dependabot performs base/action update PRs
  without this grant; workflow review permission remains false.
- Default base currently includes Hub 6.0.1. The earlier Hydra Hub is 5.4.3;
  document/test compatibility before any future deployment, not in this task.
- Local legacy image digest
  `sha256:0dd0d0038cd7a2c3294f95f6ab66a9364b6497d2b578682c727defe51c51d6ec`
  (created 2026-07-23) successfully ran its Julia 1.12.6 IJulia kernel in a fresh
  notebook folder and with an empty local Project. User reports immediate death
  before code on the cluster. Cause remains unconfirmed; do not invent one.
- New kernels use `/usr/local/bin/julia`, explicit current global project, no
  user startup file, and system installation outside the PVC home. Stable ID:
  `julia-hydra`. Test real protocol execution, not simply `using IJulia`.
- User requested a subagent evaluation of dynamic persistent VS Code based on
  `matteosecli/codespeck`, with NO implementation of that alternative. User then
  explicitly approved the minimal extension persistence fix. New image sets
  `CODE_EXTENSIONSDIR=/home/jovyan/.local/share/code-server/extensions`; tests
  will verify proxy arguments and persistence across recreated containers.
  Hydra deployment remains untouched. Microsoft-server alternative is deferred.

## Work status

- [x] Scope recorded; source branches inspected read-only.
- [x] Upstream base and CUDA preference support inspected (GPU hardware untested).
- [x] Immediate kernel failure identified with authorized read-only diagnostics.
- [x] Dockerfile, project, CI, update automation, metadata, tests implemented.
- [x] Local shell/YAML syntax and metadata tag unit tests pass.
- [x] New public GitHub repository created; initial plan pushed on main.
- [ ] Implementation pushed; native CI and actual image verification pending.
- [ ] Native amd64 build/test/publication successful.
- [ ] Registry metadata, tags, and final image pull verified.

Update this file with decisions, commands/results, failures, and outstanding
work as implementation progresses. Never mark unverified work complete.

## Current validation progress

- Implementation commit `b72c3ae`; superseded by approved persistence commit
  `acdab03` (with two-container extension/settings tests).
- Native Actions run `37933714709` was cancelled deliberately after the newer
  implementation was pushed; it was not a successful image build.
- Current native build: `37934140553` on commit `acdab03`.
- Local unit tests, Python compilation, shell syntax, TOML constraints/preferences,
  and YAML parsing passed. These are not a substitute for the native image tests.
- Dependabot jobs ran successfully; no update PR is expected while the configured
  upstream version is already current. Prefix isolation was checked against
  Dependabot's Docker Tag parser/comparison source.
- GitHub Container Registry defaults new packages to private even for a public
  repository. After a successful publish, verify anonymous access and arrange
  only this new package's public visibility if necessary; do not broaden account
  tokens or workflow review permissions.
- User explicitly approved read-only notebook diagnostics. Only inspect notebook
  logs and effective Julia kernelspec/environment; no restart, write, or deploy.
- Confirmed kernel error: local tutorial Manifest requires IJulia 1.34.2/tree
  `d9ea0eeac84e4a7397858847c8b5f1d4ef515ded`; only global IJulia 1.34.4/tree
  `102656c4efc9737f892e1bca7e66ae374c650740` is present in the image's depot.
  Kernel `--project=@.` selects the local environment and fails importing IJulia.
  New explicit-global kernels avoid this; regression fixture now includes a
  local Manifest referencing an unavailable IJulia tree. No live files changed.
- User notes the failure can also occur for new notebooks. A new notebook can
  inherit the surrounding project's environment, but do not generalize the
  observed worktree failure to all contexts: read-only Base.find_package finds
  global IJulia from /home/jovyan and returns nothing from the tutorial directory.
  Home-level Untitled notebook has no recorded kernelspec. Further live
  diagnostics are stopped per user's request; no live kernel was started.
- User subsequently confirmed that a notebook outside the tutorial folder works
  and agreed this is project/environment drift rather than a container bug.
  Superseding the earlier workaround decision, retain normal IJulia `--project=@.`
  discovery in regenerated stable/system kernels. Tests cover global startup
  and local project discovery, not masking an uninstantiated user Manifest.
- Native run 37934140553 resolved all 17 direct dependencies and successfully
  precompiled 725 packages on Julia 1.13.1. It failed the first smoke assertion
  because Python distribution names were not normalized (underscore vs hyphen),
  not because Julia/package precompilation failed. Normalize PEP 503 names in
  metadata and export metadata before smoke checks for failure diagnostics.
- Superseded runs 37936384203/37937626463 cancelled before further compilation;
  the final source preserves normal IJulia project selection as the user agreed.
