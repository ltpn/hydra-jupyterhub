#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
matlab_release="${MATLAB_RELEASE:-$(sed -n 's/^ARG MATLAB_RELEASE=//p' Dockerfile.matlab)}"
matlab_image="${MATLAB_IMAGE:-$(sed -n 's/^ARG MATLAB_IMAGE=//p' Dockerfile.matlab)}"
# Resolve provenance before copying, rather than recording only a moving tag.
matlab_digest="$(docker buildx imagetools inspect "$matlab_image" --format '{{.Manifest.Digest}}')"
matlab_snapshot="${matlab_image%@*}@${matlab_digest}"
docker tag hydra-jupyterhub:build hydra-jupyterhub:notebook
docker build --builder default --platform linux/amd64 --pull=false --no-cache \
  --build-arg MATLAB_IMAGE="$matlab_snapshot" --build-arg MATLAB_RELEASE="$matlab_release" \
  -f Dockerfile.matlab -t hydra-jupyterhub:matlab .
docker tag hydra-jupyterhub:matlab hydra-jupyterhub:build
docker run --rm --platform linux/amd64 --entrypoint python \
  -v "$PWD/tests:/tests:ro" hydra-jupyterhub:build /tests/matlab_smoke.py
