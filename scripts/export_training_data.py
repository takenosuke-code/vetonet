#!/usr/bin/env python3
"""
Export attack data from Supabase for training a classifier.

Exports all attacks with prompt, payload, and verdict label for ML training.

Usage:
    python scripts/export_training_data.py
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


def fetch_all_attacks(client) -> list:
    """Fetch all attacks from Supabase with pagination."""
    all_attacks = []
    page_size = 1000
    offset = 0

    print("Fetching attacks from Supabase...")

    while True:
        response = client.table('attacks').select(
            'prompt, payload, verdict, attack_vector, blocked_by'
        ).range(offset, offset + page_size - 1).execute()

        if not response.data:
            break

        all_attacks.extend(response.data)
        print(f"  Fetched {len(all_attacks)} records...")

        if len(response.data) < page_size:
            break

        offset += page_size

    return all_attacks


def format_for_training(attacks: list) -> list:
    """Format attacks for classifier training."""
    training_data = []

    for attack in attacks:
        prompt = attack.get('prompt', '')
        payload = attack.get('payload', {})
        verdict = attack.get('verdict', '')
        attack_vector = attack.get('attack_vector', '')
        blocked_by = attack.get('blocked_by', '')

        # Skip if missing essential fields
        if not prompt or not verdict:
            continue

        # Create training example
        # Label: 1 = attack (blocked), 0 = legitimate (approved)
        label = 1 if verdict == 'blocked' else 0

        # Combine prompt and payload into text for embedding
        payload_str = json.dumps(payload) if isinstance(payload, dict) else str(payload)
        text = f"{prompt} | {payload_str}"

        training_data.append({
            'text': text,
            'prompt': prompt,
            'payload': payload,
            'label': label,
            'verdict': verdict,
            'attack_vector': attack_vector,
            'blocked_by': blocked_by
        })

    return training_data


def save_training_data(data: list, output_path: str):
    """Save training data to JSONL file."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        for item in data:
            f.write(json.dumps(item) + '\n')

    print(f"Saved {len(data)} training examples to {output_path}")


def print_stats(data: list):
    """Print dataset statistics."""
    total = len(data)
    attacks = sum(1 for d in data if d['label'] == 1)
    legitimate = total - attacks

    print("\n--- Dataset Statistics ---")
    print(f"Total examples: {total}")
    print(f"Attacks (blocked): {attacks} ({attacks/total*100:.1f}%)")
    print(f"Legitimate (approved): {legitimate} ({legitimate/total*100:.1f}%)")

    # Attack vector distribution
    vectors = {}
    for d in data:
        v = d.get('attack_vector') or 'unknown'
        vectors[v] = vectors.get(v, 0) + 1

    print("\nTop attack vectors:")
    for v, count in sorted(vectors.items(), key=lambda x: -x[1])[:10]:
        print(f"  {v}: {count}")


def main():
    print("=" * 50)
    print("VetoNet Training Data Export")
    print("=" * 50)
    print()

    # Connect to Supabase
    client = get_supabase_client()

    # Fetch all attacks
    attacks = fetch_all_attacks(client)
    print(f"\nTotal records fetched: {len(attacks)}")

    if not attacks:
        print("No attacks found in database!")
        return

    # Format for training
    training_data = format_for_training(attacks)

    # Save to file
    output_path = Path(__file__).parent.parent / 'data' / 'training_data.jsonl'
    save_training_data(training_data, str(output_path))

    # Print statistics
    print_stats(training_data)

    print("\n" + "=" * 50)
    print("Export complete!")
    print(f"Output: {output_path}")
    print("=" * 50)


if __name__ == '__main__':
    main()
