"""
TheAskt — Competitor Scan CLI Entry Point
Loads the shared orchestrator pipeline from kfvideos to run the scan for TheAskt.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Path setup — dynamically reference kfvideos codebase and shared keys
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_THEASKT_ROOT = os.path.dirname(_SCRIPTS_DIR)
_PROJECTS_DIR = os.path.dirname(_THEASKT_ROOT)

# Path to kfvideos shared codebase
_KFVIDEOS_ROOT = os.path.join(_PROJECTS_DIR, "kfvideos")
_SHARED_SRC_DIR = os.path.join(_KFVIDEOS_ROOT, "src")

# Add the shared src folder to path
if _SHARED_SRC_DIR not in sys.path:
    sys.path.insert(0, _SHARED_SRC_DIR)

# Load the shared environment keys from kfvideos/.env
def _load_shared_env(env_path: str) -> None:
    if not os.path.exists(env_path):
        return
    with open(env_path, "r") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

_load_shared_env(os.path.join(_KFVIDEOS_ROOT, ".env"))

# Import the core orchestrator engine
try:
    import orchestrator
except ImportError as exc:
    print(f"Error: Could not import core orchestrator engine from { _SHARED_SRC_DIR }.")
    print("Please make sure the kfvideos project is present in the same workspace directory.")
    print(f"Details: {exc}")
    sys.exit(1)

CONFIG_PATH = os.path.join(_THEASKT_ROOT, "config", "theaskt_competitors.json")
OUTPUT_PATH = os.path.join(_THEASKT_ROOT, "data", "competitor_report.json")

# Quota saver parameter (True = cheap scan, False = expensive scan)
SKIP_SEARCH: bool = True

def main():
    orchestrator.run_pipeline(
        config_path=CONFIG_PATH,
        output_path=OUTPUT_PATH,
        skip_search=SKIP_SEARCH,
    )

if __name__ == "__main__":
    main()
