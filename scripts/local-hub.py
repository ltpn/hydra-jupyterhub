"""One-user localhost Hub for testing the notebook image."""
from jupyterhub.spawner import SimpleLocalProcessSpawner

c = get_config()
c.JupyterHub.bind_url = "http://0.0.0.0:8000/jupyter/"
c.JupyterHub.hub_ip = "127.0.0.1"
c.JupyterHub.authenticator_class = "dummy"
c.DummyAuthenticator.allow_all = False
c.DummyAuthenticator.allowed_users = {"jovyan"}
c.JupyterHub.spawner_class = SimpleLocalProcessSpawner
c.SimpleLocalProcessSpawner.home_dir_template = "/home/jovyan"
c.Spawner.cmd = ["/usr/local/bin/start-singleuser.py"]
c.Spawner.default_url = "/lab"
c.Spawner.notebook_dir = "/home/jovyan"
c.Spawner.http_timeout = 120
c.Spawner.env_keep.extend([
    "JULIA_DEPOT_PATH", "JULIA_PKGDIR", "JULIA_NUM_THREADS", "JULIA_CPU_TARGET",
    "CODE_EXTENSIONSDIR", "MATLAB_ROOT", "MWI_CUSTOM_MATLAB_ROOT",
    "MATHWORKS_SERVICE_HOST_MANAGED_INSTALL_ROOT",
    "MW_SERVICEHOST_USE_HOSTNAME_FOR_PERSISTENCE", "GKSwstype",
    "JUPYTER_PREFER_ENV_PATH",
])
c.JupyterHub.db_url = "sqlite:////home/jovyan/.jupyterhub-local.sqlite"
c.JupyterHub.cookie_secret_file = "/home/jovyan/.jupyterhub-local-cookie-secret"
