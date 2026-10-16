"""Start the Python API and React development server, and clean up both on exit."""
import signal
import os
import subprocess
import sys
import time
import argparse
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=int, help="Override the API port in NOVEL_API_URL")
    options = parser.parse_args()
    api = urlsplit(Settings().api_url)
    port = options.api_port if options.api_port is not None else api.port or 8010
    if not 1 <= port <= 65535:
        parser.error("API 端口必须为 1–65535")
    api_url = f"http://127.0.0.1:{port}"
    environment = {**os.environ, "NOVEL_API_URL": api_url}
    commands = [
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(port), "--reload"],
        ["npm", "run", "dev", "--prefix", str(ROOT / "frontend")],
    ]
    processes = []

    def stop(_signum=None, _frame=None):
        for process in processes:
            try:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGTERM)
                elif process.poll() is None:
                    process.terminate()
            except ProcessLookupError:
                pass

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        for command in commands:
            processes.append(subprocess.Popen(command, cwd=ROOT, env=environment, start_new_session=os.name == "posix"))
        print(f"\n续章工作台：http://127.0.0.1:5173\nAPI 文档：{api_url}/docs\nCtrl+C 停止前后端。\n", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        failed = next((process.returncode for process in processes if process.returncode), 0)
        return failed or 0
    finally:
        stop()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()


if __name__ == "__main__":
    sys.exit(main())
