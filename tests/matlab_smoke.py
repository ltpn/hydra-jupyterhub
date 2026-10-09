"""License-free MATLAB integration checks; not a licensed MATLAB execution test."""
import json
import os
import shutil
import sys
import subprocess
from pathlib import Path

from jupyter_client.kernelspec import KernelSpecManager
import jupyter_matlab_proxy

root = Path(os.environ["MATLAB_ROOT"])
metadata = json.loads(Path("/usr/local/share/hydra-jupyterhub/versions.json").read_text())
assert metadata["matlab"]["release"] == root.name
assert metadata["matlab"]["version"]
products = metadata["matlab"]["installed_products"]
for product in ("MATLAB", "Symbolic Math Toolbox", "Deep Learning Toolbox",
                "Parallel Computing Toolbox", "Deep Learning Toolbox Model for ResNet-50 Network"):
    assert product in products, product
assert metadata["python"]["packages"].get("jupyter-matlab-proxy")
assert os.environ["MWI_CUSTOM_MATLAB_ROOT"] == str(root)
assert Path(shutil.which("matlab")).resolve() == root / "bin/matlab"
assert os.access(root / "bin/matlab", os.X_OK)
assert shutil.which("Xvfb") and shutil.which("xauth")
assert Path(os.environ["MATHWORKS_SERVICE_HOST_MANAGED_INSTALL_ROOT"]).is_dir()
assert Path(metadata["matlab"]["support_packages_root"]).is_dir()
# Exercise the same startup hook twice, including when a PVC hides image home.
hook = "/usr/local/bin/before-notebook.d/20-matlab-support-packages.sh"
for _ in range(2):
    subprocess.run(["bash", hook], check=True)
user_root = Path.home() / "Documents/MATLAB/SupportPackages" / root.name
assert user_root.resolve() == Path(metadata["matlab"]["support_packages_root"]).resolve()
spec = KernelSpecManager().get_kernel_spec("jupyter_matlab_kernel")
assert spec.resource_dir.startswith("/opt/conda/share/jupyter/kernels/"), spec.resource_dir
assert Path(spec.argv[0]).resolve() == Path(sys.executable).resolve(), spec.argv
assert spec.argv[1:3] == ["-m", "jupyter_matlab_kernel"], spec.argv
proxy = jupyter_matlab_proxy.setup_matlab()
assert proxy["absolute_url"]
assert shutil.which(proxy["command"][0])
print("MATLAB_INTEGRATION_CHECKS_PASSED", metadata["matlab"]["release"])
print("Licensed MATLAB execution and browser login still require a runtime license.")
