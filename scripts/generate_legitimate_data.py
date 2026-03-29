#!/usr/bin/env python3
"""
Generate legitimate transaction examples for classifier training.

These are REAL legitimate transactions - proper vendors, no hidden fees,
correct prices - to teach the classifier what "safe" looks like.

Usage:
    python scripts/generate_legitimate_data.py
"""

import json
import random
from pathlib import Path

# Real legitimate transaction templates
LEGITIMATE_TRANSACTIONS = [
    # Gift cards - legitimate vendors
    {"prompt": "$50 Amazon Gift Card", "payload": {"item_description": "Amazon Gift Card $50", "item_category": "gift_card", "unit_price": 50.0, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$25 iTunes Gift Card", "payload": {"item_description": "iTunes Gift Card $25", "item_category": "gift_card", "unit_price": 25.0, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$100 Visa Gift Card", "payload": {"item_description": "Visa Gift Card $100", "item_category": "gift_card", "unit_price": 100.0, "quantity": 1, "vendor": "visa.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$50 Google Play Gift Card", "payload": {"item_description": "Google Play Gift Card $50", "item_category": "gift_card", "unit_price": 50.0, "quantity": 1, "vendor": "play.google.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$20 Starbucks Gift Card", "payload": {"item_description": "Starbucks Gift Card $20", "item_category": "gift_card", "unit_price": 20.0, "quantity": 1, "vendor": "starbucks.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # Electronics - legitimate vendors
    {"prompt": "iPhone 15 Pro", "payload": {"item_description": "iPhone 15 Pro 256GB", "item_category": "electronics", "unit_price": 1199.0, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "AirPods Pro", "payload": {"item_description": "AirPods Pro 2nd Gen", "item_category": "electronics", "unit_price": 249.0, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Samsung Galaxy S24", "payload": {"item_description": "Samsung Galaxy S24 Ultra", "item_category": "electronics", "unit_price": 1299.0, "quantity": 1, "vendor": "samsung.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Sony headphones under $400", "payload": {"item_description": "Sony WH-1000XM5", "item_category": "electronics", "unit_price": 349.0, "quantity": 1, "vendor": "sony.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Nintendo Switch", "payload": {"item_description": "Nintendo Switch OLED", "item_category": "electronics", "unit_price": 349.0, "quantity": 1, "vendor": "nintendo.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # Shoes - legitimate vendors
    {"prompt": "Nike Air Force 1 size 10", "payload": {"item_description": "Nike Air Force 1 '07", "item_category": "shoes", "unit_price": 115.0, "quantity": 1, "vendor": "nike.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Adidas Ultraboost", "payload": {"item_description": "Adidas Ultraboost 22", "item_category": "shoes", "unit_price": 190.0, "quantity": 1, "vendor": "adidas.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "New Balance 990", "payload": {"item_description": "New Balance 990v5", "item_category": "shoes", "unit_price": 185.0, "quantity": 1, "vendor": "newbalance.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Converse Chuck Taylor", "payload": {"item_description": "Converse Chuck Taylor All Star", "item_category": "shoes", "unit_price": 65.0, "quantity": 1, "vendor": "converse.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # Food delivery - legitimate vendors
    {"prompt": "2 large pizzas from Dominos", "payload": {"item_description": "2 Large Pepperoni Pizzas", "item_category": "food", "unit_price": 32.0, "quantity": 1, "vendor": "dominos.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Chipotle burrito bowl", "payload": {"item_description": "Chicken Burrito Bowl", "item_category": "food", "unit_price": 12.0, "quantity": 1, "vendor": "chipotle.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Starbucks coffee order", "payload": {"item_description": "Grande Caramel Macchiato", "item_category": "food", "unit_price": 6.0, "quantity": 2, "vendor": "starbucks.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # Subscriptions - legitimate
    {"prompt": "Netflix subscription", "payload": {"item_description": "Netflix Standard Plan", "item_category": "subscription", "unit_price": 15.49, "quantity": 1, "vendor": "netflix.com", "currency": "USD", "fees": [], "is_recurring": True}},
    {"prompt": "Spotify Premium", "payload": {"item_description": "Spotify Premium Individual", "item_category": "subscription", "unit_price": 11.99, "quantity": 1, "vendor": "spotify.com", "currency": "USD", "fees": [], "is_recurring": True}},
    {"prompt": "YouTube Premium", "payload": {"item_description": "YouTube Premium", "item_category": "subscription", "unit_price": 13.99, "quantity": 1, "vendor": "youtube.com", "currency": "USD", "fees": [], "is_recurring": True}},
    {"prompt": "Disney+ subscription", "payload": {"item_description": "Disney+ Monthly", "item_category": "subscription", "unit_price": 13.99, "quantity": 1, "vendor": "disneyplus.com", "currency": "USD", "fees": [], "is_recurring": True}},

    # Clothing - legitimate vendors
    {"prompt": "Levi's 501 jeans", "payload": {"item_description": "Levi's 501 Original Fit Jeans", "item_category": "clothing", "unit_price": 69.50, "quantity": 1, "vendor": "levi.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "North Face jacket", "payload": {"item_description": "The North Face Thermoball Jacket", "item_category": "clothing", "unit_price": 220.0, "quantity": 1, "vendor": "thenorthface.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Uniqlo t-shirts", "payload": {"item_description": "Uniqlo Supima Cotton T-Shirt 3 Pack", "item_category": "clothing", "unit_price": 45.0, "quantity": 1, "vendor": "uniqlo.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # Books/Media - legitimate vendors
    {"prompt": "Kindle book", "payload": {"item_description": "Kindle eBook", "item_category": "books", "unit_price": 14.99, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Audible audiobook", "payload": {"item_description": "Audible Audiobook Credit", "item_category": "books", "unit_price": 14.95, "quantity": 1, "vendor": "audible.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # Home goods - legitimate vendors
    {"prompt": "Dyson vacuum", "payload": {"item_description": "Dyson V15 Detect", "item_category": "home", "unit_price": 749.0, "quantity": 1, "vendor": "dyson.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "IKEA desk", "payload": {"item_description": "IKEA BEKANT Desk", "item_category": "furniture", "unit_price": 349.0, "quantity": 1, "vendor": "ikea.com", "currency": "USD", "fees": [], "is_recurring": False}},
]

# Variations to generate more examples
PRICE_VARIATIONS = [0.9, 0.95, 1.0, 1.0, 1.0, 1.05]  # Slight price variations
QUANTITY_VARIATIONS = [1, 1, 1, 1, 2, 3]  # Mostly single items

def generate_variation(template: dict) -> dict:
    """Generate a variation of a legitimate transaction."""
    t = template.copy()
    p = t["payload"].copy()

    # Vary price slightly
    price_mult = random.choice(PRICE_VARIATIONS)
    p["unit_price"] = round(p["unit_price"] * price_mult, 2)

    # Vary quantity sometimes
    if random.random() > 0.8:
        p["quantity"] = random.choice(QUANTITY_VARIATIONS)

    t["payload"] = p
    return t


def generate_legitimate_dataset(n: int = 500) -> list:
    """Generate n legitimate transaction examples."""
    examples = []

    while len(examples) < n:
        template = random.choice(LEGITIMATE_TRANSACTIONS)
        example = generate_variation(template)

        # Format for training - MUST match classifier.py format:
        # f"{item_category} {max_price} {constraints} | {payload_json}"
        p = example["payload"]
        category = p.get("item_category", "item")
        price = p.get("unit_price", 0)
        constraints = f"brand:{p.get('vendor', '').split('.')[0]}" if p.get('vendor') else ""
        normalized_prompt = f"{category} {price} {constraints}"

        payload_json = json.dumps(example["payload"], sort_keys=True)
        text = f"{normalized_prompt} | {payload_json}"

        examples.append({
            "text": text,
            "prompt": example["prompt"],
            "payload": example["payload"],
            "label": 0,  # Legitimate
            "verdict": "approved",
            "attack_vector": None,
            "blocked_by": None,
            "source": "synthetic_legitimate"
        })

    return examples


def main():
    print("=" * 50)
    print("Generating Legitimate Transaction Examples")
    print("=" * 50)
    print()

    # Generate examples
    examples = generate_legitimate_dataset(500)
    print(f"Generated {len(examples)} legitimate examples")

    # Save to file
    output_path = Path(__file__).parent.parent / "data" / "legitimate_examples.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"Saved to: {output_path}")

    # Show sample
    print()
    print("Sample examples:")
    for ex in examples[:3]:
        print(f"  - {ex['prompt'][:40]}... | vendor: {ex['payload']['vendor']}")

    print()
    print("=" * 50)
    print("Done! Now update export script to combine with attack data.")
    print("=" * 50)


if __name__ == "__main__":
    main()
