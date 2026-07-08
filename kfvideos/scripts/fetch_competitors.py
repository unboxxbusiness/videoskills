"""
Kampus Filter — Competitor Scan CLI Entry Point
Loads the shared orchestrator pipeline to run the YouTube scan for Kampus Filter.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Path setup — dynamically reference kfvideos codebase and shared keys
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPTS_DIR)
_SRC_DIR = os.path.join(_PROJECT_ROOT, "src")

# Add the src folder to path
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# Load env variables manually from .env
def _load_env(env_path: str) -> None:
    if not os.path.exists(env_path):
        return
    with open(env_path, "r") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

_load_env(os.path.join(_PROJECT_ROOT, ".env"))

# Import the core orchestrator engine
try:
    import orchestrator
except ImportError as exc:
    print(f"Error: Could not import core orchestrator engine from { _SRC_DIR }.")
    print(f"Details: {exc}")
    sys.exit(1)

CONFIG_PATH = os.path.join(_PROJECT_ROOT, "config", "competitors.json")
OUTPUT_PATH = os.path.join(_PROJECT_ROOT, "data", "competitor_report.json")

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
