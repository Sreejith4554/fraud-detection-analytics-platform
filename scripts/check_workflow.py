"""Static YAML and critical-gate checks; does not emulate GitHub Actions."""

import re
from pathlib import Path

import yaml

workflow = yaml.load(Path(".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
assert set(workflow["on"]) == {"push", "pull_request", "workflow_dispatch"}
assert workflow["permissions"] == {"contents": "read"}
assert workflow["jobs"]["compose"]["needs"] == "integration"
for job in workflow["jobs"].values():
    for step in job["steps"]:
        if "uses" in step:
            assert re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", step["uses"]), "Unpinned action"
        assert step.get("continue-on-error") != "true", "No silent failed gates"
commands = "\n".join(s.get("run", "") for s in workflow["jobs"]["integration"]["steps"])
assert "scripts/ci_verify.py" in commands
assert commands.index("scripts/restore_model.py") < commands.index("scripts/ci_verify.py")
print("Workflow YAML and critical gate checks passed; hosted execution not verified")
