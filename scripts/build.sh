#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
mkdir -p artifacts
revision="$(git rev-parse HEAD)"
created="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
build_id="${GITHUB_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}-${GITHUB_RUN_ATTEMPT:-local}"

# Fresh Julia resolution on EVERY build, including scheduled builds of the same
# commit. A committed Manifest or a cached package-install layer defeats that.
docker build --platform linux/amd64 --pull --no-cache \
  --build-arg SOURCE_REVISION="$revision" --build-arg BUILD_DATE="$created" \
  -t hydra-jupyterhub:build .

docker run --rm --platform linux/amd64 --memory=6g --cpus=2 \
  -e JULIA_NUM_THREADS=2 --entrypoint python \
  -v "$PWD/tests:/tests:ro" hydra-jupyterhub:build /tests/smoke.py

# Repeat with an empty, mounted notebook home, like a new JupyterHub PVC.
home_volume="$(docker volume create --label org.ltpn.hydra-jupyterhub.test=true)"
trap 'docker volume rm "$home_volume" >/dev/null' EXIT
docker run --rm --platform linux/amd64 --memory=6g --cpus=2 \
  -e JULIA_NUM_THREADS=2 --entrypoint python \
  -v "$home_volume:/home/jovyan" -v "$PWD/tests:/tests:ro" \
  hydra-jupyterhub:build /tests/smoke.py
# Real local extension installation/settings survive replacing the container.
for mode in install check; do
  docker run --rm --platform linux/amd64 --entrypoint python \
    -v "$home_volume:/home/jovyan" -v "$PWD/tests:/tests:ro" \
    hydra-jupyterhub:build /tests/vscode_persistence.py "$mode"
done
docker volume rm "$home_volume" >/dev/null
trap - EXIT

container="$(docker create --platform linux/amd64 hydra-jupyterhub:build)"
trap 'docker rm "$container" >/dev/null' EXIT
docker cp "$container:/usr/local/share/hydra-jupyterhub/." artifacts/
docker rm "$container" >/dev/null
trap - EXIT
python3 scripts/image-tags.py artifacts/versions.json --build-id "$build_id" --output artifacts
docker build --platform linux/amd64 --pull=false --network=none \
  -f artifacts/Dockerfile.metadata -t hydra-jupyterhub:tested .
docker inspect hydra-jupyterhub:tested --format '{{.Architecture}}' | grep -qx amd64
printf 'Tested image: hydra-jupyterhub:tested; resolved metadata and tags: artifacts/\n'
