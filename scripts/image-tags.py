"""Derive registry tags/labels from the built image's resolved metadata."""
import argparse
import json
import re
from pathlib import Path


def safe_tag(value):
    result = re.sub(r"[^a-zA-Z0-9_.-]", "_", value)
    if not result or len(result) > 128 or result[0] in ".-":
        raise ValueError(f"Invalid container tag: {value!r}")
    return result


def derive(metadata, build_id):
    tags = {"latest", "amd64", safe_tag(f"build-{build_id}"),
            safe_tag(f"sha-{metadata['image']['source_revision'][:12]}-{build_id}")}
    versions = {"julia": metadata["julia"]["version"], "python": metadata["python"]["version"],
                "ubuntu": metadata["os"]["version_id"], **metadata["tools"]}
    for tag, package in {"hub": "jupyterhub", "lab": "jupyterlab", "notebook": "notebook"}.items():
        versions[tag] = metadata["python"]["packages"][package]
    for name, version in versions.items():
        tags.add(safe_tag(f"{name}-{version}"))
    tags.add(safe_tag("python-" + ".".join(versions["python"].split(".")[:2])))
    for name, version in metadata["julia"]["direct_packages"].items():
        if version:
            tags.add(safe_tag(f"{name.lower().replace('_', '-')}-{version}"))
    tags.add(safe_tag(f"cuda-runtime-{metadata['julia']['cuda_runtime']}"))
    labels = {
        "org.opencontainers.image.source": "https://github.com/ltpn/hydra-jupyterhub",
        "org.opencontainers.image.revision": metadata["image"]["source_revision"],
        "org.opencontainers.image.created": metadata["image"]["created"],
        "org.opencontainers.image.base.name": metadata["image"]["base_image"].split("@")[0],
        "org.opencontainers.image.base.digest": metadata["image"]["base_image"].split("@")[1],
        "org.ltpn.hydra-jupyterhub.julia.version": versions["julia"],
        "org.ltpn.hydra-jupyterhub.julia.direct-versions": json.dumps(metadata["julia"]["direct_packages"], sort_keys=True),
        "org.ltpn.hydra-jupyterhub.julia.manifest.sha256": metadata["manifest_sha256"],
        "org.ltpn.hydra-jupyterhub.cuda.runtime": metadata["julia"]["cuda_runtime"],
        "org.ltpn.hydra-jupyterhub.software-versions": json.dumps(versions, sort_keys=True),
    }
    return sorted(tags), labels


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata", type=Path)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tags, labels = derive(json.loads(args.metadata.read_text()), args.build_id)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "tags.txt").write_text("\n".join(tags) + "\n")
    (args.output / "labels.json").write_text(json.dumps(labels, indent=2, sort_keys=True) + "\n")
    # A metadata-only layer: no second package resolution or recompilation.
    lines = ["FROM hydra-jupyterhub:build"]
    lines += [f"LABEL {key}={json.dumps(value)}" for key, value in sorted(labels.items())]
    (args.output / "Dockerfile.metadata").write_text("\n".join(lines) + "\n")
