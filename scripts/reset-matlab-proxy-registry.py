"""Discard process/port records from the previous notebook container."""
from pathlib import Path
import socket


def reset_registry(home, hostname):
    # Notebook homes persist; PIDs and localhost ports do not. The proxy manager
    # otherwise preloads a dead backend when the next container reuses its PID.
    root = Path(home) / ".matlab" / "MWI" / "hosts" / hostname / "proxy_manager"
    if not root.exists():
        return 0
    # Never follow user-created symlinks into unrelated directories.
    for path in (root, *root.parents):
        if path.is_symlink():
            raise RuntimeError("Refusing to clear a symlinked MATLAB proxy registry")
        if path == Path(home):
            break
    if not root.is_dir():
        raise RuntimeError("MATLAB proxy registry is not a directory")
    removed = 0
    for session in root.iterdir():
        if session.is_symlink() or not session.is_dir():
            continue
        for record in session.glob("*.info"):
            if record.is_file() or record.is_symlink():
                record.unlink()
                removed += 1
        if not any(session.iterdir()):
            session.rmdir()
    return removed


if __name__ == "__main__":
    try:
        count = reset_registry(Path.home(), socket.gethostname())
    except RuntimeError as error:
        # An unusual user-managed path should not prevent Jupyter itself starting.
        print(f"MATLAB startup: registry cleanup skipped: {error}")
    else:
        print(f"MATLAB startup: cleared {count} prior-container proxy session records")
