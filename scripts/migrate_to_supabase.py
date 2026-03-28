#!/usr/bin/env python3
"""
Migrate existing JSON data files to Supabase.

Run this once after setting up Supabase to import all existing attack data.

Usage:
    python scripts/migrate_to_supabase.py
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client


def get_supabase_client():
    """Get Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
        print("Set them in .env file or environment variables")
        sys.exit(1)

    return create_client(url, key)


def load_json_file(path: str) -> dict | list | None:
    """Load a JSON file."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"  Error loading {path}: {e}")
        return None


def load_jsonl_file(path: str) -> list:
    """Load a JSONL file (one JSON per line)."""
    records = []
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        print(f"  Error loading {path}: {e}")
    return records


def migrate_fuzzer_results(client, path: str, source_name: str):
    """Migrate fuzzer results JSON file."""
    data = load_json_file(path)
    if not data:
        return 0

    count = 0

    # Import successful bypasses
    for bypass in data.get("successful_bypasses", []):
        payload = bypass.get("payload", {})

        record = {
            "type": "fuzzer",
            "prompt": f"Fuzzer test: {source_name}",
            "attack_vector": bypass.get("vector"),
            "verdict": "approved",  # It bypassed, so it was approved
            "payload": payload,
            "intent": {"source": source_name},
        }

        try:
            client.table("attacks").insert(record).execute()
            count += 1
        except Exception as e:
            print(f"  Error inserting bypass: {e}")

    # Also record summary stats
    by_vector = data.get("by_vector", {})
    for vector, stats in by_vector.items():
        # Record blocked attacks too
        blocked = stats.get("total", 0) - stats.get("bypassed", 0)
        for _ in range(min(blocked, 10)):  # Cap at 10 per vector to avoid bloat
            record = {
                "type": "fuzzer",
                "prompt": f"Fuzzer test: {source_name}",
                "attack_vector": vector,
                "verdict": "blocked",
                "intent": {"source": source_name},
            }
            try:
                client.table("attacks").insert(record).execute()
                count += 1
            except Exception:
                pass

    return count


def migrate_attack_attempts(client, path: str):
    """Migrate attack_attempts.jsonl file."""
    records = load_jsonl_file(path)
    if not records:
        return 0

    count = 0
    for record in records:
        # Determine verdict
        verdict = "approved" if record.get("bypassed") or record.get("approved") else "blocked"

        # Find blocked_by from checks
        blocked_by = record.get("blocked_by")
        if not blocked_by and verdict == "blocked":
            for check in record.get("checks", []):
                if not check.get("passed"):
                    blocked_by = check.get("name")
                    break

        db_record = {
            "type": record.get("type", "unknown"),
            "prompt": record.get("prompt"),
            "attack_vector": record.get("attack_vector"),
            "verdict": verdict,
            "blocked_by": blocked_by,
            "checks": record.get("checks"),
            "payload": record.get("payload"),
            "intent": record.get("intent"),
        }

        try:
            client.table("attacks").insert(db_record).execute()
            count += 1
        except Exception as e:
            print(f"  Error inserting record: {e}")

    return count


def main():
    print("=" * 60)
    print("VetoNet Data Migration to Supabase")
    print("=" * 60)
    print()

    client = get_supabase_client()
    print("Connected to Supabase")
    print()

    root = Path(__file__).parent.parent
    total_migrated = 0

    # Files to migrate
    files_to_migrate = [
        ("fuzzer_results.json", "fuzzer", migrate_fuzzer_results),
        ("advanced_pentest_results.json", "advanced_pentest", migrate_fuzzer_results),
        ("elite_pentest_results.json", "elite_pentest", migrate_fuzzer_results),
        ("mega_pentest_results.json", "mega_pentest", migrate_fuzzer_results),
        ("scripts/mega_pentest_results.json", "scripts_mega_pentest", migrate_fuzzer_results),
    ]

    # Migrate JSON files
    for filename, source_name, migrate_fn in files_to_migrate:
        path = root / filename
        if path.exists():
            print(f"Migrating {filename}...")
            count = migrate_fn(client, str(path), source_name)
            print(f"  Imported {count} records")
            total_migrated += count
        else:
            print(f"Skipping {filename} (not found)")

    # Migrate JSONL file
    jsonl_path = root / "data" / "attack_attempts.jsonl"
    if jsonl_path.exists():
        print(f"Migrating data/attack_attempts.jsonl...")
        count = migrate_attack_attempts(client, str(jsonl_path))
        print(f"  Imported {count} records")
        total_migrated += count
    else:
        print("Skipping data/attack_attempts.jsonl (not found)")

    print()
    print("=" * 60)
    print(f"Migration complete! Total records imported: {total_migrated}")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Verify data in Supabase dashboard")
    print("2. Delete local JSON files (they're now in Supabase)")
    print("3. Add *.json to .gitignore (except package.json, etc.)")
    print()


if __name__ == "__main__":
    main()
