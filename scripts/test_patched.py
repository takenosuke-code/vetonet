"""
Test bypassed attacks against current classifier to see how many are now patched.

This script:
1. Fetches all bypassed attacks from Supabase
2. Runs them through the current ML classifier
3. Reports how many would now be blocked (patched)
4. Updates the patched_count in Supabase for the stats API
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from vetonet import db
from vetonet.checks.classifier import is_classifier_available, check_classifier
from vetonet.models import IntentAnchor, AgentPayload

def test_patched_attacks():
    """Test all bypassed attacks against current classifier."""

    # Check classifier is available
    if not is_classifier_available():
        print("ERROR: Classifier not available. Train it first with:")
        print("  python scripts/train_classifier.py")
        return

    print("Classifier loaded. Fetching bypassed attacks...\n")

    # Fetch only TRUE attacks that bypassed (not legitimate transactions)
    # These vectors indicate real attack attempts that fooled the system
    TRUE_ATTACK_VECTORS = [
        'scam_pattern', 'payload_smuggling', 'encoding',
        'ai_impersonation', 'emotional_manipulation', 'hidden_fees',
        'semantic_bypass'
    ]

    client = db.get_client()
    result = client.table("attacks").select("*").eq("verdict", "approved").in_("attack_vector", TRUE_ATTACK_VECTORS).execute()
    bypassed = result.data

    print(f"Found {len(bypassed)} TRUE attack bypasses (excluding legitimate transactions)\n")

    patched = 0
    still_bypassing = 0
    errors = 0

    patched_attacks = []
    still_bypassing_attacks = []

    for attack in bypassed:
        try:
            prompt = attack.get("prompt", "")
            intent_data = attack.get("intent") or {}
            payload_data = attack.get("payload") or {}
            attack_vector = attack.get("attack_vector", "unknown")

            # Build intent anchor
            intent = IntentAnchor(
                item_category=intent_data.get("item_category", "gift_card"),
                max_price=intent_data.get("max_price", 100),
                quantity=intent_data.get("quantity", 1),
                currency=intent_data.get("currency", "USD"),
                core_constraints=intent_data.get("core_constraints", [])
            )

            # Build payload
            payload = AgentPayload(
                item_description=payload_data.get("item_description", ""),
                item_category=payload_data.get("item_category", "gift_card"),
                unit_price=payload_data.get("unit_price", 0),
                quantity=payload_data.get("quantity", 1),
                currency=payload_data.get("currency", "USD"),
                vendor=payload_data.get("vendor", ""),
                fees=[]
            )

            # Run through classifier
            classifier_result = check_classifier(intent, payload)

            if classifier_result and not classifier_result.passed:
                # Classifier now catches this attack!
                patched += 1
                patched_attacks.append({
                    "id": attack["id"],
                    "vector": attack_vector,
                    "prompt": prompt[:50],
                    "confidence": classifier_result.details.get("confidence", 0) if classifier_result.details else 0
                })
            else:
                still_bypassing += 1
                still_bypassing_attacks.append({
                    "id": attack["id"],
                    "vector": attack_vector,
                    "prompt": prompt[:50],
                    "payload_desc": payload_data.get("item_description", "")[:60]
                })

        except Exception as e:
            errors += 1
            print(f"  Error processing {attack.get('id', 'unknown')}: {e}")

    # Print results
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total bypassed attacks:  {len(bypassed)}")
    print(f"Now PATCHED (blocked):   {patched} ({100*patched/len(bypassed):.1f}%)")
    print(f"Still bypassing:         {still_bypassing} ({100*still_bypassing/len(bypassed):.1f}%)")
    print(f"Errors:                  {errors}")
    print()

    # Show patched by vector
    if patched_attacks:
        print("PATCHED ATTACKS BY VECTOR:")
        vectors = {}
        for a in patched_attacks:
            v = a["vector"]
            vectors[v] = vectors.get(v, 0) + 1
        for v, count in sorted(vectors.items(), key=lambda x: -x[1]):
            print(f"  {v}: {count}")
        print()

    # Show still bypassing
    if still_bypassing_attacks:
        print("STILL BYPASSING (need more training data):")
        vectors = {}
        for a in still_bypassing_attacks:
            v = a["vector"]
            vectors[v] = vectors.get(v, 0) + 1
        for v, count in sorted(vectors.items(), key=lambda x: -x[1]):
            print(f"  {v}: {count}")
        print()

        print("Sample still-bypassing attacks:")
        for a in still_bypassing_attacks[:5]:
            print(f"  - [{a['vector']}] {a['payload_desc'][:50]}...")

    # Save stats to Supabase meta table
    stats = {
        "total_bypassed": len(bypassed),
        "patched": patched,
        "still_bypassing": still_bypassing,
        "patch_rate": round(100 * patched / len(bypassed), 1) if bypassed else 0
    }

    try:
        client.table("vetonet_meta").upsert({
            "key": "patched_stats",
            "value": stats,
            "updated_at": "now()"
        }).execute()
        print("\nSaved patched stats to Supabase")
    except Exception as e:
        print(f"\nFailed to save stats: {e}")

    return stats


if __name__ == "__main__":
    stats = test_patched_attacks()
    if stats:
        print("\n" + "=" * 60)
        print(f"PATCH RATE: {stats['patch_rate']}%")
        print(f"({stats['patched']} of {stats['total_bypassed']} bypassed attacks now blocked)")
        print("=" * 60)
