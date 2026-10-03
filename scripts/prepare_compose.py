"""Create an uncommitted local demo password; verify the trusted model before build."""

import hashlib
import json
import os
import secrets
from pathlib import Path


def main():
    manifest = json.loads(Path("docs/evidence/model-selection.json").read_text())
    with Path("artifacts/model.joblib").open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != manifest["model_sha256"]:
            raise ValueError("Restore the trusted model before preparing Compose")
    directory = Path(".secrets")
    directory.mkdir(mode=0o700, exist_ok=True)
    target = directory / "db_password"
    if not target.exists():
        # Compose mounts the file for a non-root app user; parent is owner-private on host.
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "w") as stream:
            stream.write(secrets.token_urlsafe(32) + "\n")
    print("Trusted model verified; local Compose password file ready (value not displayed).")


if __name__ == "__main__":
    main()
