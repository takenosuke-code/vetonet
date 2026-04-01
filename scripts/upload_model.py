#!/usr/bin/env python3
"""
Upload trained classifier model to Supabase Storage.

This allows Railway to download the model at startup.

Usage:
    python scripts/upload_model.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client


def main():
    print("=" * 50)
    print("Uploading Model to Supabase Storage")
    print("=" * 50)
    print()

    # Get credentials
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    # Model path
    model_path = Path(__file__).parent.parent / 'models' / 'attack_classifier.pkl'

    if not model_path.exists():
        print(f"Error: Model not found at {model_path}")
        print("Run train_classifier.py first!")
        sys.exit(1)

    print(f"Model file: {model_path}")
    print(f"Model size: {model_path.stat().st_size / 1024:.1f} KB")

    # Connect to Supabase
    client = create_client(url, key)

    # Read model file
    with open(model_path, 'rb') as f:
        model_data = f.read()

    print(f"\nUploading to Supabase Storage...")

    try:
        # Upload to storage bucket 'models'
        # Use upsert to overwrite if exists
        result = client.storage.from_('models').upload(
            'attack_classifier.pkl',
            model_data,
            file_options={"content-type": "application/octet-stream", "upsert": "true"}
        )
        print(f"Upload successful!")
        print(f"Result: {result}")
    except Exception as e:
        # Try to update if file exists
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("File exists, updating...")
            result = client.storage.from_('models').update(
                'attack_classifier.pkl',
                model_data,
                file_options={"content-type": "application/octet-stream"}
            )
            print(f"Update successful!")
        else:
            print(f"Upload failed: {e}")
            sys.exit(1)

    print("\n" + "=" * 50)
    print("Done! Model uploaded to Supabase Storage.")
    print("Railway will download it on next deploy.")
    print("=" * 50)


if __name__ == '__main__':
    main()
