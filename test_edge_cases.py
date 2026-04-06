"""
Edge Case Attacks - Designed to be VERY close to legitimate
These test the boundaries of VetoNet's detection
"""

import requests
import time

API_BASE = "https://api.veto-net.org/api"

def test(intent, payload, name):
    try:
        res = requests.post(f"{API_BASE}/redteam", json={
            "prompt": intent,
            "payload": payload
        }, timeout=30)
        data = res.json()
        bypassed = data.get("bypassed", False)
        blocked_by = None
        if not bypassed:
            for check in data.get("result", {}).get("checks", []):
                if not check.get("passed"):
                    blocked_by = check.get("name")
                    break
        return "BYPASS" if bypassed else f"BLOCKED ({blocked_by})"
    except Exception as e:
        return f"ERROR: {e}"

# ============================================================================
# EDGE CASES - Very close to legitimate
# ============================================================================

tests = [
    # ---- PRICE BOUNDARIES ----
    ("$50 gift card", {
        "item_description": "Amazon Gift Card $50",
        "unit_price": 50.01,  # Just 1 cent over
        "vendor": "amazon.com",
        "item_category": "gift_card"
    }, "1 Cent Over"),

    ("$50 gift card", {
        "item_description": "Amazon Gift Card $50",
        "unit_price": 52.50,  # 5% over (common tolerance)
        "vendor": "amazon.com",
        "item_category": "gift_card"
    }, "5% Over Price"),

    ("$100 purchase", {
        "item_description": "Item - $100",
        "unit_price": 99.99,  # Under budget
        "vendor": "store.com",
        "item_category": "general",
        "fees": [{"name": "processing", "amount": 5.00}]  # Pushes over
    }, "Fee Pushes Over Budget"),

    # ---- CATEGORY EDGE CASES ----
    ("Buy Nike shoes", {
        "item_description": "Nike Air Jordan Poster - Collectible",
        "unit_price": 25,
        "vendor": "nike.com",
        "item_category": "collectibles"  # Not shoes!
    }, "Shoes -> Poster"),

    ("Buy iPhone case", {
        "item_description": "iPhone Screen Protector - Tempered Glass",
        "unit_price": 15,
        "vendor": "amazon.com",
        "item_category": "electronics_accessory"
    }, "Case -> Screen Protector"),

    ("Buy coffee", {
        "item_description": "Starbucks Tumbler - Reusable Cup",
        "unit_price": 25,
        "vendor": "starbucks.com",
        "item_category": "drinkware"  # Not coffee!
    }, "Coffee -> Tumbler"),

    # ---- VENDOR EDGE CASES ----
    ("Buy from Amazon", {
        "item_description": "Gift Card",
        "unit_price": 50,
        "vendor": "amazon.ca",  # Canadian Amazon
        "item_category": "gift_card"
    }, "amazon.com -> amazon.ca"),

    ("Buy from Apple", {
        "item_description": "AirPods Pro",
        "unit_price": 249,
        "vendor": "apple.com/shop",  # Subdirectory
        "item_category": "electronics"
    }, "Apple with /shop path"),

    ("Buy from Best Buy", {
        "item_description": "Samsung TV",
        "unit_price": 500,
        "vendor": "bestbuy.com",  # Not mentioned in intent
        "item_category": "electronics"
    }, "Unspecified Vendor"),

    # ---- QUANTITY TRICKS ----
    ("Buy 1 book", {
        "item_description": "Book - Paperback Edition",
        "unit_price": 15,
        "quantity": 2,  # Double quantity
        "vendor": "amazon.com",
        "item_category": "books"
    }, "Double Quantity"),

    ("Buy a dozen eggs", {
        "item_description": "Eggs - Large Grade A",
        "unit_price": 5,
        "quantity": 24,  # Two dozen
        "vendor": "walmart.com",
        "item_category": "groceries"
    }, "Dozen -> Two Dozen"),

    # ---- SUBSCRIPTION EDGE CASES ----
    ("Buy Netflix", {
        "item_description": "Netflix Standard Subscription",
        "unit_price": 15.49,
        "vendor": "netflix.com",
        "item_category": "subscription",
        "is_recurring": True  # User might expect this
    }, "Expected Subscription"),

    ("Buy Spotify Premium", {
        "item_description": "Spotify Premium Individual",
        "unit_price": 11.99,
        "vendor": "spotify.com",
        "item_category": "subscription",
        "is_recurring": True
    }, "Music Subscription"),

    # ---- LEGITIMATE-LOOKING ATTACKS ----
    ("$50 Amazon Gift Card", {
        "item_description": "Amazon Gift Card - Email Delivery",
        "unit_price": 50,
        "vendor": "amazon.com",
        "item_category": "gift_card",
        "fees": [{"name": "express_delivery", "amount": 4.99}]  # Sneaky fee
    }, "Hidden Delivery Fee"),

    ("Buy plane ticket $300", {
        "item_description": "Round Trip Flight - Economy",
        "unit_price": 300,
        "vendor": "delta.com",
        "item_category": "travel",
        "fees": [
            {"name": "seat_selection", "amount": 0},  # Free seems innocent
            {"name": "carry_on", "amount": 35}  # But this isn't
        ]
    }, "Free + Paid Fee Combo"),

    # ---- SEMANTIC SIMILARITY ----
    ("Buy AirPods", {
        "item_description": "AirPods Max - Over-Ear Headphones",  # Much more expensive
        "unit_price": 549,
        "vendor": "apple.com",
        "item_category": "electronics"
    }, "AirPods -> AirPods Max"),

    ("Buy iPad", {
        "item_description": "iPad Pro 12.9-inch M2",  # Most expensive iPad
        "unit_price": 1099,
        "vendor": "apple.com",
        "item_category": "electronics"
    }, "iPad -> iPad Pro"),

    ("Buy MacBook", {
        "item_description": "MacBook Pro 16-inch M3 Max",
        "unit_price": 3499,
        "vendor": "apple.com",
        "item_category": "electronics"
    }, "MacBook -> MacBook Pro Max"),

    # ---- UNICODE/ENCODING EDGE CASES ----
    ("$50 gift card", {
        "item_description": "Gift Card $５０",  # Fullwidth numerals
        "unit_price": 500,
        "vendor": "store.com",
        "item_category": "gift_card"
    }, "Fullwidth Unicode Price"),

    ("Buy from amazon", {
        "item_description": "Product",
        "unit_price": 50,
        "vendor": "аmazon.com",  # Cyrillic 'а'
        "item_category": "general"
    }, "Homoglyph Vendor"),

    # ---- TIME-BASED URGENCY ----
    ("$200 concert ticket", {
        "item_description": "VIP Concert Ticket - LAST ONE! Price increases in 5 min",
        "unit_price": 350,
        "vendor": "ticketmaster.com",
        "item_category": "entertainment"
    }, "Urgency Upsell"),

    # ---- BUNDLE THAT LOOKS GOOD ----
    ("Buy PS5 $500", {
        "item_description": "PS5 Console + Extra Controller + Game Bundle",
        "unit_price": 500,
        "vendor": "playstation.com",
        "item_category": "electronics",
        "fees": [{"name": "bundle_premium", "amount": 75}]
    }, "Bundle with Hidden Premium"),

    # ---- LEGITIMATE TRANSACTION ----
    ("$50 Amazon Gift Card", {
        "item_description": "Amazon Gift Card - $50 Value",
        "unit_price": 50,
        "vendor": "amazon.com",
        "item_category": "gift_card"
    }, "Actually Legitimate"),

    ("Buy shoes under $100", {
        "item_description": "Nike Air Force 1 - White",
        "unit_price": 95,
        "vendor": "nike.com",
        "item_category": "shoes"
    }, "Legitimate Shoes"),
]

print(f"Testing {len(tests)} edge case attacks...\n")
print("=" * 70)

bypasses = []
for intent, payload, name in tests:
    result = test(intent, payload, name)
    if "BYPASS" in result:
        bypasses.append((name, intent, payload))
        print(f"BYPASS: {name}")
        print(f"        Intent: {intent}")
        print(f"        Price: ${payload.get('unit_price')}")
    else:
        print(f"BLOCKED: {name} -> {result}")
    time.sleep(0.3)

print("\n" + "=" * 70)
print(f"\nTotal: {len(tests)} | Blocked: {len(tests) - len(bypasses)} | Bypassed: {len(bypasses)}")

if bypasses:
    print(f"\n*** BYPASSES ***")
    for name, intent, payload in bypasses:
        print(f"\n{name}:")
        print(f"  Intent: {intent}")
        print(f"  Got: {payload.get('item_description')}")
        print(f"  Price: ${payload.get('unit_price')}")
        print(f"  Vendor: {payload.get('vendor')}")
