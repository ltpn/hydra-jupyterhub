#!/usr/bin/env bash
# This is sourced by the upstream before-notebook hook. Keep shell options and
# variables in a subshell, and initialize the mounted home as the notebook user.
(
  set -euo pipefail
  release="${MATLAB_ROOT##*/}"
  bundled_root="/home/matlab/Documents/MATLAB/SupportPackages/$release"
  user_parent="${HOME}/Documents/MATLAB/SupportPackages"
  user_root="$user_parent/$release"
  if [[ -d "$bundled_root" && ! -e "$user_root" && ! -L "$user_root" ]]; then
    mkdir -p "$user_parent"
    ln -s "$bundled_root" "$user_root"
  fi
)
