"""Derive registry tags/labels from the built image's resolved metadata."""
import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path


def safe_tag(value):
    result = re.sub(r"[^a-zA-Z0-9_.-]", "_", value)
    if not result or len(result) > 128 or result[0] in ".-":
        raise ValueError(f"Invalid container tag: {value!r}")
    return result


def matching_base_tags(tags, digests):
    return sorted({row["name"] for row in tags
                   if row.get("manifest_digest") in digests
                   and not row["name"].startswith(("aarch64-", "arm64-"))})


def upstream_tags(base_image):
    """Quay aliases for this exact multiarch base or its Linux amd64 child."""
    name, digest = base_image.split("@", 1)
    if not name.startswith("quay.io/"):
        raise ValueError("Upstream tag discovery expects a Quay base image")
    repository = name.removeprefix("quay.io/").rsplit(":", 1)[0]
    endpoint = f"https://quay.io/api/v1/repository/{repository}"

    def get_json(url):
        with urllib.request.urlopen(url, timeout=60) as response:
            return json.load(response)

    manifest = json.loads(get_json(f"{endpoint}/manifest/{digest}")["manifest_data"])
    digests = {digest}
    digests.update(row["digest"] for row in manifest.get("manifests", [])
                   if row.get("platform", {}).get("os") == "linux"
                   and row["platform"].get("architecture") == "amd64")
    aliases = set()
    page = 1
    while True:
        query = urllib.parse.urlencode({"limit": 100, "page": page, "onlyActiveTags": "true"})
        data = get_json(f"{endpoint}/tag/?{query}")
        aliases.update(matching_base_tags(data["tags"], digests))
        if not data.get("has_additional"):
            break
        page += 1
    return sorted(aliases)


def derive(metadata, build_id, base_tags=()):
    tags = {"latest", "amd64", safe_tag(f"build-{build_id}"),
            safe_tag(f"sha-{metadata['image']['source_revision'][:12]}-{build_id}")}
    versions = {"julia": metadata["julia"]["version"], "python": metadata["python"]["version"],
                "ubuntu": metadata["os"]["version_id"], **metadata["tools"]}
    for tag, package in {"hub": "jupyterhub", "lab": "jupyterlab", "notebook": "notebook"}.items():
        versions[tag] = metadata["python"]["packages"][package]
    for name, version in versions.items():
        tags.add(safe_tag(f"{name}-{version}"))
    if metadata.get("matlab"):
        versions["matlab"] = metadata["matlab"]["release"]
        tags.add(safe_tag(f"matlab-{metadata['matlab']['release']}"))
        tags.add(safe_tag(f"matlab-{metadata['matlab']['version']}"))
    tags.add(safe_tag("python-" + ".".join(versions["python"].split(".")[:2])))
    for name, version in metadata["julia"]["direct_packages"].items():
        if version:
            tags.add(safe_tag(f"{name.lower().replace('_', '-')}-{version}"))
    tags.add(safe_tag(f"cuda-runtime-{metadata['julia']['cuda_runtime']}"))
    for tag in base_tags:
        if safe_tag(tag) != tag:
            raise ValueError(f"Invalid upstream tag: {tag!r}")
        tags.add(tag)
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
    if metadata.get("matlab"):
        labels["org.ltpn.hydra-jupyterhub.matlab.source-image"] = metadata["matlab"]["source_image"]
        labels["org.ltpn.hydra-jupyterhub.matlab.release"] = metadata["matlab"]["release"]
        labels["org.ltpn.hydra-jupyterhub.matlab.version"] = metadata["matlab"]["version"]
    if base_tags:
        labels["org.ltpn.hydra-jupyterhub.base.tags"] = json.dumps(sorted(base_tags))
    return sorted(tags), labels


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("metadata", type=Path)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--upstream", action="store_true", help="Preserve matching Quay base/amd64 aliases")
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text())
    base_tags = upstream_tags(metadata["image"]["base_image"]) if args.upstream else []
    tags, labels = derive(metadata, args.build_id, base_tags)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "tags.txt").write_text("\n".join(tags) + "\n")
    (args.output / "labels.json").write_text(json.dumps(labels, indent=2, sort_keys=True) + "\n")
    if args.upstream:
        (args.output / "upstream-tags.json").write_text(json.dumps(base_tags, indent=2) + "\n")
    # A metadata-only layer: no second package resolution or recompilation.
    lines = ["FROM hydra-jupyterhub:build"]
    lines += [f"LABEL {key}={json.dumps(value)}" for key, value in sorted(labels.items())]
    (args.output / "Dockerfile.metadata").write_text("\n".join(lines) + "\n")
