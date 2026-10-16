"""Print or write project-scoped Codex MCP configuration; preserve unrelated tables."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings  # noqa: E402


def configuration(api_url: str | None = None) -> str:
    def literal(value):
        return json.dumps(str(value), ensure_ascii=False)

    python = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    return (
        "[mcp_servers.novelstudio]\n"
        f"command = {literal(python)}\n"
        'args = ["-m", "backend.app.mcp_server"]\n'
        f"cwd = {literal(ROOT)}\n"
        "startup_timeout_sec = 20\n"
        "tool_timeout_sec = 120\n\n"
        "[mcp_servers.novelstudio.env]\n"
        f"NOVEL_API_URL = {literal(api_url or Settings().api_url)}\n"
    )


def merge(existing: str, new: str) -> str:
    parts = re.split(r"(?m)(?=^\[)", existing)
    retained = [part for part in parts if not re.match(r"\[mcp_servers\.novelstudio(?:\.[^\]]+)?\]", part)]
    return "".join(retained).rstrip() + "\n\n" + new if any(part.strip() for part in retained) else new


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write .codex/config.toml for this project")
    parser.add_argument("--api-url", help="Backend URL; defaults to NOVEL_API_URL or .env")
    options = parser.parse_args()
    config = configuration(options.api_url)
    if options.write:
        file = ROOT / ".codex/config.toml"
        file.parent.mkdir(exist_ok=True)
        file.write_text(merge(file.read_text() if file.exists() else "", config), encoding="utf-8")
        print(f"已写入 {file}\n重新打开项目或重启 Codex 会话后，检查 novelstudio MCP。")
    else:
        print(config)
