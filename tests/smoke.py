"""Run inside the built image; exercise the actual Jupyter kernel protocol."""
import json
import os
import inspect
import subprocess
import tempfile
from pathlib import Path

from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager


def execute(kernel_name, code, cwd):
    manager = KernelManager(kernel_name=kernel_name)
    client = None
    try:
        manager.start_kernel(cwd=str(cwd))
        client = manager.client()
        client.start_channels()
        client.wait_for_ready(timeout=180)
        message_id = client.execute(code)
        messages = []
        while True:
            message = client.get_iopub_msg(timeout=300)
            if message.get("parent_header", {}).get("msg_id") != message_id:
                continue
            if message["msg_type"] == "error":
                raise AssertionError("\n".join(message["content"]["traceback"]))
            messages.append(message)
            if message["msg_type"] == "status" and message["content"]["execution_state"] == "idle":
                break
        reply = client.get_shell_msg(timeout=30)
        assert reply["content"]["status"] == "ok", reply
        return messages
    finally:
        if client:
            client.stop_channels()
        manager.shutdown_kernel(now=True)


metadata = json.loads(Path("/usr/local/share/hydra-jupyterhub/versions.json").read_text())
assert metadata["image"]["architecture"] == "x86_64"
assert metadata["julia"]["cuda_runtime"] == "12.9"
assert metadata["julia"]["cuda_compiler"] == "12.9"
assert metadata["python"]["packages"].get("jupyter-vscode-proxy")
assert metadata["python"]["packages"].get("jupyter-pluto-proxy")
spec = KernelSpecManager().get_kernel_spec("julia-hydra")
assert spec.argv[0] == "/usr/local/bin/julia", spec.argv
assert "--project=@." in spec.argv, spec.argv
assert spec.resource_dir.startswith("/opt/conda/share/jupyter/kernels/"), spec.resource_dir
assert not Path("/opt/conda/envs/Qiskit").exists()
assert os.environ["CODE_EXTENSIONSDIR"] == "/home/jovyan/.local/share/code-server/extensions"
# Explicit proxy argument overrides conda's nonpersistent extensions default.
import jupyter_vscode_proxy
command = jupyter_vscode_proxy.setup_vscode()["command"]
if callable(command):
    kwargs = {"port": 12345}
    if "unix_socket" in inspect.signature(command).parameters:
        kwargs["unix_socket"] = ""
    command = command(**kwargs)
assert "--extensions-dir" in command, command
assert command[command.index("--extensions-dir") + 1] == os.environ["CODE_EXTENSIONSDIR"], command

with tempfile.TemporaryDirectory() as directory:
    cwd = Path(directory)
    execute("python3", "assert 1 + 1 == 2; print('PYTHON_KERNEL_OK')", cwd)
    code = '''
        using Pkg, TOML, IJulia, BenchmarkTools, QuantumToolbox, ITensors, ITensorMPS, JLD2, HDF5
        @assert 1 + 1 == 2
        @assert startswith(Base.active_project(), "/opt/julia/environments/v")
        prefs = TOML.parsefile(joinpath(dirname(Base.active_project()), "LocalPreferences.toml"))
        @assert prefs["CUDA_Runtime_jll"]["version"] == "12.9"
        println("JULIA_KERNEL_OK ", VERSION, " ", Base.active_project())
    '''
    execute("julia-hydra", code, cwd)
    # Preserve normal IJulia project discovery: an empty local project can use
    # installed global IJulia; a project with its own deps must be instantiated.
    (cwd / "Project.toml").write_text("[deps]\n")
    local_code = '@assert Base.active_project() == joinpath(pwd(), "Project.toml"); @assert 1+1 == 2; println("LOCAL_PROJECT_KERNEL_OK")'
    execute("julia-hydra", local_code, cwd)

# CPU-only package loading is a separate check from hardware GPU execution.
subprocess.run(["julia", "--startup-file=no", "-e",
                "using CUDA, Pluto, CairoMakie, Plots, OrdinaryDiffEq, StochasticDiffEq, ITensorGaussianMPS; "
                "println(\"JULIA_IMPORTS_OK\")"], check=True, timeout=600)
print("SMOKE_TESTS_PASSED", json.dumps({"julia": metadata["julia"]["version"],
                                        "hub": metadata["python"]["packages"]["jupyterhub"]}))
