"""Local inspection and reproducible demonstration commands."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from chronicle import __version__
from chronicle.storage import db


def main() -> None:
    parser = argparse.ArgumentParser(description="Chronicle event intelligence tools")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("stats", help="Show database counts as JSON")
    demo = commands.add_parser(
        "demo", help="Create an offline sample corpus and cluster it"
    )
    demo.add_argument(
        "--db", default="data/chronicle-demo.db", help="New demo database path"
    )
    args = parser.parse_args()
    if args.command == "demo":
        path = Path(args.db)
        if path.exists():
            parser.error("Demo database already exists. Choose a new --db path.")
        os.environ["CHRONICLE_DB_PATH"] = str(path)
        from chronicle.cluster.pipeline import run_batch
        from chronicle.config import settings

        settings.embedding_backend = "tfidf"
        settings.dedup_threshold = 0.95
        settings.cluster_min_size = 3
        conn = db.connect()
        topics = [
            (
                "space",
                "Lunar mission",
                "Lunar spacecraft mission reaches the moon. "
                "Engineers confirm the lunar spacecraft orbit and moon landing mission.",
            ),
            (
                "energy",
                "Solar storage",
                "Solar energy battery storage powers the grid. "
                "Engineers expand solar energy batteries and renewable grid storage.",
            ),
            (
                "ocean",
                "Ocean research",
                "Ocean researchers study coral reef marine ecosystems. "
                "The marine expedition measures ocean coral biodiversity and reef recovery.",
            ),
        ]
        try:
            for topic, title, body in topics:
                for index, angle in enumerate(
                    ("Launch", "Analysis", "Update", "Results")
                ):
                    db.insert_doc(
                        conn,
                        {
                            "source": "demo",
                            "external_id": f"{topic}-{index}",
                            "title": f"{title}: {angle}",
                            "text": f"{body} Report {angle.lower()}.",
                            "url": f"https://example.com/{topic}/{index}",
                            "ts": 1790899200 + index * 3600,
                        },
                    )
        finally:
            conn.close()
        run_batch()
    conn = db.connect()
    try:
        print(json.dumps(db.get_stats(conn), indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
