"""Entrypoint CLI del progetto.

Uso: python -m src.cli etl
     python -m src.cli schema
"""

from __future__ import annotations

import argparse
import logging
import os

from neo4j import GraphDatabase

from src.etl.build_csv import DEFAULT_OUTPUT_DIR, DEFAULT_PARQUET_PATH, build_graph_csvs
from src.schema import apply_schema_with_driver

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(prog="src.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    etl_parser = subparsers.add_parser("etl", help="Genera i CSV per nodi/relazioni dal parquet sorgente")
    etl_parser.add_argument("--parquet-path", default=str(DEFAULT_PARQUET_PATH))
    etl_parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))

    subparsers.add_parser("schema", help="Applica constraint e indici Neo4j")

    args = parser.parse_args()

    if args.command == "etl":
        build_graph_csvs(parquet_path=args.parquet_path, output_dir=args.output_dir)
    elif args.command == "schema":
        driver = GraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
        )
        try:
            apply_schema_with_driver(driver)
            logger.info("Constraint e indici applicati con successo")
        finally:
            driver.close()


if __name__ == "__main__":
    main()
