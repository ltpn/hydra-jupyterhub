#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
mkdir -p artifacts
revision="$(git rev-parse HEAD)"
created="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
build_id="${GITHUB_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}-${GITHUB_RUN_ATTEMPT:-local}"
include_matlab="${HYDRA_INCLUDE_MATLAB:-1}"
daemon_builder="$(docker context show)"
if [[ "$include_matlab" == 1 ]]; then
  matlab_image="${MATLAB_IMAGE:-$(sed -n 's/^ARG MATLAB_IMAGE=//p' Dockerfile.matlab)}"
  # Fail before expensive Julia compilation if the required upstream release
  # has not been published. Never silently substitute an older MATLAB release.
  docker buildx imagetools inspect "$matlab_image" >/dev/null
fi

# Fresh Julia resolution on EVERY build, including scheduled builds of the same
# commit. A committed Manifest or a cached package-install layer defeats that.
docker build --builder "$daemon_builder" --platform linux/amd64 --pull --no-cache \
  --build-arg SOURCE_REVISION="$revision" --build-arg BUILD_DATE="$created" \
  -t hydra-jupyterhub:build .

# Export before smoke tests so failed builds retain useful resolution evidence.
container="$(docker create --platform linux/amd64 hydra-jupyterhub:build)"
trap 'docker rm "$container" >/dev/null' EXIT
docker cp "$container:/usr/local/share/hydra-jupyterhub/." artifacts/
docker rm "$container" >/dev/null
trap - EXIT

docker run --rm --platform linux/amd64 --memory=6g --cpus=2 \
  -e JULIA_NUM_THREADS=2 --entrypoint python \
  -v "$PWD/tests:/tests:ro" hydra-jupyterhub:build /tests/smoke.py

if [[ "$include_matlab" == 1 ]]; then
  bash scripts/add-matlab.sh
  container="$(docker create --platform linux/amd64 hydra-jupyterhub:build)"
  trap 'docker rm "$container" >/dev/null' EXIT
  docker cp "$container:/usr/local/share/hydra-jupyterhub/." artifacts/
  docker rm "$container" >/dev/null
  trap - EXIT
fi

# Repeat with an empty, mounted notebook home, like a new JupyterHub PVC.
home_volume="$(docker volume create --label org.ltpn.hydra-jupyterhub.test=true)"
trap 'docker volume rm "$home_volume" >/dev/null' EXIT
docker run --rm --platform linux/amd64 --memory=6g --cpus=2 \
  -e JULIA_NUM_THREADS=2 --entrypoint python \
  -v "$home_volume:/home/jovyan" -v "$PWD/tests:/tests:ro" \
  hydra-jupyterhub:build /tests/smoke.py
if [[ "$include_matlab" == 1 ]]; then
  docker run --rm --platform linux/amd64 --entrypoint python \
    -v "$home_volume:/home/jovyan" -v "$PWD/tests:/tests:ro" \
    hydra-jupyterhub:build /tests/matlab_smoke.py
fi
# Real local extension installation/settings survive replacing the container.
for mode in install check; do
  docker run --rm --platform linux/amd64 --entrypoint python \
    -v "$home_volume:/home/jovyan" -v "$PWD/tests:/tests:ro" \
    hydra-jupyterhub:build /tests/vscode_persistence.py "$mode"
done
docker volume rm "$home_volume" >/dev/null
trap - EXIT

python3 scripts/image-tags.py artifacts/versions.json --build-id "$build_id" --output artifacts
docker build --builder "$daemon_builder" --platform linux/amd64 --pull=false --network=none \
  -f artifacts/Dockerfile.metadata -t hydra-jupyterhub:tested .
docker inspect hydra-jupyterhub:tested --format '{{.Architecture}}' | grep -qx amd64
printf 'Tested image: hydra-jupyterhub:tested; resolved metadata and tags: artifacts/\n'
