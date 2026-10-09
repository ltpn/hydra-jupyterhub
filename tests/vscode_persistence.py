"""Install a tiny local VSIX, then verify it in a recreated container/home."""
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

extensions = Path(os.environ["CODE_EXTENSIONSDIR"])
settings = Path.home() / ".local/share/code-server/User/settings.json"
extension_id = "hydra-ci.persistence-test"
command = ["code-server", "--disable-telemetry", "--extensions-dir", str(extensions)]

if sys.argv[1] == "install":
    with tempfile.TemporaryDirectory() as directory:
        vsix = Path(directory) / "persistence-test.vsix"
        with zipfile.ZipFile(vsix, "w") as archive:
            archive.writestr("[Content_Types].xml", '''<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="json" ContentType="application/json"/>
<Default Extension="vsixmanifest" ContentType="text/xml"/>
</Types>''')
            archive.writestr("extension.vsixmanifest", '''<?xml version="1.0"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
<Metadata><Identity Language="en-US" Id="persistence-test" Publisher="hydra-ci" Version="0.0.1"/>
<DisplayName>Hydra CI persistence test</DisplayName><Description>Local test fixture</Description></Metadata>
<Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation>
<Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets>
</PackageManifest>''')
            archive.writestr("extension/package.json", json.dumps({
                "name": "persistence-test", "displayName": "Hydra CI persistence test",
                "publisher": "hydra-ci", "version": "0.0.1", "engines": {"vscode": "^1.90.0"},
                "contributes": {},
            }))
        subprocess.run(command + ["--install-extension", str(vsix)], check=True, timeout=120)
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({"editor.fontSize": 17}))
elif sys.argv[1] != "check":
    raise ValueError("Expected install or check")

installed = subprocess.check_output(command + ["--list-extensions"], text=True, timeout=120)
assert extension_id in installed.splitlines(), installed
assert json.loads(settings.read_text())["editor.fontSize"] == 17
assert extensions.is_relative_to(Path.home()), extensions
print("VSCODE_PERSISTENCE_OK", sys.argv[1], extensions)
