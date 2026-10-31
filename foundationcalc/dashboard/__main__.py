"""Run the dashboard with `python -m foundationcalc.dashboard`."""

import os
import subprocess
import sys


def main() -> None:
    here = os.path.dirname(__file__)
    app_path = os.path.join(here, "app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", app_path]
    subprocess.run(cmd, check=False)


if __name__ == "__main__":
    main()
