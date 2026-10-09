# VS Code persistence and dynamic installation evaluation

The user requested evaluation of `matteosecli/codespeck` without implementing
its dynamic Microsoft-server approach, then approved the smaller
`CODE_EXTENSIONSDIR` persistence fix. This image implements only that fix.

## Why the existing extensions can disappear

The conda-forge code-server launcher defaults `--extensions-dir` to
`/opt/conda/share/code-server/extensions`. That is in the container's writable
layer, outside a persistent `/home/jovyan` volume. Putting the binary in the
image does not inherently make user extensions ephemeral; their storage path
does. This is a source-based explanation, not a live-pod inspection.

The Jupyter proxy supports `CODE_EXTENSIONSDIR` and passes the corresponding
explicit `--extensions-dir` argument. The new image sets it to:

```text
/home/jovyan/.local/share/code-server/extensions
```

Normal user settings and launcher configuration reside under
`~/.local/share/code-server` and `~/.config/code-server`, also on the home volume.
The container tests install a tiny local VSIX and settings on a disposable home
volume, then check them from a newly created container using that same volume.

For extension installation from a terminal, explicitly pass the path too:

```bash
code-server --extensions-dir "$CODE_EXTENSIONSDIR" --install-extension EXTENSION_ID
```

The environment override is consumed by the Jupyter proxy; the conda CLI wrapper
does not itself use `CODE_EXTENSIONSDIR` as its default.

## Dynamic editor installation

Codespeck downloads a Microsoft web-server build into versioned directories
under `~/.vscode/cli/serve-web`, reads devcontainer settings/extension names,
writes Machine settings, patches workbench JavaScript, and starts the server's
internal executable. It does not provision a complete devcontainer.

This can reduce the shared image size and give each user independent editor
versions. However, each user's volume then contains a copy of the binary; first
start requires network access, and interrupted downloads, parallel starts,
version cleanup, base-path/WebSocket behavior, and updates become responsibilities
of the launcher. A robust implementation needs atomic installs, locks, artifact
verification, deliberate version selection, preserved user settings, and a
supported Jupyter Server Proxy process configuration rather than editing an
installed Python package. Codespeck's workbench patch also depends on Microsoft's
internal frontend layout.

## Marketplace and licensing

Downloading Microsoft binaries at runtime is not a blanket exemption from
their use/service terms. The Microsoft Server FAQ says the server cannot be
hosted as a service, while its Remote Development FAQ permits internal/private
services under the applicable license. A turnkey multiuser browser service
requires clarification for that exact usage; one server process per user is
an isolation choice, not a resolution of the license question.

Code-server and OpenVSCode-Server normally use Open VSX. Changing their extension
gallery to Microsoft's does not establish Marketplace entitlement. Official
per-user Remote Tunnels are a documented alternative using desktop VS Code or
`vscode.dev`, but introduce another account/relay workflow and do not reuse the
JupyterHub browser endpoint or organization authorization automatically.

## Recommendation and status

Keep the tested shared code-server binary in the image and store each user's
extensions/settings on their existing home volume. This fixes the concrete
persistence problem with fewer moving parts. No extensions are preinstalled in
the new image; users may install and update their own.

The dynamic Microsoft-server option is evaluated only and is not implemented.
No changes to the running Hydra deployment are made as part of this image work.
The existing untrusted HTTPS certificate can also affect webviews/service workers,
independently of where the editor is installed.

## Primary sources

- [Conda-forge code-server launcher](https://github.com/conda-forge/code-server-feedstock/blob/main/recipe/build.sh)
- [Jupyter VS Code proxy command](https://github.com/betatim/vscode-binder/blob/master/jupyter_vscode_proxy/__init__.py)
- [Codespeck source](https://github.com/matteosecli/codespeck/blob/main/codespeck)
- [Jupyter Server Proxy process configuration](https://jupyter-server-proxy.readthedocs.io/en/latest/server-process.html)
- [Code-server FAQ and extension paths](https://coder.com/docs/code-server/FAQ)
- [Microsoft VS Code Server license](https://code.visualstudio.com/license/server)
- [Microsoft Server FAQ](https://code.visualstudio.com/docs/remote/vscode-server#can-i-host-the-vs-code-server-as-a-service)
- [Microsoft Remote Development FAQ](https://code.visualstudio.com/docs/remote/faq#can-i-use-the-vs-code-remote-development-extensions-to-build-my-own-product-or-service)
- [Official Remote Tunnels](https://code.visualstudio.com/docs/remote/tunnels)
