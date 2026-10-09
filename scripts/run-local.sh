#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
mode="${1:-hub}"
image="${IMAGE:-ghcr.io/ltpn/hydra-jupyterhub:latest}"
port="${PORT:-8000}"
volume="${VOLUME:-hydra-jupyterhub-local-home}"
container="${CONTAINER:-hydra-jupyterhub-local-$mode}"

case "$mode" in
  hub)
    url="http://localhost:$port/jupyter/hub/"
    command=(bash -c 'mamba install --yes --freeze-installed configurable-http-proxy && exec jupyterhub -f /tmp/local-hub.py')
    internal_port=8000
    ;;
  lab)
    url="http://localhost:$port/lab"
    command=(start-notebook.py)
    internal_port=8888
    ;;
  *) echo "Usage: bash scripts/run-local.sh [hub|lab]" >&2; exit 2 ;;
esac

if docker container inspect "$container" >/dev/null 2>&1; then
  echo "Container already exists: $container. Restart with: docker start -ai $container" >&2
  exit 1
fi
echo "$url"
if [[ "$mode" == hub ]]; then echo 'Test login: jovyan; any password.'; fi
echo "Home volume: $volume; stop with Ctrl-C, restart with docker start -ai $container"
docker_args=(run -it --name "$container" --platform linux/amd64 --pull "${PULL_POLICY:-always}" \
  --memory="${MEMORY:-8g}" --cpus="${CPUS:-4}" \
  -p "127.0.0.1:$port:$internal_port" -e JULIA_NUM_THREADS=2 \
  -v "$volume:/home/jovyan")
if [[ "$mode" == hub ]]; then
  docker_args+=(-v "$PWD/scripts/local-hub.py:/tmp/local-hub.py:ro")
fi
docker "${docker_args[@]}" "$image" "${command[@]}"
