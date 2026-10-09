# syntax=docker/dockerfile:1
# Dependabot tracks stable Julia-prefixed tags and the corresponding base digest.
ARG BASE_IMAGE=quay.io/jupyter/julia-notebook:julia-1.13.1@sha256:930f69277b2589b3dd671d1b4c1a0b554a811388b3400c7bfca6c6d5986f48dd
FROM ${BASE_IMAGE}
ARG BASE_IMAGE
ARG TARGETARCH
ARG SOURCE_REVISION=local
ARG BUILD_DATE=unknown
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV HYDRA_BASE_IMAGE=${BASE_IMAGE} \
    HYDRA_SOURCE_REVISION=${SOURCE_REVISION} \
    HYDRA_BUILD_DATE=${BUILD_DATE} \
    JULIA_NUM_THREADS=auto \
    JULIA_CPU_TARGET="generic;sandybridge,-xsaveopt,clone_all;haswell,-rdrnd,base(1);x86-64-v4,-rdrnd,base(1)" \
    CODE_EXTENSIONSDIR=/home/jovyan/.local/share/code-server/extensions \
    JUPYTER_PREFER_ENV_PATH=1 \
    GKSwstype=100

USER root
RUN test "${TARGETARCH}" = amd64 || { echo 'This image supports linux/amd64 only.' >&2; exit 1; }
COPY Project.toml LocalPreferences.toml /opt/hydra-build/
COPY scripts/install-julia.jl scripts/export-metadata.py /opt/hydra-build/
RUN chown -R "${NB_UID}:${NB_GID}" /opt/hydra-build \
    && mkdir -p /usr/local/share/hydra-jupyterhub \
    && chown "${NB_UID}:${NB_GID}" /usr/local/share/hydra-jupyterhub

USER ${NB_UID}
# Only UI integration is added; no tutorial requirements, Qiskit, or second Python.
# Freeze the upstream environment so VS Code doesn't silently upgrade its stack.
RUN mamba install --yes --freeze-installed jupyter-vscode-proxy code-server \
    && mamba clean --all --yes \
    && fix-permissions "${CONDA_DIR}"
RUN JULIA_NUM_PRECOMPILE_TASKS=2 julia --threads=2 --startup-file=no /opt/hydra-build/install-julia.jl \
    && fix-permissions "${JULIA_PKGDIR}" "${CONDA_DIR}/share/jupyter" \
    && python /opt/hydra-build/export-metadata.py

USER root
RUN rm -rf /opt/hydra-build
USER ${NB_UID}
WORKDIR /home/${NB_USER}

LABEL org.opencontainers.image.title="hydra-jupyterhub" \
    org.opencontainers.image.description="Standalone amd64 Julia notebook with CUDA 12.9 preferences and VS Code integration" \
    org.opencontainers.image.source="https://github.com/ltpn/hydra-jupyterhub" \
    org.opencontainers.image.licenses="MIT" \
    org.ltpn.hydra-jupyterhub.metadata="/usr/local/share/hydra-jupyterhub/versions.json"
