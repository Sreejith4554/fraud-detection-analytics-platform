"""Small explicit source hygiene gate, not a comprehensive secret scanner."""

import subprocess
from pathlib import Path


def main():
    files = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    problems = []
    for name in filter(None, files):
        path = Path(name)
        if name.startswith((".secrets/", "data/raw/", "data/processed/", "upload/")):
            problems.append(name)
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            problems.append(name)
        if path.is_file() and path.stat().st_size > 10 * 1024 * 1024:
            problems.append(name + " exceeds 10 MiB")
    if problems:
        raise SystemExit("Repository gate failed: " + ", ".join(problems))
    print("Tracked-path and size checks passed; not a complete secrets/security audit")


if __name__ == "__main__":
    main()
