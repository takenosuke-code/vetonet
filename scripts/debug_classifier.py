"""Debug why classifier isn't catching bypassed attacks."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from vetonet import db
# Import module, not internal vars
from vetonet.models import IntentAnchor, AgentPayload
import json

def debug_bypassed():
    # Import after loading
    from vetonet.checks import classifier as cls

    if not cls._load_model():
        print("Classifier not loaded!")
        return

    _embedder = cls._embedder
    _classifier = cls._classifier

    if _embedder is None:
        print("Embedder is None!")
        return

    client = db.get_client()
    result = client.table("attacks").select("*").eq("verdict", "approved").limit(10).execute()

    print("Checking 10 bypassed attacks:\n")

    for attack in result.data:
        intent_data = attack.get("intent") or {}
        payload_data = attack.get("payload") or {}

        intent = IntentAnchor(
            item_category=intent_data.get("item_category", "gift_card"),
            max_price=intent_data.get("max_price", 100),
            quantity=intent_data.get("quantity", 1),
            core_constraints=intent_data.get("core_constraints", [])
        )

        payload = AgentPayload(
            item_description=payload_data.get("item_description", ""),
            item_category=payload_data.get("item_category", "gift_card"),
            unit_price=payload_data.get("unit_price", 0),
            quantity=payload_data.get("quantity", 1),
            vendor=payload_data.get("vendor", ""),
            fees=[]
        )

        # Same text preparation as classifier
        prompt_text = f"{intent.item_category} {intent.max_price} {' '.join(intent.core_constraints)}"
        payload_dict = payload.model_dump()
        payload_dict.pop('metadata', None)
        payload_json = json.dumps(payload_dict, sort_keys=True, default=str)
        text = f"{prompt_text} | {payload_json}"

        # Get prediction
        embedding = _embedder.encode([text])
        proba = _classifier.predict_proba(embedding)[0]

        print(f"Vector: {attack.get('attack_vector', 'unknown')}")
        print(f"Prompt: {attack.get('prompt', '')[:50]}...")
        print(f"Attack prob: {proba[1]:.2%}, Legit prob: {proba[0]:.2%}")
        print(f"Would block: {proba[1] >= 0.85}")
        print(f"Text: {text[:100]}...")
        print("-" * 60)


if __name__ == "__main__":
    debug_bypassed()
