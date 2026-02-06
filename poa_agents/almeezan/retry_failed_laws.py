#!/usr/bin/env python3
"""
Retry fetching the 2 laws that failed due to connection errors.
"""

import json
from pathlib import Path
from fetch_for_supabase import fetch_single_law, POA_LAWS

# Laws that failed
FAILED_LAW_IDS = [2492, 2572]

def retry_failed():
    output_dir = Path(__file__).parent / "supabase_import"

    # Load existing records
    all_file = output_dir / "all_poa_articles.json"
    with open(all_file, "r", encoding="utf-8") as f:
        existing_records = json.load(f)

    print(f"Existing records: {len(existing_records)}")

    # Fetch failed laws
    for law_info in POA_LAWS:
        if law_info["law_id"] in FAILED_LAW_IDS:
            try:
                records = fetch_single_law(law_info)
                existing_records.extend(records)

                # Save individual file
                law_file = output_dir / f"law_{law_info['law_id']}_supabase.json"
                with open(law_file, "w", encoding="utf-8") as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                print(f"  → Saved: {law_file}")

            except Exception as e:
                print(f"  ✗ Error: {e}")

    # Update combined file
    with open(all_file, "w", encoding="utf-8") as f:
        json.dump(existing_records, f, ensure_ascii=False, indent=2)

    print(f"\nTotal records now: {len(existing_records)}")
    print(f"Updated: {all_file}")
    print("\nRun json_to_csv.py to regenerate CSV")


if __name__ == "__main__":
    retry_failed()
