"""Parse version lines while ignoring CLI startup logs and timestamps."""
import re


def parse_tool_version(output):
    output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output)
    match = re.search(r"(?m)^(?:conda |btop version: )?v?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)(?:\s|$)", output)
    if not match:
        raise ValueError("CLI did not report a recognizable software version")
    return match.group(1)
