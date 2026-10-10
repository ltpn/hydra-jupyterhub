#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
mkdir -p artifacts
revision="$(git rev-parse HEAD)"
created="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
build_id="${GITHUB_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}-${GITHUB_RUN_ATTEMPT:-local}"
daemon_builder="$(docker context show)"
matlab_image="${MATLAB_IMAGE:-$(sed -n 's/^ARG MATLAB_IMAGE=//p' Dockerfile)}"
matlab_release="${MATLAB_RELEASE:-$(sed -n 's/^ARG MATLAB_RELEASE=//p' Dockerfile)}"
matlab_digest="$(docker buildx imagetools inspect "$matlab_image" --format '{{.Manifest.Digest}}')"
matlab_snapshot="${matlab_image%@*}@${matlab_digest}"

# Fresh Julia resolution on EVERY build, including scheduled builds of the same
# commit. A committed Manifest or a cached package-install layer defeats that.
docker build --builder "$daemon_builder" --platform linux/amd64 --pull --no-cache \
  --build-arg SOURCE_REVISION="$revision" --build-arg BUILD_DATE="$created" \
  --build-arg MATLAB_IMAGE="$matlab_snapshot" --build-arg MATLAB_RELEASE="$matlab_release" \
  --build-arg MPM_GOGC="${MPM_GOGC:-100}" \
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

docker run --rm --platform linux/amd64 --entrypoint python \
  -v "$PWD/tests:/tests:ro" hydra-jupyterhub:build /tests/matlab_smoke.py

# Repeat with an empty, mounted notebook home, like a new JupyterHub PVC.
home_volume="$(docker volume create --label org.ltpn.hydra-jupyterhub.test=true)"
trap 'docker volume rm "$home_volume" >/dev/null' EXIT
docker run --rm --platform linux/amd64 --memory=6g --cpus=2 \
  -e JULIA_NUM_THREADS=2 --entrypoint python \
  -v "$home_volume:/home/jovyan" -v "$PWD/tests:/tests:ro" \
  hydra-jupyterhub:build /tests/smoke.py
docker run --rm --platform linux/amd64 --entrypoint python \
  -v "$home_volume:/home/jovyan" -v "$PWD/tests:/tests:ro" \
  hydra-jupyterhub:build /tests/matlab_smoke.py
# Real local extension installation/settings survive replacing the container.
for mode in install check; do
  docker run --rm --platform linux/amd64 --entrypoint python \
    -v "$home_volume:/home/jovyan" -v "$PWD/tests:/tests:ro" \
    hydra-jupyterhub:build /tests/vscode_persistence.py "$mode"
done
docker volume rm "$home_volume" >/dev/null
trap - EXIT

python3 scripts/image-tags.py artifacts/versions.json --build-id "$build_id" --upstream --output artifacts
docker build --builder "$daemon_builder" --platform linux/amd64 --pull=false --network=none \
  -f artifacts/Dockerfile.metadata -t hydra-jupyterhub:tested .
docker inspect hydra-jupyterhub:tested --format '{{.Architecture}}' | grep -qx amd64
printf 'Tested image: hydra-jupyterhub:tested; resolved metadata and tags: artifacts/\n'
