"""Export actual installed versions using Python/Julia stdlib metadata only."""
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path
from runtime_versions import parse_tool_version

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
python_packages = {re.sub(r"[-_.]+", "-", dist.metadata["Name"]).lower(): dist.version
                   for dist in importlib.metadata.distributions() if dist.metadata["Name"]}
os_info = {}
for line in Path("/etc/os-release").read_text().splitlines():
    if "=" in line:
        key, value = line.split("=", 1)
        os_info[key.lower()] = value.strip('"')
tools = {}
for name, command in {"code-server": ["code-server", "--version"],
                      "conda": ["conda", "--version"], "mamba": ["mamba", "--version"],
                      "btop": ["btop", "--version"]}.items():
    tools[name] = parse_tool_version(subprocess.check_output(command, text=True, stderr=subprocess.PIPE))
base_record = ROOT / "base-image.txt"
base_image = base_record.read_text().strip() if base_record.is_file() else os.environ["HYDRA_BASE_IMAGE"]
metadata = {
    "schema_version": 1,
    "image": {"architecture": platform.machine(), "base_image": base_image,
              "source_revision": os.environ["HYDRA_SOURCE_REVISION"], "created": os.environ["HYDRA_BUILD_DATE"]},
    "julia": julia,
    "python": {"version": platform.python_version(), "packages": python_packages},
    "tools": tools,
    "os": os_info,
    "manifest_sha256": hashlib.sha256((ROOT / "Manifest.toml").read_bytes()).hexdigest(),
}
if os.environ.get("MATLAB_ROOT"):
    matlab_root = Path(os.environ["MATLAB_ROOT"])
    version_info = matlab_root / "VersionInfo.xml"
    version_xml = ET.parse(version_info).getroot()
    release = version_xml.findtext("release")
    version = version_xml.findtext("version")
    if not release or not version or matlab_root.name != release:
        raise RuntimeError(f"Unexpected MATLAB VersionInfo.xml in {matlab_root}")
    support_root = Path("/home/matlab/Documents/MATLAB/SupportPackages") / release
    products = {}
    for catalog in (matlab_root / "appdata/products", support_root / "appdata/products"):
        for product_file in sorted(catalog.glob("*.xml")):
            product_xml = ET.parse(product_file).getroot()
            name = product_xml.findtext("productName")
            product_version = product_xml.findtext("productVersion")
            if name and product_version:
                products[name] = {"version": product_version,
                                  "type": product_xml.findtext("productType"),
                                  "release": product_xml.findtext("releaseFamily")}
    metadata["matlab"] = {
        "release": release,
        "version": version,
        "root": str(matlab_root),
        "source_image": os.environ["HYDRA_MATLAB_IMAGE"],
        "support_packages_root": str(support_root),
        "installed_products": products,
        "license_bundled": False,
    }
    (ROOT / "MATLAB-VersionInfo.xml").write_bytes(version_info.read_bytes())
(ROOT / "versions.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
print(json.dumps({"julia": julia["version"], "direct_packages": direct,
                  "manifest_sha256": metadata["manifest_sha256"]}, indent=2))
