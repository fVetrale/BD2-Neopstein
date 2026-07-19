"""Entrypoint CLI del progetto.

Uso: python -m src.cli etl
     python -m src.cli schema
     python -m src.cli import
     python -m src.cli validate
"""

from __future__ import annotations

import argparse
import logging
import os

from neo4j import GraphDatabase

from src.etl.build_csv import DEFAULT_OUTPUT_DIR, DEFAULT_PARQUET_PATH, build_graph_csvs
from src.etl.import_data import run_import, verify_counts
from src.etl.validate_import import check_graph_integrity, format_integrity_report
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

    subparsers.add_parser("import", help="Importa i CSV in Neo4j (nodi, poi relazioni)")

    subparsers.add_parser(
        "validate", help="Verifica conteggi CSV vs Neo4j e cardinalità/integrità del grafo importato"
    )

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
    elif args.command == "import":
        driver = GraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
        )
        try:
            counts = run_import(driver)
            logger.info("Import completato: %s", counts)
            verification = verify_counts(driver)
            mismatches = {k: v for k, v in verification.items() if not v["match"]}
            if mismatches:
                logger.warning("Discrepanze rilevate nei conteggi: %s", mismatches)
            else:
                logger.info("Tutti i conteggi corrispondono ai CSV sorgente")
        finally:
            driver.close()
    elif args.command == "validate":
        driver = GraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
        )
        try:
            verification = verify_counts(driver)
            mismatches = {k: v for k, v in verification.items() if not v["match"]}
            if mismatches:
                logger.warning("Discrepanze rilevate nei conteggi: %s", mismatches)
            else:
                logger.info("Tutti i conteggi corrispondono ai CSV sorgente")

            integrity = check_graph_integrity(driver)
            print(format_integrity_report(integrity))
        finally:
            driver.close()


if __name__ == "__main__":
    main()
