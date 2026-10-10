# Hydra notebook image

`ghcr.io/ltpn/hydra-jupyterhub:latest` — Linux **amd64**.

JupyterLab with the default Python stack, Julia, VS Code/code-server, Pluto,
and MATLAB R2026a with LTPN's deep-learning, Symbolic Math, and Curve Fitting toolboxes.
MATLAB stays on R2026a because R2026b dropped support for Hydra's Pascal GPU.
Julia packages are listed in [Project.toml](Project.toml); CUDA runtime and
compiler preferences are **12.9**.

## Run locally

Start a one-user test Hub:

```bash
bash scripts/run-local.sh
```

Open **http://localhost:8000/jupyter/hub/**. Login: **jovyan**, any password.
This localhost-only test uses a dummy login. The script installs the Hub proxy
inside the test container on first use.

Useful links after login:

- [JupyterLab](http://localhost:8000/jupyter/hub/user-redirect/lab)
- [VS Code](http://localhost:8000/jupyter/hub/user-redirect/vscode)
- [Pluto](http://localhost:8000/jupyter/hub/user-redirect/pluto)
- [MATLAB](http://localhost:8000/jupyter/hub/user-redirect/matlab)

Stop with **Ctrl-C**, then restart:

```bash
docker start -ai hydra-jupyterhub-local-hub
```

Notebooks, settings, and VS Code extensions persist in the named Docker volume
`hydra-jupyterhub-local-home`. To fetch a newer image, remove the stopped
container and rerun the script; the home volume remains:

```bash
docker rm hydra-jupyterhub-local-hub
bash scripts/run-local.sh
```

For JupyterLab alone, without the Hub login:

```bash
bash scripts/run-local.sh lab
```

Use the token shown in the logs. Override settings as needed:

```bash
PORT=8001 MEMORY=10g IMAGE=ghcr.io/ltpn/hydra-jupyterhub:julia-1.13.1 bash scripts/run-local.sh
```

Apple Silicon runs this amd64 image through emulation. NVIDIA GPU execution
requires a Linux machine with NVIDIA Container Toolkit.

## Build and test

```bash
bash scripts/build.sh
IMAGE=hydra-jupyterhub:tested PULL_POLICY=never bash scripts/run-local.sh
```

One Dockerfile combines the Julia base and LTPN's MATLAB installation. Every
build resolves compatible Julia package releases, precompiles them, and tests
kernels, MATLAB integration, mounted homes, and VS Code extension persistence.
Native amd64 builds are faster than emulated laptop builds.

Select **Julia (Hydra)** in JupyterLab. Its default environment is
`/opt/julia/environments/v<major>.<minor>`. A notebook inside another Julia
project uses that project's environment; instantiate its dependencies first.

## Images and updates

Main-branch builds publish after tests pass; weekly builds refresh Julia packages.
Dependabot opens PRs for Julia base updates. Tags include `latest`, actual Julia
and software/package versions, and matching upstream Quay aliases, including
amd64 aliases. ARM aliases are excluded. Use a registry digest for an exact snapshot.

Resolved versions, preferences, and the full Julia Manifest are in
`/usr/local/share/hydra-jupyterhub/`; CI also uploads them as an artifact.

## Use with JupyterHub

```yaml
singleuser:
  image:
    name: ghcr.io/ltpn/hydra-jupyterhub
    tag: latest
    pullPolicy: Always
```

`Always` checks the image when a container starts; it does not replace running
notebook servers. Keep the Hub and image's `jupyterhub-singleuser` versions
compatible. The currently published image includes **JupyterHub 6.0.1**.

MATLAB users supply their own MathWorks account or network license in its login
dialog. No license credentials are included. Batch-token tests are local only;
tokens must not be committed, copied into an image, or uploaded to CI.

Project source is MIT-licensed. MATLAB, upstream software, and the
[vendored dependency list](MATLAB-DEPS-LICENSE.md) retain their own licenses.
