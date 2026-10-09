"""Export actual installed versions using Python/Julia stdlib metadata only."""
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path("/usr/local/share/hydra-jupyterhub")
project = tomllib.loads((ROOT / "Project.toml").read_text())
manifest = tomllib.loads((ROOT / "Manifest.toml").read_text())
preferences = tomllib.loads((ROOT / "LocalPreferences.toml").read_text())
julia = tomllib.loads((ROOT / "julia-info.toml").read_text())
packages = []
direct = {}
for name, entries in sorted(manifest["deps"].items()):
    for entry in entries:
        row = {"name": name, "uuid": entry["uuid"], "version": entry.get("version"),
               "direct": project.get("deps", {}).get(name) == entry["uuid"]}
        packages.append(row)
        if row["direct"]:
            direct[name] = row["version"]
julia.update(direct_packages=direct, packages=packages,
             cuda_runtime=preferences["CUDA_Runtime_jll"]["version"],
             cuda_compiler=preferences["CUDA_Compiler_jll"]["version"])
python_packages = {dist.metadata["Name"].lower(): dist.version
                   for dist in importlib.metadata.distributions() if dist.metadata["Name"]}
os_info = {}
for line in Path("/etc/os-release").read_text().splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        os_info[key.lower()] = value.strip('"')
tools = {}
for name, command in {"code-server": ["code-server", "--version"],
                      "conda": ["conda", "--version"], "mamba": ["mamba", "--version"]}.items():
    tools[name] = subprocess.check_output(command, text=True).splitlines()[0].split()[-1 if name == "conda" else 0]
metadata = {
    "schema_version": 1,
    "image": {"architecture": platform.machine(), "base_image": os.environ["HYDRA_BASE_IMAGE"],
              "source_revision": os.environ["HYDRA_SOURCE_REVISION"], "created": os.environ["HYDRA_BUILD_DATE"]},
    "julia": julia,
    "python": {"version": platform.python_version(), "packages": python_packages},
    "tools": tools,
    "os": os_info,
    "manifest_sha256": hashlib.sha256((ROOT / "Manifest.toml").read_bytes()).hexdigest(),
}
(ROOT / "versions.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
print(json.dumps({"julia": julia["version"], "direct_packages": direct,
                  "manifest_sha256": metadata["manifest_sha256"]}, indent=2))
