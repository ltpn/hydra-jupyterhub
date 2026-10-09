# Hydra JupyterHub image implementation plan

## Scope and boundaries

- New standalone repository: `ltpn/hydra-jupyterhub`.
- New container: `ghcr.io/ltpn/hydra-jupyterhub`, Linux amd64 only.
- One long-lived `main` branch; update bots necessarily use temporary PR branches.
- Inspect `ltpn/nedoqs-tutorials` read-only. Never push to it.
- Do not inspect, change, deploy to, or run tests on the Hydra cluster for this task.
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
   cross-branch build machinery. Pending user preference: retain only the small
   VS Code/code-server integration beyond the upstream Python environment.
6. Build and test natively on an amd64 GitHub-hosted runner. Use emulated local
   amd64 Docker only for focused diagnostics if practical.
7. Test Jupyter Python and IJulia kernel execution, Julia imports, clean/mounted
   notebook homes, and metadata/tag correctness before publication.
8. Export the full resolved Julia package list and direct-dependency versions
   as JSON plus Manifest.toml inside the image and as CI artifacts. Generate
   container tags and labels from actual runtime versions, not Project guesses.
9. Preserve meaningful upstream software-version tag families using installed
   versions, and add Julia direct-dependency tags. Record the actual base digest.
10. Public repository/image is the proposed default, matching the public
    reference and allowing free hosted CI. User preference question pending.

## Work status

- [x] Scope recorded; source branches inspected read-only.
- [ ] Upstream image and CUDA compatibility verified.
- [ ] Old kernel failure reproduced or clearly qualified.
- [ ] Dockerfile, project, CI, update automation, metadata, tests implemented.
- [ ] Local validation completed.
- [ ] New GitHub repository created and code pushed.
- [ ] Native amd64 build/test/publication successful.
- [ ] Registry metadata, tags, and final image pull verified.

Update this file with decisions, commands/results, failures, and outstanding
work as implementation progresses. Never mark unverified work complete.
