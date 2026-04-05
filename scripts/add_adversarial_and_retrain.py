"""Add real-world adversarial cases to training data and retrain."""
import json
import subprocess
import sys

cases = [
    # === PRODUCT SUBSTITUTION ATTACKS (cheap version of requested item) ===
    {"text": 'electronics 1200.0 brand:Apple | {"item_description": "Apple iPad 9th Gen 64GB WiFi", "item_category": "electronics", "unit_price": 329.0, "vendor": "apple.com"}', "label": "attack"},
    {"text": 'electronics 350.0 brand:Sony | {"item_description": "Sony MDR-ZX110 On-Ear Headphones", "item_category": "electronics", "unit_price": 12.99, "vendor": "amazon.com"}', "label": "attack"},
    {"text": 'electronics 999.0 brand:Samsung | {"item_description": "Samsung Galaxy A15 5G 128GB", "item_category": "electronics", "unit_price": 159.0, "vendor": "samsung.com"}', "label": "attack"},
    {"text": 'electronics 400.0 brand:Bose | {"item_description": "Bose-Compatible Bluetooth Earbuds TWS", "item_category": "electronics", "unit_price": 19.99, "vendor": "amazon.com"}', "label": "attack"},
    {"text": 'electronics 300.0 brand:Dyson | {"item_description": "Dyson-Type Cordless Vacuum V8 Compatible", "item_category": "electronics", "unit_price": 49.0, "vendor": "home-deals.shop"}', "label": "attack"},
    {"text": 'electronics 250.0 brand:Nintendo | {"item_description": "Nintendo Switch Lite - Used Refurb", "item_category": "electronics", "unit_price": 89.0, "vendor": "game-deals-outlet.com"}', "label": "attack"},

    # === SAME VENDOR WRONG PRODUCT ===
    {"text": 'gift_card 50.0 brand:Amazon | {"item_description": "Amazon Web Services Credits $50", "item_category": "gift_card", "unit_price": 50.0, "vendor": "amazon.com"}', "label": "attack"},
    {"text": 'gift_card 50.0 brand:Amazon | {"item_description": "Kindle Unlimited 12 Month Subscription", "item_category": "gift_card", "unit_price": 49.99, "vendor": "amazon.com"}', "label": "attack"},
    {"text": 'gift_card 50.0 brand:Amazon | {"item_description": "Amazon Prime Annual Membership", "item_category": "gift_card", "unit_price": 49.0, "vendor": "amazon.com"}', "label": "attack"},
    {"text": 'subscription 15.0 | {"item_description": "Netflix Premium 4K UHD Plan", "item_category": "subscription", "unit_price": 22.99, "vendor": "netflix.com"}', "label": "attack"},

    # === VAGUE / STRIPPED DESCRIPTIONS ===
    {"text": 'electronics 200.0 brand:JBL | {"item_description": "Item - Standard", "item_category": "electronics", "unit_price": 199.0, "vendor": "unknown"}', "label": "attack"},
    {"text": 'shoes 150.0 brand:Nike | {"item_description": "Athletic Footwear - Size 10", "item_category": "shoes", "unit_price": 140.0, "vendor": "shoes-outlet.com"}', "label": "attack"},
    {"text": 'electronics 500.0 | {"item_description": "Product SKU-44891", "item_category": "electronics", "unit_price": 499.0, "vendor": "store.example.com"}', "label": "attack"},
    {"text": 'clothing 200.0 brand:Gucci | {"item_description": "Designer Item - Premium", "item_category": "clothing", "unit_price": 195.0, "vendor": "luxury-outlet.net"}', "label": "attack"},

    # === SCAM PATTERNS ===
    {"text": 'gift_card 100.0 | {"item_description": "Urgent Hurricane Relief Fund - Verified Charity", "item_category": "donation", "unit_price": 100.0, "vendor": "relief-fund-donate.org"}', "label": "attack"},
    {"text": 'gift_card 200.0 | {"item_description": "Account Verification Required - Apple ID Security", "item_category": "gift_card", "unit_price": 200.0, "vendor": "apple-verify.com"}', "label": "attack"},
    {"text": 'gift_card 50.0 | {"item_description": "Refund Processing - Order 8834 Store Credit", "item_category": "gift_card", "unit_price": 50.0, "vendor": "refund-process.com"}', "label": "attack"},
    {"text": 'electronics 500.0 | {"item_description": "Digital Asset Portfolio Starter Package", "item_category": "electronics", "unit_price": 500.0, "vendor": "coinbase.com"}', "label": "attack"},

    # === PRICE TOO GOOD TO BE TRUE ===
    {"text": 'electronics 500.0 | {"item_description": "DJI Mini 4 Pro Drone with RC2", "item_category": "electronics", "unit_price": 45.0, "vendor": "deals-electronics-usa.com"}', "label": "attack"},
    {"text": 'clothing 2000.0 brand:Canada_Goose | {"item_description": "Canada Goose Expedition Parka", "item_category": "clothing", "unit_price": 89.0, "vendor": "outlet-luxury.shop"}', "label": "attack"},
    {"text": 'subscription 9.99 | {"item_description": "Premium VPN Identity Protection Bundle", "item_category": "subscription", "unit_price": 9.99, "vendor": "securevpn-protect.com"}', "label": "attack"},
    {"text": 'gift_card 25.0 | {"item_description": "Gift Card Balance Check and Transfer Service", "item_category": "gift_card", "unit_price": 25.0, "vendor": "giftcard-balance.net"}', "label": "attack"},

    # === REAL LEGITIMATE TRANSACTIONS (model MUST learn these are OK) ===
    {"text": 'electronics 1200.0 brand:Apple | {"item_description": "Apple MacBook Air M3 15-inch 256GB", "item_category": "electronics", "unit_price": 1199.0, "vendor": "apple.com"}', "label": "legitimate"},
    {"text": 'electronics 350.0 brand:Sony | {"item_description": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones", "item_category": "electronics", "unit_price": 348.0, "vendor": "amazon.com"}', "label": "legitimate"},
    {"text": 'electronics 999.0 brand:Samsung | {"item_description": "Samsung Galaxy S24 Ultra 256GB Titanium", "item_category": "electronics", "unit_price": 979.0, "vendor": "samsung.com"}', "label": "legitimate"},
    {"text": 'electronics 400.0 brand:Bose | {"item_description": "Bose QuietComfort Ultra Headphones Black", "item_category": "electronics", "unit_price": 379.0, "vendor": "bose.com"}', "label": "legitimate"},
    {"text": 'gift_card 50.0 brand:Amazon | {"item_description": "Amazon Gift Card $50 Value eDelivery", "item_category": "gift_card", "unit_price": 50.0, "vendor": "amazon.com"}', "label": "legitimate"},
    {"text": 'electronics 200.0 brand:JBL | {"item_description": "JBL Charge 5 Portable Bluetooth Speaker Teal", "item_category": "electronics", "unit_price": 179.95, "vendor": "jbl.com"}', "label": "legitimate"},
    {"text": 'shoes 150.0 brand:Nike | {"item_description": "Nike Air Force 1 07 White Mens Size 10", "item_category": "shoes", "unit_price": 115.0, "vendor": "nike.com"}', "label": "legitimate"},
    {"text": 'gift_card 100.0 | {"item_description": "American Red Cross Disaster Relief Donation", "item_category": "donation", "unit_price": 100.0, "vendor": "redcross.org"}', "label": "legitimate"},
    {"text": 'electronics 500.0 | {"item_description": "DJI Mini 4 Pro Fly More Combo Bundle", "item_category": "electronics", "unit_price": 489.0, "vendor": "dji.com"}', "label": "legitimate"},
    {"text": 'clothing 2000.0 brand:Canada_Goose | {"item_description": "Canada Goose Expedition Parka Heritage Black Label", "item_category": "clothing", "unit_price": 1695.0, "vendor": "canadagoose.com"}', "label": "legitimate"},
    {"text": 'electronics 500.0 | {"item_description": "Ledger Nano X Crypto Hardware Wallet", "item_category": "electronics", "unit_price": 149.0, "vendor": "ledger.com"}', "label": "legitimate"},
    {"text": 'gift_card 200.0 brand:Apple | {"item_description": "Apple Store Gift Card $200 Physical", "item_category": "gift_card", "unit_price": 200.0, "vendor": "apple.com"}', "label": "legitimate"},
    {"text": 'subscription 10.99 | {"item_description": "Spotify Premium Individual Monthly Plan", "item_category": "subscription", "unit_price": 10.99, "vendor": "spotify.com"}', "label": "legitimate"},
    {"text": 'electronics 80.0 | {"item_description": "Anker PowerCore 26800mAh Portable Charger USB-C", "item_category": "electronics", "unit_price": 65.99, "vendor": "amazon.com"}', "label": "legitimate"},
    {"text": 'clothing 60.0 brand:Uniqlo | {"item_description": "Uniqlo Ultra Light Down Jacket Mens Navy", "item_category": "clothing", "unit_price": 59.90, "vendor": "uniqlo.com"}', "label": "legitimate"},
    {"text": 'food 30.0 | {"item_description": "DoorDash Order - Thai Basil Restaurant Pad Thai", "item_category": "food", "unit_price": 28.50, "vendor": "doordash.com"}', "label": "legitimate"},
    {"text": 'travel 250.0 | {"item_description": "United Airlines LAX to SFO Round Trip Economy", "item_category": "flight", "unit_price": 234.0, "vendor": "united.com"}', "label": "legitimate"},
    {"text": 'gift_card 25.0 brand:Starbucks | {"item_description": "Starbucks Gift Card $25 Digital", "item_category": "gift_card", "unit_price": 25.0, "vendor": "starbucks.com"}', "label": "legitimate"},
    {"text": 'electronics 1500.0 brand:Apple | {"item_description": "Apple iPhone 15 Pro Max 256GB Natural Titanium", "item_category": "electronics", "unit_price": 1199.0, "vendor": "apple.com"}', "label": "legitimate"},
    {"text": 'subscription 15.0 | {"item_description": "Netflix Standard with Ads Monthly", "item_category": "subscription", "unit_price": 6.99, "vendor": "netflix.com"}', "label": "legitimate"},
    {"text": 'electronics 100.0 | {"item_description": "Logitech MX Master 3S Wireless Mouse", "item_category": "electronics", "unit_price": 99.99, "vendor": "logitech.com"}', "label": "legitimate"},
    {"text": 'shoes 200.0 brand:Adidas | {"item_description": "Adidas Ultraboost Light Running Shoes Size 11", "item_category": "shoes", "unit_price": 190.0, "vendor": "adidas.com"}', "label": "legitimate"},
    {"text": 'gift_card 50.0 brand:Steam | {"item_description": "Steam Wallet Gift Card $50 Digital Code", "item_category": "gift_card", "unit_price": 50.0, "vendor": "store.steampowered.com"}', "label": "legitimate"},
]

# Count
attacks = sum(1 for c in cases if c["label"] == "attack")
legit = len(cases) - attacks
print(f"Adding {len(cases)} real-world cases ({attacks} attacks, {legit} legitimate)")

# Append to training data
with open("data/training_data.jsonl", "a") as f:
    for c in cases:
        f.write(json.dumps(c) + "\n")

print(f"Appended to data/training_data.jsonl")
print("Retraining classifier...")

# Retrain
subprocess.run([sys.executable, "scripts/train_classifier.py"], check=True)
