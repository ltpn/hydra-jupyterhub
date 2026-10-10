using Pkg, TOML

version_name = "v$(VERSION.major).$(VERSION.minor)"
environment = joinpath(first(DEPOT_PATH), "environments", version_name)
mkpath(environment)
for name in readdir(environment)
    if occursin(r"^Manifest(?:-v\d+\.\d+)?\.toml$", name)
        rm(joinpath(environment, name))
    end
end
for name in ("Project.toml", "LocalPreferences.toml")
    cp(joinpath(@__DIR__, name), joinpath(environment, name); force=true)
end
Pkg.activate(environment)
Pkg.Registry.update()
Pkg.resolve()
Pkg.instantiate()
Pkg.precompile(; strict=true)

# Rebuild/register against the resolved IJulia, keeping specs outside PVC homes.
ENV["JUPYTER"] = joinpath(ENV["CONDA_DIR"], "bin", "jupyter")
ENV["JUPYTER_DATA_DIR"] = joinpath(ENV["CONDA_DIR"], "share", "jupyter")
ENV["IJULIA_NODEFAULTKERNEL"] = "1"
Pkg.build("IJulia")
using IJulia
# Replace inherited system Julia specs with one stable entry. User-home specs
# are outside this directory and are never modified during image construction.
kernels_dir = joinpath(ENV["JUPYTER_DATA_DIR"], "kernels")
for name in readdir(kernels_dir)
    specdir = joinpath(kernels_dir, name)
    specfile = joinpath(specdir, "kernel.json")
    if isfile(specfile) && occursin(r"\"language\"\s*:\s*\"julia\"", read(specfile, String))
        rm(specdir; recursive=true)
    end
end
IJulia.installkernel("Julia", "--project=@.";
    julia=Cmd(["/usr/local/bin/julia"]), specname="julia-hydra")

# These are the precise inputs/results for this image; do not commit a Manifest.
metadata_dir = "/usr/local/share/hydra-jupyterhub"
for name in ("Project.toml", "LocalPreferences.toml", "Manifest.toml")
    cp(joinpath(environment, name), joinpath(metadata_dir, name); force=true)
end
open(joinpath(metadata_dir, "julia-info.toml"), "w") do io
    TOML.print(io, Dict("version" => string(VERSION), "default_environment" => environment,
        "cpu_target" => get(ENV, "JULIA_CPU_TARGET", "")))
end
println("Resolved and precompiled the default environment: ", environment)
