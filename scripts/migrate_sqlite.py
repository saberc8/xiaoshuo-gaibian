"""Back up and migrate existing workspace records into configured PostgreSQL."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings
from backend.app.migration import migrate_sqlite
from backend.app.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'data/studio.sqlite3')
    parser.add_argument('--backup-dir', type=Path, default=ROOT/'data/migration-backups')
    options = parser.parse_args()
    settings = Settings()
    store = Store(settings.data_dir, settings.database_url, settings.database_schema)
    try:
        print(json.dumps(migrate_sqlite(options.source, store, options.backup_dir), ensure_ascii=False, indent=2))
    finally:
        store.close()


if __name__ == '__main__':
    main()
