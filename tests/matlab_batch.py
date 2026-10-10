"""Opt-in local licensed check. Mount a token read-only; never upload it to CI."""
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

token_file = Path("/run/secrets/matlab-batch-token")
if not token_file.is_file():
    raise SystemExit("Local token mount required. This test is not run in public CI.")
with tempfile.TemporaryDirectory(prefix="hydra-matlab-batch-") as directory:
    executable = Path(directory) / "matlab-batch"
    urllib.request.urlretrieve(
        "https://ssd.mathworks.com/supportfiles/ci/matlab-batch/v1/glnxa64/matlab-batch",
        executable,
    )
    executable.chmod(0o700)
    # Read only within the disposable local container. Do not set a Docker
    # container environment variable or pass the token as a process argument.
    environment = os.environ.copy()
    environment["MLM_LICENSE_TOKEN"] = token_file.read_text().strip()
    statement = """
        try;
        assert(1+1==2);
        fprintf('HYDRA_MATLAB_STAGE arithmetic\\n');
        assert(double(sym(1)+sym(1))==2);
        fprintf('HYDRA_MATLAB_STAGE symbolic\\n');
        x=(1:5)'; f=fit(x,2*x+1,'poly1');
        assert(max(abs(coeffvalues(f)-[2 1]))<1e-10);
        fprintf('HYDRA_MATLAB_STAGE curve_fitting\\n');
        assert(isequal(size(imresize(ones(4),2)),[8 8]));
        fprintf('HYDRA_MATLAB_STAGE image_resize\\n');
        assert(exist('resnet50','file')==2);
        fprintf('HYDRA_MATLAB_STAGE model_entrypoint\\n');
        net=resnet50; assert(numel(net.Layers)>0);
        fprintf('HYDRA_MATLAB_BATCH_OK %s\\n',version('-release'));
        fprintf('HYDRA_MATLAB_PRODUCTS_JSON %s\\n',jsonencode(ver));
        catch ME; fprintf('HYDRA_MATLAB_ERROR_ID %s\\n',ME.identifier); rethrow(ME); end;
    """
    statement = " ".join(statement.split())
    try:
        result = subprocess.run(
            ["xvfb-run", "-a", str(executable), statement], env=environment,
            capture_output=True, text=True, timeout=900,
        )
    except subprocess.TimeoutExpired:
        raise SystemExit("Local licensed MATLAB check timed out; output withheld.") from None
    # Licensing tools can print sensitive diagnostics. Publish only our explicit
    # validation markers, never arbitrary stdout/stderr or environment contents.
    passed = False
    for line in (result.stdout + result.stderr).splitlines():
        line = line.strip()
        if line.startswith(("HYDRA_MATLAB_BATCH_OK ", "HYDRA_MATLAB_PRODUCTS_JSON ",
                            "HYDRA_MATLAB_STAGE ", "HYDRA_MATLAB_ERROR_ID ")):
            print(line)
            passed = passed or line.startswith("HYDRA_MATLAB_BATCH_OK ")
    if result.returncode or not passed:
        known = ("License checkout failed", "Invalid license token", "error while loading shared libraries")
        category = next((value for value in known if value in result.stdout + result.stderr), "failure")
        # Fixed diagnostic categories reveal neither raw licensing text nor
        # parts of the token. They distinguish launcher/emulation failures.
        output = (result.stdout + result.stderr).lower()
        flags = {name: needle in output for name, needle in {
            "token-mentioned": "token", "expired": "expired", "update-required": "download",
            "matlab-mentioned": "matlab", "license-mentioned": "license",
            "crash": "segmentation", "illegal-instruction": "illegal instruction",
            "oom": "killed", "missing-library": "shared libraries",
            "error-mentioned": "error", "usage": "usage", "success": "success",
        }.items()}
        print("MATLAB_BATCH_DIAGNOSTIC_FLAGS", flags, "output_bytes", len(output))
        raise SystemExit(f"Local licensed MATLAB check: {category}; success marker={passed}; raw output withheld (exit {result.returncode}).")
