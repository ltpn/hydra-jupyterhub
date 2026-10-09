"""Parse version lines while ignoring CLI startup logs and timestamps."""
import re


def parse_tool_version(output):
    match = re.search(r"(?m)^(?:conda )?v?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)(?:\s|$)", output)
    if not match:
        raise ValueError("CLI did not report a recognizable software version")
    return match.group(1)
