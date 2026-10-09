# syntax=docker/dockerfile:1
# Reuse LTPN's installation, including every toolbox shipped in that image.
# This layer is built after the standalone notebook has passed its own tests.
ARG MATLAB_IMAGE=ghcr.io/ltpn/matlab:R2026b
ARG NOTEBOOK_IMAGE=hydra-jupyterhub:build
FROM ${MATLAB_IMAGE} AS matlab_installation
FROM ${NOTEBOOK_IMAGE}
ARG MATLAB_IMAGE
ARG MATLAB_RELEASE=R2026b
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV HYDRA_MATLAB_IMAGE=${MATLAB_IMAGE} \
    MATLAB_ROOT=/opt/matlab/${MATLAB_RELEASE} \
    MWI_CUSTOM_MATLAB_ROOT=/opt/matlab/${MATLAB_RELEASE} \
    MATHWORKS_SERVICE_HOST_MANAGED_INSTALL_ROOT=/opt/MathWorks/ServiceHost \
    MW_SERVICEHOST_USE_HOSTNAME_FOR_PERSISTENCE=false

USER root
# Copy the installation only, not the MATLAB image's user, entrypoint, or license.
COPY --from=matlab_installation /opt/matlab/ /opt/matlab/
# The deep-learning image installs support packages outside the MATLAB root.
# Keep their original absolute paths and managed Service Host for online login.
COPY --from=matlab_installation /home/matlab/Documents/MATLAB/SupportPackages/ /home/matlab/Documents/MATLAB/SupportPackages/
COPY --from=matlab_installation /opt/MathWorks/ServiceHost/ /opt/MathWorks/ServiceHost/
COPY MATLAB-DEPS-LICENSE.md /usr/local/share/hydra-jupyterhub/MATLAB-DEPS-LICENSE.md
COPY matlab-base-dependencies.txt /tmp/matlab-base-dependencies.txt
RUN test -x "${MATLAB_ROOT}/bin/matlab" \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive xargs -a /tmp/matlab-base-dependencies.txt \
       apt-get install --yes --no-install-recommends xvfb xauth \
    && rm -rf /var/lib/apt/lists/* /tmp/matlab-base-dependencies.txt \
    && ln -s "${MATLAB_ROOT}/bin/matlab" /usr/local/bin/matlab

USER ${NB_UID}
# Keep every installed Python distribution at its current version. Pip may add
# proxy dependencies but must fail rather than replace the base Python stack.
RUN python -c 'import importlib.metadata as m; from pathlib import Path; Path("/tmp/hydra-python-constraints.txt").write_text("\n".join(d.metadata["Name"]+"=="+d.version for d in m.distributions() if d.metadata["Name"]))' \
    && python -m pip install --no-cache-dir --constraint /tmp/hydra-python-constraints.txt jupyter-matlab-proxy \
    && install-matlab-kernelspec \
    && python -m pip check \
    && rm /tmp/hydra-python-constraints.txt \
    && fix-permissions "${CONDA_DIR}"

COPY scripts/export-metadata.py /tmp/hydra-export-metadata.py
RUN python /tmp/hydra-export-metadata.py
USER root
RUN rm /tmp/hydra-export-metadata.py
USER ${NB_UID}
WORKDIR /home/${NB_USER}
LABEL org.opencontainers.image.description="Standalone amd64 Julia notebook with CUDA 12.9, VS Code, and MATLAB integration"
