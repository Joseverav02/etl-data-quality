"""CLI: python -m etl --input data/policies_sample.csv --db warehouse.db"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from etl.pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline ETL de pólizas con calidad de datos.")
    parser.add_argument("--input", type=Path, required=True, help="CSV de origen")
    parser.add_argument("--db", type=Path, default=Path("warehouse.db"), help="SQLite de destino")
    parser.add_argument("--report", type=Path, help="ruta opcional del informe JSON")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report = run(args.input, args.db)
    payload = json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload, encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
