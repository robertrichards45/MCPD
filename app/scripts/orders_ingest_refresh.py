from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.services.orders_ingestion import run_official_orders_ingestion


def main() -> int:
    app = create_app()
    with app.app_context():
        result = run_official_orders_ingestion(max_new=30, fetch_limit=160)
        print(
            f"ok={result.get('ok')} scanned={result.get('scanned')} inserted={result.get('inserted')} "
            f"updated={result.get('updated')} errors={len(result.get('errors') or [])}"
        )
        return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

