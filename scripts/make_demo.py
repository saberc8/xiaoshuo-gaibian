"""Write the original, self-contained sample EPUB for upload testing."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.demo import demo_epub  # noqa: E402

if __name__ == "__main__":
    path = ROOT / "examples" / "雾港来信.epub"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(demo_epub())
    print(path)
