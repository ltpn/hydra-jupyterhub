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
- Inspect `ltpn/matlab-dockerfile` read-only; user will update it independently.
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
11. User added MATLAB notebooks and browser-desktop integration through MathWorks
    `jupyter-matlab-proxy`. Reuse LTPN's published MATLAB installation/toolboxes
    rather than maintain another MPM product installation in this repository.
    Target current MATLAB R2026b; no license credentials in the public image.

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
- [x] Implementation pushed; native notebook CI successful.
- [x] Native amd64 combined build/test/publication successful.
- [x] Registry metadata, all 34 tags, and final full image pull verified.

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

## MATLAB integration (added 2026-10-09)

- Current native notebook build: 37938254659, commit 00a06b5, still in progress.
- Correct public MATLAB package is `ghcr.io/ltpn/matlab`, not the nested image
  path in the reference repository's current workflow. R2026a resolves to digest
  `sha256:73a28217a2f2fbe416a3d42d8336d8b75f0dc00696cab072c176b7b95b9f9803`.
- R2026b is current according to MathWorks, but LTPN's R2026b tag is not available
  yet. User will update the reference independently; never substitute R2026a
  silently in the requested final image.
- Reference main and upgrade-ci Dockerfiles/workflows default to MATLAB only.
  Ask which extra products/image source contains LTPN additions. Copy the actual
  complete `/opt/matlab` installation, preserving whatever toolboxes it contains.
- Latest Julia base is Ubuntu 26.04. MathWorks' validated R2026b list includes
  Ubuntu 24.04/22.04, not 26.04. However the official container-images repository
  provides `matlab-deps/r2026b/ubuntu26.04/base-dependencies-amd64.txt`.
  Use that concrete dependency list and test; describe validation limitation.
- Dependency-list source commit: `99bc35ad91f417f5635af41262af2e92c4521df3`.
- Prepare a separate MATLAB installation layer over the tested notebook image;
  preserve upstream entrypoint/notebook uid/PVC conventions. Add Xvfb, system
  kernelspec, and proxy package while constraining installed Python packages.
- Record MATLAB release and image provenance in final runtime metadata/tags.
  Structural checks can run without a license; licensed execution must not be
  claimed from a kernelspec/import check. No Hydra deployment change authorized.
- [x] MATLAB integration layer built/tested with LTPN's R2026b installation.
- User clarified the deep-learning variant. Confirmed the actual customized
  Dockerfile is `alternates/building-on-matlab-docker-image/Dockerfile`; it uses
  `mathworks/matlab-deep-learning` and adds Symbolic Math Toolbox and ResNet-50.
  Its `from-matlab-docker-build-test.yml` publishes `ghcr.io/ltpn/matlab`, unlike
  the main Dockerfile/workflow initially inspected. No product list input needed.
- Published R2026a image history confirms the deep-learning products plus LTPN's
  symbolic addition. Preserve support packages under their original absolute
  `/home/matlab/Documents/MATLAB/SupportPackages` path, outside the notebook PVC,
  as well as `/opt/MathWorks/ServiceHost` for MathWorks online licensing.
- Local reference pull encountered unexpected EOF; retry once using cached layers.
- User provided a local MATLAB batch token strictly for testing, with conditional
  permission for GitHub only if no other org user could retrieve it. This cannot
  be guaranteed for repository/workflow writers, so DO NOT upload any token to
  GitHub. Keep it outside this repository and Docker build context. Licensed
  validation is opt-in, in disposable local containers with a read-only mount,
  captured output and explicit non-secret result markers only. No public CI
  secret or deployment license configuration is added.
- Local licensed R2026a source-image validation PASSED: arithmetic, Symbolic
  Math, image resize, ResNet-50 entry point; `ver` confirms all 11 installed
  products including MATLAB and Symbolic Math. This checks the existing source
  installation, not the new combined Ubuntu 26.04 image. Token stayed local.
- Strengthened and reran that check: `resnet50` actually loads the pretrained
  network and has layers, confirming inherited support-package data is usable.
- First batch expression used a multiline string and yielded no success marker.
  Flattened it to a single-line statement as required by this launcher behavior;
  explicit marker validation now prevents zero-exit false positives.
- MATLAB release/products/support-package versions are parsed from actual
  VersionInfo.xml and appdata/products catalogs. Add release/full-version tags
  and source-image digest labels without guessing from the requested release.
- Local unit tests, Python compilation, shell syntax, YAML parsing and diff
  whitespace checks pass for the new layer; actual combined build is pending.

## Successful notebook publication and MATLAB compatibility checks

- Native notebook run 37938254659 on 00a06b5 PASSED: two real kernel/import
  smoke runs, including a mounted home, and VS Code extension/settings checks
  across recreated containers. Published digest:
  `sha256:96bbca771325139df59f94ee3471bd9fdf61d6656b73afc748831b130f623933`.
- Explicit anonymous registry-token test returns HTTP 200; registry config
  confirms amd64 and matching source revision. No visibility change or broader
  account token scope was needed. Package REST API requires read:packages;
  do not request this scope merely to query visibility already proven anonymously.
- Artifact review identified one incorrect version field: code-server's first-run
  timestamp log was parsed as its version, producing an erroneous code-server
  alias in the initial notebook-only publication. Correct the parser to select
  a semantic version line; regression tests cover timestamp noise. Combined
  probe now reports actual code-server 4.141.0. Do not represent that initial
  image as the final MATLAB-enabled image or final corrected metadata.
- Latest Julia notebook/Python/Ubuntu 26.04 compatibility probe built locally
  without the full extra Julia package installation (not published/deployed).
  MATLAB proxy installed successfully with all existing Python versions frozen.
  Version metadata identifies 24 installed products/support packages.
- MATLAB executable/proxy/system kernelspec checks passed normally and with a
  mounted home. Licensed arithmetic, Symbolic Math, and image processing worked;
  ResNet-50 initially failed with `nnet_cnn:supportpackages:NotInstalled` because
  the default support root followed the new user's home. MW_SUPPORT_PACKAGE_ROOT
  did not fix this (do not add it as an unverified workaround).
- A symlink from the notebook user's default support-root location to the
  bundled original support directory fixes actual model loading. Implement it
  through the verified upstream before-notebook hook as uid 1000/gid 100,
  after home/PVC mounting; preserve existing user-managed roots.
- Real start.sh hook execution, proxy/kernelspec checks, and licensed ResNet-50
  loading all PASSED across recreated local probe containers sharing a disposable
  volume. Token mount remained local/read-only; no raw licensing output uploaded.
- Use the daemon builder associated with `docker context show`, so Docker Desktop
  desktop-linux and native CI default contexts both reuse local image layers.
- MATLAB-enabled run 37941981745 fails early as designed while LTPN R2026b is
  unavailable; do not spend another Julia precompile cycle until that prerequisite
  is published. Waiting for user-provided R2026b source; no original workflow runs
  or Hydra operations are triggered here.
- Corrected source commit a9328fa pushed. Run 37945799712 confirms the sole
  current prerequisite error: `ghcr.io/ltpn/matlab:R2026b: not found`.
- Full public notebook image pull by immutable digest SUCCEEDED locally.
- MATLAB layer also built over that actual published/full scientific notebook,
  explicitly using R2026a for a LOCAL-ONLY combined test. Real startup hooks,
  proxy/kernelspec, and licensed arithmetic/symbolic/image-resize/ResNet-50
  model loading all PASSED across recreated containers sharing a mounted home.
  All existing Python distribution versions and the resolved Julia Manifest
  are unchanged by the MATLAB layer. Metadata retains all 17 direct Julia deps,
  correct code-server 4.141.0, and 24 MATLAB product/support-package entries.
- R2026a test images are not published and nothing is deployed to Hydra.
  Final R2026b combined build/publication remains pending the user's source tag.

## Resumed validation

- User asked to resume after usage limit. Existing goal status is usageLimited;
  status resumption is user/system controlled, not changed through update_goal.
  Continue the explicitly requested task and keep progress in this plan.
- LTPN's alternate Dockerfile now says R2026b, but the published tag is still
  absent at the first resumed check. Inspect original workflow read-only only.
- Closer inspection of Dependabot run 37941613084 shows no parsed dependency
  checks, not evidence that the Julia base was actually tracked. Replace the
  whole-image ARG/FROM indirection with a literal pinned FROM. Store that exact
  line's image reference in base-image.txt for metadata, so bot updates do not
  leave a duplicate metadata string stale. Restrict Docker updates to the Julia
  repository name as documented by GitHub (registry excluded from name).
- R2026b is now published at
  `sha256:5a12950f75c90345dcf73f26c856fbcd0bb8781e8b4c4fe5c793220fcbb7b882`.
  Native combined build 37960361376 on fb1400b is running. Local R2026b pull
  completed; build the layer and run licensed validation locally only.
- Corrected Dependabot Docker run 37960372097 explicitly checks
  jupyter/julia-notebook, queries Quay's Julia tags/digest, and reports current
  latest julia-1.13.1/no update needed. Automation is now actually verified,
  superseding the earlier empty-dependency run. Actions updater also passes.
- Local R2026b layer over the actual tested full scientific notebook PASSED:
  real startup hooks, system kernelspec/proxy, mounted-home behavior, licensed
  arithmetic/Symbolic Math/image resize and actual ResNet-50 model loading.
  Installed MATLAB version 26.2.0.3386108; 24 product/support-package catalog
  entries. Two recreated containers share a disposable home; the token stays
  read-only/local and is never passed to public CI or embedded in the image.

## Final native publication

- Native combined run 37960361376 on fb1400b SUCCEEDED. Fresh Julia resolution,
  both real kernel/import smoke checks (including after MATLAB/PVC), both MATLAB
  proxy/kernelspec/home checks, and actual VS Code extension/settings persistence
  all passed before publication. No MATLAB token was used in GitHub Actions.
- Published Linux amd64 digest:
  `sha256:56c07d37d0ceedb66f10862ef091adf7c2d1c9558972f5ed5a5402b953750c1f`.
- All 34 generated registry tags resolve anonymously to that same digest. OCI
  labels match the artifact's labels.json, source fb1400b, base tag/digest, and
  MATLAB release/version/source-image digest. Registry architecture is amd64.
- Final metadata: Julia 1.13.1, Python 3.13.15, Hub 6.0.1, code-server 4.141.0,
  MATLAB R2026b 26.2.0.3386108; 17 direct Julia dependencies and 24 MATLAB
  product/support-package entries. Runtime/compiler preferences both CUDA 12.9.
- Full resolved Manifest checksum verified:
  `5c45f2b27123b0cfcea18742d02f8203e0f2f4d0e067dab4e949ff4e3dd1913d`.
  See native artifact for the authoritative full checksum and environment.
- Full final-image pull SUCCEEDED by immutable digest; fetched image architecture
  is amd64, size 24,127,273,658 bytes. A transient layer-transfer interruption
  retried successfully and passed checksum verification. No Hydra deployment or
  original repository modification occurred. Physical GPU execution and a
  Hub 5.4.3/6.0.1 deployment pairing are outside the authorized image-only work.
- Exact published-digest licensed MATLAB check PASSED with an empty disposable
  mounted home and real upstream startup hooks: arithmetic, Symbolic Math, image
  resize, ResNet-50 model loading, and MATLAB R2026b product inventory.
- This final optional local check first hit Docker VM storage exhaustion before
  MATLAB launched. Removed only task-created diagnostic image tags/the recorded
  superseded diagnostic image, plus 32 specifically identified task-owned private
  reclaimable cache IDs (including their descendants). Scoped cache cleanup
  reclaimed 28.05 GB; unrelated images/volumes/cache were preserved. Retry passed.
- All requested image implementation/publication/validation work is complete.
  Native source revision is fb1400b; later commits update verification docs only.
  Personal MATLAB batch token remained local, uncommitted, excluded from builds,
  and absent from GitHub secrets/workflows. The final image stays available locally.
