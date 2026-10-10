"""Download Microsoft's icon with fallbacks and configure the existing proxy."""
import os
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REFS = ("HEAD", "959031245ebb1fe077e0d512e1397c0ae82006e4")
ICON_PATH = "src/vs/sessions/browser/media/vscode-icon.svg"
RAW_ROOT = "https://raw.githubusercontent.com/microsoft/vscode"
BEGIN = "# BEGIN Hydra VS Code launcher"
END = "# END Hydra VS Code launcher"


def fetch(url):
    with urllib.request.urlopen(url, timeout=8) as response:
        data = response.read(256 * 1024 + 1)
    if len(data) > 256 * 1024:
        raise ValueError("Icon or license response too large")
    return data


def download_icon(directory, get=fetch):
    directory.mkdir(parents=True, exist_ok=True)
    icon = directory / "vscode-icon.svg"
    license_file = directory / "VSCODE-ICON-LICENSE.txt"
    source_file = directory / "vscode-icon-source.txt"
    for ref in REFS:
        source = f"{RAW_ROOT}/{ref}/{ICON_PATH}"
        try:
            data = get(source)
            if ET.fromstring(data).tag != "{http://www.w3.org/2000/svg}svg":
                raise ValueError("Response is not an SVG")
            license_data = get(f"{RAW_ROOT}/{ref}/LICENSE.txt")
            if not license_data.decode("utf-8-sig").startswith("MIT License"):
                raise ValueError("Expected the upstream MIT license")
        except (OSError, urllib.error.URLError, ValueError, ET.ParseError) as error:
            if isinstance(error, urllib.error.HTTPError):
                error.close()
            print(f"VS Code icon unavailable at {ref}: {type(error).__name__}")
            continue
        icon.write_bytes(data)
        license_file.write_bytes(license_data)
        source_file.write_text(source + "\n")
        print(f"VS Code icon downloaded: {source}")
        return icon
    # Only our generated files are removed; the plugin's original SVG is untouched.
    for path in (icon, license_file, source_file):
        path.unlink(missing_ok=True)
    print("Using the plugin's default VS Code icon")
    return None


def configure(config_path, icon):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    text = config_path.read_text() if config_path.exists() else ""
    if BEGIN in text and END in text:
        start = text.index(BEGIN)
        stop = text.index(END, start) + len(END)
        text = text[:start] + text[stop:]
    lines = [BEGIN,
             "import jupyter_vscode_proxy as _hydra_vscode_proxy",
             "if not hasattr(_hydra_vscode_proxy, '_hydra_original_setup_vscode'):",
             "    _hydra_vscode_proxy._hydra_original_setup_vscode = _hydra_vscode_proxy.setup_vscode",
             "def _hydra_setup_vscode():",
             "    config = _hydra_vscode_proxy._hydra_original_setup_vscode()",
             "    config['launcher_entry']['title'] = 'VS Code'"]
    if icon:
        lines.append(f"    config['launcher_entry']['icon_path'] = {str(icon)!r}")
    # ServerProxy.servers adds a second process instead of replacing entry points.
    lines += ["    return config",
              "_hydra_vscode_proxy.setup_vscode = _hydra_setup_vscode", END]
    config_path.write_text(text.rstrip() + "\n\n" + "\n".join(lines) + "\n")


if __name__ == "__main__":
    metadata = Path("/usr/local/share/hydra-jupyterhub")
    icon = download_icon(metadata)
    config = Path(os.environ["CONDA_DIR"]) / "etc/jupyter/jupyter_server_config.py"
    configure(config, icon)
