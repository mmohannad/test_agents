#!/usr/bin/env python3
"""
Convert JSON articles to CSV for Supabase import.
"""

import csv
import json
from pathlib import Path


def json_to_csv(json_file: Path, csv_file: Path):
    """Convert JSON articles file to CSV."""
    with open(json_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        print("No records found in JSON file")
        return

    # CSV columns matching Supabase table (excluding id, embedding, arabic_embedding)
    fieldnames = [
        "idx",
        "article_number",
        "law_id",
        "hierarchy_path",
        "citation",
        "text_arabic",
        "text_english",
        "effective_date",
        "is_active",
        "updated",
        "added"
    ]

    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            # Extract law_id from citation JSON
            citation = json.loads(record["citation"])
            row = {
                "idx": record["idx"],
                "article_number": record["article_number"],
                "law_id": citation["law_id"],
                "hierarchy_path": record["hierarchy_path"],
                "citation": record["citation"],
                "text_arabic": record["text_arabic"],
                "text_english": record["text_english"],
                "effective_date": record["effective_date"],
                "is_active": record["is_active"],
                "updated": record["updated"],
                "added": record["added"]
            }
            writer.writerow(row)

    print(f"Created CSV with {len(records)} records: {csv_file}")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    json_file = script_dir / "supabase_import" / "all_poa_articles.json"
    csv_file = script_dir / "supabase_import" / "poa_articles.csv"

    if not json_file.exists():
        print(f"JSON file not found: {json_file}")
        print("Run fetch_for_supabase.py first to generate the JSON file.")
    else:
        json_to_csv(json_file, csv_file)
