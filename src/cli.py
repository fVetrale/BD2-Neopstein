"""Entrypoint CLI del progetto.

Uso: python -m src.cli etl
"""

from __future__ import annotations

import argparse
import logging

from src.etl.build_csv import DEFAULT_OUTPUT_DIR, DEFAULT_PARQUET_PATH, build_graph_csvs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(prog="src.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    etl_parser = subparsers.add_parser("etl", help="Genera i CSV per nodi/relazioni dal parquet sorgente")
    etl_parser.add_argument("--parquet-path", default=str(DEFAULT_PARQUET_PATH))
    etl_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))

    args = parser.parse_args()

    if args.command == "etl":
        build_graph_csvs(parquet_path=args.parquet_path, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
