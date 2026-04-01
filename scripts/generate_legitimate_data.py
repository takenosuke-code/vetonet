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

# Real legitimate transaction templates - 55+ diverse examples
LEGITIMATE_TRANSACTIONS = [
    # ============ GIFT CARDS ============
    {"prompt": "$50 Amazon Gift Card", "payload": {"item_description": "Amazon Gift Card $50", "item_category": "gift_card", "unit_price": 50.0, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$25 iTunes Gift Card", "payload": {"item_description": "iTunes Gift Card $25", "item_category": "gift_card", "unit_price": 25.0, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$100 Visa Gift Card", "payload": {"item_description": "Visa Gift Card $100", "item_category": "gift_card", "unit_price": 100.0, "quantity": 1, "vendor": "visa.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$50 Google Play Gift Card", "payload": {"item_description": "Google Play Gift Card $50", "item_category": "gift_card", "unit_price": 50.0, "quantity": 1, "vendor": "play.google.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$20 Starbucks Gift Card", "payload": {"item_description": "Starbucks Gift Card $20", "item_category": "gift_card", "unit_price": 20.0, "quantity": 1, "vendor": "starbucks.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$100 Best Buy Gift Card", "payload": {"item_description": "Best Buy Gift Card $100", "item_category": "gift_card", "unit_price": 100.0, "quantity": 1, "vendor": "bestbuy.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$75 Target Gift Card", "payload": {"item_description": "Target Gift Card $75", "item_category": "gift_card", "unit_price": 75.0, "quantity": 1, "vendor": "target.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$50 Steam Gift Card", "payload": {"item_description": "Steam Wallet Gift Card $50", "item_category": "gift_card", "unit_price": 50.0, "quantity": 1, "vendor": "store.steampowered.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # ============ ELECTRONICS ============
    {"prompt": "iPhone 15 Pro", "payload": {"item_description": "iPhone 15 Pro 256GB", "item_category": "electronics", "unit_price": 1199.0, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "AirPods Pro", "payload": {"item_description": "AirPods Pro 2nd Gen", "item_category": "electronics", "unit_price": 249.0, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Samsung Galaxy S24", "payload": {"item_description": "Samsung Galaxy S24 Ultra", "item_category": "electronics", "unit_price": 1299.0, "quantity": 1, "vendor": "samsung.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Sony headphones under $400", "payload": {"item_description": "Sony WH-1000XM5", "item_category": "electronics", "unit_price": 349.0, "quantity": 1, "vendor": "sony.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Nintendo Switch", "payload": {"item_description": "Nintendo Switch OLED", "item_category": "electronics", "unit_price": 349.0, "quantity": 1, "vendor": "nintendo.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "PlayStation 5", "payload": {"item_description": "PlayStation 5 Console", "item_category": "electronics", "unit_price": 499.0, "quantity": 1, "vendor": "playstation.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Xbox Series X", "payload": {"item_description": "Xbox Series X Console", "item_category": "electronics", "unit_price": 499.0, "quantity": 1, "vendor": "xbox.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "iPad Air", "payload": {"item_description": "iPad Air 5th Gen 64GB", "item_category": "electronics", "unit_price": 599.0, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Apple Watch", "payload": {"item_description": "Apple Watch Series 9 45mm", "item_category": "electronics", "unit_price": 429.0, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Dell monitor", "payload": {"item_description": "Dell UltraSharp 27 4K Monitor", "item_category": "electronics", "unit_price": 449.0, "quantity": 1, "vendor": "dell.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Logitech mouse", "payload": {"item_description": "Logitech MX Master 3S", "item_category": "electronics", "unit_price": 99.0, "quantity": 1, "vendor": "logitech.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Mechanical keyboard", "payload": {"item_description": "Keychron K2 Wireless", "item_category": "electronics", "unit_price": 89.0, "quantity": 1, "vendor": "keychron.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Bose earbuds", "payload": {"item_description": "Bose QuietComfort Earbuds II", "item_category": "electronics", "unit_price": 279.0, "quantity": 1, "vendor": "bose.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Canon camera", "payload": {"item_description": "Canon EOS R6 Mark II", "item_category": "electronics", "unit_price": 2499.0, "quantity": 1, "vendor": "usa.canon.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # ============ SHOES ============
    {"prompt": "Nike Air Force 1 size 10", "payload": {"item_description": "Nike Air Force 1 '07", "item_category": "shoes", "unit_price": 115.0, "quantity": 1, "vendor": "nike.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Adidas Ultraboost", "payload": {"item_description": "Adidas Ultraboost 22", "item_category": "shoes", "unit_price": 190.0, "quantity": 1, "vendor": "adidas.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "New Balance 990", "payload": {"item_description": "New Balance 990v5", "item_category": "shoes", "unit_price": 185.0, "quantity": 1, "vendor": "newbalance.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Converse Chuck Taylor", "payload": {"item_description": "Converse Chuck Taylor All Star", "item_category": "shoes", "unit_price": 65.0, "quantity": 1, "vendor": "converse.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Vans Old Skool", "payload": {"item_description": "Vans Old Skool Classic", "item_category": "shoes", "unit_price": 70.0, "quantity": 1, "vendor": "vans.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "ASICS running shoes", "payload": {"item_description": "ASICS Gel-Kayano 30", "item_category": "shoes", "unit_price": 160.0, "quantity": 1, "vendor": "asics.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # ============ FOOD ============
    {"prompt": "2 large pizzas from Dominos", "payload": {"item_description": "2 Large Pepperoni Pizzas", "item_category": "food", "unit_price": 32.0, "quantity": 1, "vendor": "dominos.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Chipotle burrito bowl", "payload": {"item_description": "Chicken Burrito Bowl", "item_category": "food", "unit_price": 12.0, "quantity": 1, "vendor": "chipotle.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Starbucks coffee order", "payload": {"item_description": "Grande Caramel Macchiato", "item_category": "food", "unit_price": 6.0, "quantity": 2, "vendor": "starbucks.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Thai food delivery", "payload": {"item_description": "Pad Thai with Chicken", "item_category": "food", "unit_price": 16.0, "quantity": 1, "vendor": "doordash.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Sushi order", "payload": {"item_description": "Salmon Sashimi Combo", "item_category": "food", "unit_price": 28.0, "quantity": 1, "vendor": "ubereats.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # ============ SUBSCRIPTIONS ============
    {"prompt": "Netflix subscription", "payload": {"item_description": "Netflix Standard Plan", "item_category": "subscription", "unit_price": 15.49, "quantity": 1, "vendor": "netflix.com", "currency": "USD", "fees": [], "is_recurring": True}},
    {"prompt": "Spotify Premium", "payload": {"item_description": "Spotify Premium Individual", "item_category": "subscription", "unit_price": 11.99, "quantity": 1, "vendor": "spotify.com", "currency": "USD", "fees": [], "is_recurring": True}},
    {"prompt": "YouTube Premium", "payload": {"item_description": "YouTube Premium", "item_category": "subscription", "unit_price": 13.99, "quantity": 1, "vendor": "youtube.com", "currency": "USD", "fees": [], "is_recurring": True}},
    {"prompt": "Disney+ subscription", "payload": {"item_description": "Disney+ Monthly", "item_category": "subscription", "unit_price": 13.99, "quantity": 1, "vendor": "disneyplus.com", "currency": "USD", "fees": [], "is_recurring": True}},
    {"prompt": "HBO Max", "payload": {"item_description": "Max Ad-Free Monthly", "item_category": "subscription", "unit_price": 15.99, "quantity": 1, "vendor": "max.com", "currency": "USD", "fees": [], "is_recurring": True}},
    {"prompt": "Apple Music", "payload": {"item_description": "Apple Music Individual", "item_category": "subscription", "unit_price": 10.99, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": True}},
    {"prompt": "Amazon Prime", "payload": {"item_description": "Amazon Prime Monthly", "item_category": "subscription", "unit_price": 14.99, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": True}},
    {"prompt": "ChatGPT Plus", "payload": {"item_description": "ChatGPT Plus Subscription", "item_category": "subscription", "unit_price": 20.0, "quantity": 1, "vendor": "openai.com", "currency": "USD", "fees": [], "is_recurring": True}},
    {"prompt": "Adobe Creative Cloud", "payload": {"item_description": "Adobe Creative Cloud All Apps", "item_category": "subscription", "unit_price": 59.99, "quantity": 1, "vendor": "adobe.com", "currency": "USD", "fees": [], "is_recurring": True}},

    # ============ CLOTHING ============
    {"prompt": "Levi's 501 jeans", "payload": {"item_description": "Levi's 501 Original Fit Jeans", "item_category": "clothing", "unit_price": 69.50, "quantity": 1, "vendor": "levi.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "North Face jacket", "payload": {"item_description": "The North Face Thermoball Jacket", "item_category": "clothing", "unit_price": 220.0, "quantity": 1, "vendor": "thenorthface.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Uniqlo t-shirts", "payload": {"item_description": "Uniqlo Supima Cotton T-Shirt 3 Pack", "item_category": "clothing", "unit_price": 45.0, "quantity": 1, "vendor": "uniqlo.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Patagonia fleece", "payload": {"item_description": "Patagonia Better Sweater Fleece", "item_category": "clothing", "unit_price": 149.0, "quantity": 1, "vendor": "patagonia.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "H&M basics", "payload": {"item_description": "H&M Basic T-Shirt 5 Pack", "item_category": "clothing", "unit_price": 29.99, "quantity": 1, "vendor": "hm.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Gap hoodie", "payload": {"item_description": "Gap Logo Fleece Hoodie", "item_category": "clothing", "unit_price": 59.95, "quantity": 1, "vendor": "gap.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # ============ BOOKS/MEDIA ============
    {"prompt": "Kindle book", "payload": {"item_description": "Kindle eBook", "item_category": "books", "unit_price": 14.99, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Audible audiobook", "payload": {"item_description": "Audible Audiobook Credit", "item_category": "books", "unit_price": 14.95, "quantity": 1, "vendor": "audible.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Barnes Noble book", "payload": {"item_description": "Hardcover Book", "item_category": "books", "unit_price": 27.99, "quantity": 1, "vendor": "barnesandnoble.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # ============ HOME/FURNITURE ============
    {"prompt": "Dyson vacuum", "payload": {"item_description": "Dyson V15 Detect", "item_category": "home", "unit_price": 749.0, "quantity": 1, "vendor": "dyson.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "IKEA desk", "payload": {"item_description": "IKEA BEKANT Desk", "item_category": "furniture", "unit_price": 349.0, "quantity": 1, "vendor": "ikea.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Wayfair couch", "payload": {"item_description": "Wayfair 3-Seater Sofa", "item_category": "furniture", "unit_price": 599.0, "quantity": 1, "vendor": "wayfair.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Instant Pot", "payload": {"item_description": "Instant Pot Duo 7-in-1", "item_category": "home", "unit_price": 89.0, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "Roomba vacuum", "payload": {"item_description": "iRobot Roomba i7+", "item_category": "home", "unit_price": 799.0, "quantity": 1, "vendor": "irobot.com", "currency": "USD", "fees": [], "is_recurring": False}},

    # ============ CRYPTO (LEGITIMATE) ============
    {"prompt": "$500 Bitcoin", "payload": {"item_description": "Bitcoin (BTC)", "item_category": "cryptocurrency", "unit_price": 500.0, "quantity": 1, "vendor": "coinbase.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$1000 Ethereum", "payload": {"item_description": "Ethereum (ETH)", "item_category": "cryptocurrency", "unit_price": 1000.0, "quantity": 1, "vendor": "kraken.com", "currency": "USD", "fees": [], "is_recurring": False}},
    {"prompt": "$100 USDC", "payload": {"item_description": "USD Coin (USDC)", "item_category": "cryptocurrency", "unit_price": 100.0, "quantity": 1, "vendor": "coinbase.com", "currency": "USD", "fees": [], "is_recurring": False}},
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

    # Generate examples - 1500 to balance ~4000 attacks
    examples = generate_legitimate_dataset(1500)
    print(f"Generated {len(examples)} legitimate examples")
    print(f"Templates used: {len(LEGITIMATE_TRANSACTIONS)}")

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
