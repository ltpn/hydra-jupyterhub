# syntax=docker/dockerfile:1
# Dependabot tracks stable Julia-prefixed tags and the corresponding base digest.
# Keep R2026a for Hydra's GTX 1070 Ti (Pascal, compute capability 6.1).
# R2026b requires compute capability >= 7.5; R2026a still supports Pascal.
# https://www.mathworks.com/help/releases/R2026a/parallel-computing/gpu-computing-requirements.html
ARG MATLAB_IMAGE=ghcr.io/ltpn/matlab:R2026a
ARG MATLAB_RELEASE=R2026a
ARG MATLAB_PLATFORM=linux/amd64
FROM --platform=${MATLAB_PLATFORM} ${MATLAB_IMAGE} AS matlab_installation
ARG MATLAB_RELEASE
# Disable Go GC only for mpm when building under amd64 emulation on Apple Silicon.
ARG MPM_GOGC=100
USER root
WORKDIR /tmp
# Add the toolbox to the existing LTPN MATLAB installation; no license is baked in.
RUN wget -q https://www.mathworks.com/mpm/glnxa64/mpm -O /tmp/mpm \
    && chmod +x /tmp/mpm \
    && GOGC=${MPM_GOGC} HOME=/home/matlab /tmp/mpm install --release="${MATLAB_RELEASE}" \
       --destination="/opt/matlab/${MATLAB_RELEASE}" --products=Curve_Fitting_Toolbox \
    && rm -f /tmp/mpm /tmp/mathworks_root.log
FROM quay.io/jupyter/julia-notebook:julia-1.13.1@sha256:930f69277b2589b3dd671d1b4c1a0b554a811388b3400c7bfca6c6d5986f48dd
ARG MATLAB_IMAGE
ARG MATLAB_RELEASE
ARG TARGETARCH
ARG SOURCE_REVISION=local
ARG BUILD_DATE=unknown
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV HYDRA_SOURCE_REVISION=${SOURCE_REVISION} \
    HYDRA_BUILD_DATE=${BUILD_DATE} \
    JULIA_NUM_THREADS=auto \
    JULIA_CPU_TARGET="generic;sandybridge,-xsaveopt,clone_all;haswell,-rdrnd,base(1);x86-64-v4,-rdrnd,base(1)" \
    CODE_EXTENSIONSDIR=/home/jovyan/.local/share/code-server/extensions \
    JUPYTER_PREFER_ENV_PATH=1 \
    GKSwstype=100 \
    HYDRA_MATLAB_IMAGE=${MATLAB_IMAGE} \
    MATLAB_ROOT=/opt/matlab/${MATLAB_RELEASE} \
    MWI_CUSTOM_MATLAB_ROOT=/opt/matlab/${MATLAB_RELEASE} \
    MATHWORKS_SERVICE_HOST_MANAGED_INSTALL_ROOT=/opt/MathWorks/ServiceHost \
    MW_SERVICEHOST_USE_HOSTNAME_FOR_PERSISTENCE=false

USER root
RUN test "${TARGETARCH}" = amd64 || { echo 'This image supports linux/amd64 only.' >&2; exit 1; }
COPY --from=matlab_installation /opt/matlab/ /opt/matlab/
COPY --from=matlab_installation /home/matlab/Documents/MATLAB/SupportPackages/ /home/matlab/Documents/MATLAB/SupportPackages/
COPY --from=matlab_installation /opt/MathWorks/ServiceHost/ /opt/MathWorks/ServiceHost/
COPY MATLAB-DEPS-LICENSE.md /usr/local/share/hydra-jupyterhub/MATLAB-DEPS-LICENSE.md
COPY matlab-base-dependencies.txt /tmp/matlab-base-dependencies.txt
COPY scripts/matlab-support-packages.sh /usr/local/bin/before-notebook.d/20-matlab-support-packages.sh
RUN test -x "${MATLAB_ROOT}/bin/matlab" \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive xargs -a /tmp/matlab-base-dependencies.txt \
       apt-get install --yes --no-install-recommends xvfb xauth \
    && rm -rf /var/lib/apt/lists/* /tmp/matlab-base-dependencies.txt \
    && ln -s "${MATLAB_ROOT}/bin/matlab" /usr/local/bin/matlab
COPY Dockerfile Project.toml LocalPreferences.toml /opt/hydra-build/
COPY scripts/install-julia.jl scripts/export-metadata.py scripts/runtime_versions.py scripts/configure-vscode-launcher.py /opt/hydra-build/
RUN chown -R "${NB_UID}:${NB_GID}" /opt/hydra-build \
    && mkdir -p /usr/local/share/hydra-jupyterhub \
    && chown "${NB_UID}:${NB_GID}" /usr/local/share/hydra-jupyterhub \
    && awk '/^FROM quay.io\/jupyter\/julia-notebook:/ {print $2; exit}' /opt/hydra-build/Dockerfile > /usr/local/share/hydra-jupyterhub/base-image.txt

USER ${NB_UID}
# Preserve the upstream Python stack while adding editor and MATLAB integration.
RUN mamba install --yes --freeze-installed jupyter-vscode-proxy code-server btop \
    && mamba clean --all --yes \
    && fix-permissions "${CONDA_DIR}"
RUN python -c 'import importlib.metadata as m; from pathlib import Path; Path("/tmp/hydra-python-constraints.txt").write_text("\n".join(d.metadata["Name"]+"=="+d.version for d in m.distributions() if d.metadata["Name"]))' \
    && python -m pip install --no-cache-dir --constraint /tmp/hydra-python-constraints.txt jupyter-matlab-proxy \
    && install-matlab-kernelspec \
    && python -m pip check \
    && rm /tmp/hydra-python-constraints.txt \
    && fix-permissions "${CONDA_DIR}"
RUN JULIA_NUM_PRECOMPILE_TASKS=2 julia --threads=2 --startup-file=no /opt/hydra-build/install-julia.jl \
    && fix-permissions "${JULIA_PKGDIR}" "${CONDA_DIR}/share/jupyter"

USER root
# Download the icon at build time: HEAD, then the pinned commit, then plugin default.
RUN python /opt/hydra-build/configure-vscode-launcher.py
USER ${NB_UID}
RUN python /opt/hydra-build/export-metadata.py
USER root
RUN rm -rf /opt/hydra-build
USER ${NB_UID}
WORKDIR /home/${NB_USER}

LABEL org.opencontainers.image.title="hydra-jupyterhub" \
    org.opencontainers.image.description="AMD64 JupyterLab with Julia, CUDA 12.9 preferences, VS Code, Pluto, and MATLAB" \
    org.opencontainers.image.source="https://github.com/ltpn/hydra-jupyterhub" \
    org.opencontainers.image.licenses="MIT" \
    org.ltpn.hydra-jupyterhub.metadata="/usr/local/share/hydra-jupyterhub/versions.json"
