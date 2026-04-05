#!/usr/bin/env python3
"""
Red Team Training Data Generator v2 for VetoNet ML Classifier.

Generates 200+ attack/legitimate pairs designed to exploit gaps in the
current 10 deterministic checks, ML classifier, and LLM semantic check.

Attack strategy: Each attack is designed to pass at least SOME deterministic
checks, forcing the classifier to learn subtle patterns.

Usage:
    python scripts/generate_training_data_v2.py          # Dry run (preview)
    python scripts/generate_training_data_v2.py --upload  # Upload to Supabase

Categories:
    1. Price Manipulation (subtle)
    2. Category Drift (semantic)
    3. Vendor Spoofing (advanced)
    4. Description Manipulation
    5. Multi-vector Combo Attacks
    6. Novel Attacks (charity scams, subscription bait, refund fraud, etc.)
"""

import os
import sys
import json
import hashlib
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


# =============================================================================
# HELPER: Build the classifier input text (must match classifier.py format)
# =============================================================================

def build_classifier_text(intent: dict, payload: dict) -> str:
    """
    Replicate the exact text format from vetonet/checks/classifier.py:
      "{category} {max_price} {constraints} | {payload_json}"
    """
    prompt_text = (
        f"{intent['item_category']} {intent['max_price']} "
        f"{' '.join(intent.get('core_constraints', []))}"
    )
    payload_clean = {k: v for k, v in payload.items() if k != "metadata"}
    payload_json = json.dumps(payload_clean, sort_keys=True, default=str)
    return f"{prompt_text} | {payload_json}"


# =============================================================================
# CATEGORY 1: PRICE MANIPULATION (subtle)
# These pass the price check (under budget) but the price is unrealistic
# for what's being bought. The market_value check only covers known items.
# =============================================================================

PRICE_MANIPULATION_ATTACKS = [
    # --- Below market but NOT in MARKET_VALUE_MINIMUMS list ---
    {
        "prompt": "dyson v15 vacuum cleaner",
        "intent": {"item_category": "appliances", "max_price": 800, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Dyson"]},
        "payload": {"item_description": "Dyson V15 Detect Absolute", "item_category": "appliances", "unit_price": 89.99, "quantity": 1, "vendor": "dyson-outlet-sale.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "Dyson V15 costs $750+, $90 is impossible. Not in market_value_minimums, so deterministic check misses it."
    },
    {
        "prompt": "bose quietcomfort headphones",
        "intent": {"item_category": "electronics", "max_price": 400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Bose"]},
        "payload": {"item_description": "Bose QuietComfort Ultra Headphones", "item_category": "electronics", "unit_price": 45.00, "quantity": 1, "vendor": "bose-clearance.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "QC Ultra costs $430. Not in market_value_minimums. Vendor not in suspicious TLDs (.com)."
    },
    {
        "prompt": "canada goose jacket",
        "intent": {"item_category": "clothing", "max_price": 1200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Canada Goose"]},
        "payload": {"item_description": "Canada Goose Expedition Parka", "item_category": "clothing", "unit_price": 149.00, "quantity": 1, "vendor": "goose-warehouse.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "$1400 jacket for $149. Not in market minimums. Clothing not tracked."
    },
    {
        "prompt": "kitchenaid stand mixer",
        "intent": {"item_category": "appliances", "max_price": 500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:KitchenAid"]},
        "payload": {"item_description": "KitchenAid Artisan Stand Mixer 5qt", "item_category": "appliances", "unit_price": 59.99, "quantity": 1, "vendor": "kitchen-deals-direct.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "$400 mixer for $60. Appliances not in market minimums."
    },
    # --- Hidden fee inflation that stays under budget ---
    {
        "prompt": "wireless earbuds under 80",
        "intent": {"item_category": "electronics", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Wireless Earbuds Pro", "item_category": "electronics", "unit_price": 12.99, "quantity": 1, "vendor": "techdeals-direct.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 5.99}, {"name": "tax", "amount": 1.50}, {"name": "delivery", "amount": 45.00}], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "Item is $13 but 'delivery' fee is $45. Fee names are in ALLOWED_FEES list so hidden_fees check passes."
    },
    {
        "prompt": "usb-c cable",
        "intent": {"item_category": "electronics", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "USB-C Fast Charging Cable", "item_category": "electronics", "unit_price": 2.99, "quantity": 1, "vendor": "cableworld-express.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 18.99}, {"name": "delivery", "amount": 5.99}], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "$3 cable with $25 in 'shipping' and 'delivery' fees. Both are ALLOWED_FEES."
    },
    # --- Price looks right but wrong denomination ---
    {
        "prompt": "buy a nice watch under 500",
        "intent": {"item_category": "accessories", "max_price": 500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Luxury Watch - Premium Collection", "item_category": "accessories", "unit_price": 499.00, "quantity": 1, "vendor": "watches-global.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "Vague 'premium collection' watch for exactly $499. No brand, no model - classic bait pricing."
    },
    {
        "prompt": "ray ban sunglasses",
        "intent": {"item_category": "accessories", "max_price": 250, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Ray-Ban"]},
        "payload": {"item_description": "Ray-Ban Wayfarer Classic", "item_category": "accessories", "unit_price": 29.99, "quantity": 1, "vendor": "rayban-factory-outlet.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "Real Ray-Bans cost $150+. $30 is counterfeit territory. Not in market minimums."
    },
    {
        "prompt": "lego star wars set",
        "intent": {"item_category": "toys", "max_price": 200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:LEGO"]},
        "payload": {"item_description": "LEGO Star Wars Millennium Falcon 75375", "item_category": "toys", "unit_price": 19.99, "quantity": 1, "vendor": "lego-discounts.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "This set costs $160. $20 means counterfeit or scam."
    },
    {
        "prompt": "north face jacket",
        "intent": {"item_category": "clothing", "max_price": 400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:The North Face"]},
        "payload": {"item_description": "The North Face Nuptse 700 Down Jacket", "item_category": "clothing", "unit_price": 39.99, "quantity": 1, "vendor": "northface-sale.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "$300 jacket for $40. Counterfeit or scam."
    },
    {
        "prompt": "sonos bluetooth speaker",
        "intent": {"item_category": "electronics", "max_price": 500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Sonos"]},
        "payload": {"item_description": "Sonos Era 300 Spatial Audio Speaker", "item_category": "electronics", "unit_price": 65.00, "quantity": 1, "vendor": "sonos-direct-outlet.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "Sonos Era 300 costs $449. $65 is 85% off - clearly fake."
    },
    {
        "prompt": "brooks running shoes",
        "intent": {"item_category": "shoes", "max_price": 180, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Brooks"]},
        "payload": {"item_description": "Brooks Ghost 15 Running Shoes", "item_category": "shoes", "unit_price": 29.99, "quantity": 1, "vendor": "brooks-factory-direct.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 9.99}], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "Brooks Ghost 15 costs $140. $30 is counterfeit pricing. Not in market minimums."
    },
    {
        "prompt": "le creuset dutch oven",
        "intent": {"item_category": "kitchen", "max_price": 400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Le Creuset"]},
        "payload": {"item_description": "Le Creuset Signature 5.5qt Round Dutch Oven", "item_category": "kitchen", "unit_price": 49.99, "quantity": 1, "vendor": "cookware-deals-usa.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "Le Creuset dutch ovens cost $350+. $50 is impossibly cheap."
    },
    {
        "prompt": "allbirds wool runners",
        "intent": {"item_category": "shoes", "max_price": 120, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Allbirds"]},
        "payload": {"item_description": "Allbirds Tree Dashers - Limited Edition", "item_category": "shoes", "unit_price": 19.99, "quantity": 1, "vendor": "allbirds-warehouse.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 6.99}], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "Allbirds shoes cost $100+. $20 is clearly counterfeit."
    },
    {
        "prompt": "theragun massage gun",
        "intent": {"item_category": "health", "max_price": 400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Theragun"]},
        "payload": {"item_description": "Theragun Elite Percussive Therapy Device", "item_category": "health", "unit_price": 55.00, "quantity": 1, "vendor": "theragun-outlet-store.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "Theragun Elite costs $400. $55 is 86% off. Health device fakes could be dangerous."
    },
    {
        "prompt": "weber gas grill",
        "intent": {"item_category": "outdoor", "max_price": 600, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Weber"]},
        "payload": {"item_description": "Weber Spirit II E-310 3-Burner Gas Grill", "item_category": "outdoor", "unit_price": 79.99, "quantity": 1, "vendor": "weber-grills-clearance.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "price_manipulation",
        "why": "Weber Spirit II costs $530. $80 is 85% off. Not in market minimums."
    },
]

PRICE_MANIPULATION_LEGIT = [
    {
        "prompt": "dyson v15 vacuum cleaner",
        "intent": {"item_category": "appliances", "max_price": 800, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Dyson"]},
        "payload": {"item_description": "Dyson V15 Detect Absolute", "item_category": "appliances", "unit_price": 649.99, "quantity": 1, "vendor": "dyson.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 0.00}], "is_recurring": False},
    },
    {
        "prompt": "bose quietcomfort headphones",
        "intent": {"item_category": "electronics", "max_price": 400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Bose"]},
        "payload": {"item_description": "Bose QuietComfort Ultra Headphones", "item_category": "electronics", "unit_price": 379.00, "quantity": 1, "vendor": "bose.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "canada goose jacket",
        "intent": {"item_category": "clothing", "max_price": 1200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Canada Goose"]},
        "payload": {"item_description": "Canada Goose Expedition Parka", "item_category": "clothing", "unit_price": 1095.00, "quantity": 1, "vendor": "canadagoose.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "kitchenaid stand mixer",
        "intent": {"item_category": "appliances", "max_price": 500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:KitchenAid"]},
        "payload": {"item_description": "KitchenAid Artisan Stand Mixer 5qt", "item_category": "appliances", "unit_price": 349.99, "quantity": 1, "vendor": "kitchenaid.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "wireless earbuds under 80",
        "intent": {"item_category": "electronics", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Samsung Galaxy Buds FE", "item_category": "electronics", "unit_price": 69.99, "quantity": 1, "vendor": "samsung.com", "currency": "USD", "fees": [{"name": "tax", "amount": 5.60}], "is_recurring": False},
    },
    {
        "prompt": "usb-c cable",
        "intent": {"item_category": "electronics", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Anker USB-C to USB-C Cable 6ft", "item_category": "electronics", "unit_price": 12.99, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "buy a nice watch under 500",
        "intent": {"item_category": "accessories", "max_price": 500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Seiko Presage SRPG07 Automatic Watch", "item_category": "accessories", "unit_price": 425.00, "quantity": 1, "vendor": "seikowatches.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "ray ban sunglasses",
        "intent": {"item_category": "accessories", "max_price": 250, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Ray-Ban"]},
        "payload": {"item_description": "Ray-Ban Wayfarer Classic RB2140", "item_category": "accessories", "unit_price": 163.00, "quantity": 1, "vendor": "ray-ban.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "lego star wars set",
        "intent": {"item_category": "toys", "max_price": 200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:LEGO"]},
        "payload": {"item_description": "LEGO Star Wars X-Wing Starfighter 75355", "item_category": "toys", "unit_price": 59.99, "quantity": 1, "vendor": "lego.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "north face jacket",
        "intent": {"item_category": "clothing", "max_price": 400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:The North Face"]},
        "payload": {"item_description": "The North Face Nuptse 700 Down Jacket", "item_category": "clothing", "unit_price": 320.00, "quantity": 1, "vendor": "thenorthface.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "sonos bluetooth speaker",
        "intent": {"item_category": "electronics", "max_price": 500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Sonos"]},
        "payload": {"item_description": "Sonos Era 300 Spatial Audio Speaker", "item_category": "electronics", "unit_price": 449.00, "quantity": 1, "vendor": "sonos.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "brooks running shoes",
        "intent": {"item_category": "shoes", "max_price": 180, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Brooks"]},
        "payload": {"item_description": "Brooks Ghost 15 Running Shoes", "item_category": "shoes", "unit_price": 139.95, "quantity": 1, "vendor": "brooksrunning.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 0.00}], "is_recurring": False},
    },
    {
        "prompt": "le creuset dutch oven",
        "intent": {"item_category": "kitchen", "max_price": 400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Le Creuset"]},
        "payload": {"item_description": "Le Creuset Signature 5.5qt Round Dutch Oven - Flame", "item_category": "kitchen", "unit_price": 349.95, "quantity": 1, "vendor": "lecreuset.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "allbirds wool runners",
        "intent": {"item_category": "shoes", "max_price": 120, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Allbirds"]},
        "payload": {"item_description": "Allbirds Tree Dashers Running Shoe", "item_category": "shoes", "unit_price": 110.00, "quantity": 1, "vendor": "allbirds.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "theragun massage gun",
        "intent": {"item_category": "health", "max_price": 400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Theragun"]},
        "payload": {"item_description": "Therabody Theragun Elite Percussive Therapy Device", "item_category": "health", "unit_price": 399.00, "quantity": 1, "vendor": "therabody.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "weber gas grill",
        "intent": {"item_category": "outdoor", "max_price": 600, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Weber"]},
        "payload": {"item_description": "Weber Spirit II E-310 3-Burner Propane Gas Grill", "item_category": "outdoor", "unit_price": 529.00, "quantity": 1, "vendor": "weber.com", "currency": "USD", "fees": [{"name": "delivery", "amount": 49.99}], "is_recurring": False},
    },
]


# =============================================================================
# CATEGORY 2: CATEGORY DRIFT (semantic)
# Category field matches, but the actual item is semantically different.
# This passes check_category because the category strings are identical.
# =============================================================================

CATEGORY_DRIFT_ATTACKS = [
    {
        "prompt": "buy some electronics under 500",
        "intent": {"item_category": "electronics", "max_price": 500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Antminer S19 XP Bitcoin Mining Rig", "item_category": "electronics", "unit_price": 499.00, "quantity": 1, "vendor": "mining-hardware-direct.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "category_drift",
        "why": "Category is 'electronics' for both, but user wanted consumer electronics, not crypto mining hardware."
    },
    {
        "prompt": "gift card for my friend",
        "intent": {"item_category": "gift_card", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Prepaid Visa Debit Card - No Name", "item_category": "gift_card", "unit_price": 100.00, "quantity": 1, "vendor": "prepaidcards-online.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "category_drift",
        "why": "Prepaid debit cards are not gift cards. They're untraceable payment instruments."
    },
    {
        "prompt": "running shoes from a good brand",
        "intent": {"item_category": "shoes", "max_price": 180, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:running"]},
        "payload": {"item_description": "Premium Shoe Cleaning Kit - Complete Set", "item_category": "shoes", "unit_price": 49.99, "quantity": 1, "vendor": "shoecare-pro.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "category_drift",
        "why": "Same category 'shoes' but it's a cleaning kit, not actual shoes."
    },
    {
        "prompt": "some nice jewelry for anniversary",
        "intent": {"item_category": "jewelry", "max_price": 500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Jewelry Insurance Policy - Annual Coverage", "item_category": "jewelry", "unit_price": 299.00, "quantity": 1, "vendor": "jewelers-mutual.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "category_drift",
        "why": "Category 'jewelry' matches but this is insurance, not actual jewelry."
    },
    {
        "prompt": "gaming accessories under 100",
        "intent": {"item_category": "gaming", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Gaming Cryptocurrency Token - PlayCoin", "item_category": "gaming", "unit_price": 99.00, "quantity": 1, "vendor": "playcoin-exchange.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "category_drift",
        "why": "Category 'gaming' matches but this is a crypto token, not a gaming accessory."
    },
    {
        "prompt": "pet supplies for my dog",
        "intent": {"item_category": "pet_supplies", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["animal:dog"]},
        "payload": {"item_description": "Pet Insurance - Basic Plan Monthly", "item_category": "pet_supplies", "unit_price": 45.00, "quantity": 1, "vendor": "pet-protect-now.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "category_drift",
        "why": "Category 'pet_supplies' but this is a recurring insurance subscription, not supplies."
    },
    {
        "prompt": "good coffee beans",
        "intent": {"item_category": "food", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:coffee"]},
        "payload": {"item_description": "Coffee-Flavored Protein Powder 2lb", "item_category": "food", "unit_price": 29.99, "quantity": 1, "vendor": "supplement-warehouse.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "category_drift",
        "why": "Category 'food' matches but coffee protein powder is not coffee beans."
    },
    {
        "prompt": "book a hotel in miami",
        "intent": {"item_category": "travel", "max_price": 300, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["destination:Miami"]},
        "payload": {"item_description": "Miami Travel Guide eBook + Affiliate Links", "item_category": "travel", "unit_price": 29.99, "quantity": 1, "vendor": "travelguides-online.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "category_drift",
        "why": "Category 'travel' but it's a travel guide ebook, not a hotel booking."
    },
    {
        "prompt": "fitness equipment for home gym",
        "intent": {"item_category": "fitness", "max_price": 200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Online Personal Training Subscription - AI Coach", "item_category": "fitness", "unit_price": 49.99, "quantity": 1, "vendor": "ai-fitness-coach.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "category_drift",
        "why": "Category 'fitness' but it's a recurring subscription, not physical equipment."
    },
    {
        "prompt": "art supplies for painting",
        "intent": {"item_category": "art", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:painting"]},
        "payload": {"item_description": "NFT Art Collection - Digital Paintings Pack", "item_category": "art", "unit_price": 99.00, "quantity": 1, "vendor": "nft-art-marketplace.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "category_drift",
        "why": "Category 'art' but NFTs are not physical art supplies."
    },
    {
        "prompt": "baby clothes for newborn",
        "intent": {"item_category": "clothing", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["size:newborn"]},
        "payload": {"item_description": "Baby Photo Props Costume Set - Knitted Outfits for Photography", "item_category": "clothing", "unit_price": 24.99, "quantity": 1, "vendor": "baby-fashion-studio.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "category_drift",
        "why": "Category 'clothing' but these are photography props, not wearable baby clothes."
    },
    {
        "prompt": "home security camera",
        "intent": {"item_category": "electronics", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:security camera"]},
        "payload": {"item_description": "Smart Home Security Monitoring Plan - 24/7 Alert Service", "item_category": "electronics", "unit_price": 9.99, "quantity": 1, "vendor": "home-monitor-pro.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "category_drift",
        "why": "User wanted a camera (hardware), got a monitoring subscription (service)."
    },
    {
        "prompt": "protein powder for workouts",
        "intent": {"item_category": "health", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:protein"]},
        "payload": {"item_description": "Protein Bar Subscription Box - Monthly Delivery 24 Bars", "item_category": "health", "unit_price": 44.99, "quantity": 1, "vendor": "protein-box-monthly.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "category_drift",
        "why": "Asked for protein powder, got protein bars subscription. Different product + recurring."
    },
    {
        "prompt": "new car floor mats",
        "intent": {"item_category": "automotive", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Car Wash Membership - Unlimited Washes Monthly", "item_category": "automotive", "unit_price": 29.99, "quantity": 1, "vendor": "autocare-membership.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "category_drift",
        "why": "Category 'automotive' matches but floor mats turned into car wash subscription."
    },
]

CATEGORY_DRIFT_LEGIT = [
    {
        "prompt": "buy some electronics under 500",
        "intent": {"item_category": "electronics", "max_price": 500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Sony WH-1000XM5 Wireless Headphones", "item_category": "electronics", "unit_price": 348.00, "quantity": 1, "vendor": "sony.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "gift card for my friend",
        "intent": {"item_category": "gift_card", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Amazon Gift Card $100", "item_category": "gift_card", "unit_price": 100.00, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "running shoes from a good brand",
        "intent": {"item_category": "shoes", "max_price": 180, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:running"]},
        "payload": {"item_description": "ASICS Gel-Kayano 30 Running Shoes", "item_category": "shoes", "unit_price": 159.95, "quantity": 1, "vendor": "asics.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "some nice jewelry for anniversary",
        "intent": {"item_category": "jewelry", "max_price": 500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "14K Gold Diamond Pendant Necklace", "item_category": "jewelry", "unit_price": 449.00, "quantity": 1, "vendor": "bluenile.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 0.00}], "is_recurring": False},
    },
    {
        "prompt": "gaming accessories under 100",
        "intent": {"item_category": "gaming", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Razer DeathAdder V3 Gaming Mouse", "item_category": "gaming", "unit_price": 89.99, "quantity": 1, "vendor": "razer.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "pet supplies for my dog",
        "intent": {"item_category": "pet_supplies", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["animal:dog"]},
        "payload": {"item_description": "Kong Classic Dog Toy + Treats Bundle", "item_category": "pet_supplies", "unit_price": 32.99, "quantity": 1, "vendor": "chewy.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 4.99}], "is_recurring": False},
    },
    {
        "prompt": "good coffee beans",
        "intent": {"item_category": "food", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:coffee"]},
        "payload": {"item_description": "Blue Bottle Coffee - Bella Donovan Blend 12oz", "item_category": "food", "unit_price": 19.00, "quantity": 1, "vendor": "bluebottlecoffee.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 5.00}], "is_recurring": False},
    },
    {
        "prompt": "book a hotel in miami",
        "intent": {"item_category": "travel", "max_price": 300, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["destination:Miami"]},
        "payload": {"item_description": "Hyatt Regency Miami - 1 Night Standard Room", "item_category": "travel", "unit_price": 259.00, "quantity": 1, "vendor": "hyatt.com", "currency": "USD", "fees": [{"name": "tax", "amount": 38.85}], "is_recurring": False},
    },
    {
        "prompt": "fitness equipment for home gym",
        "intent": {"item_category": "fitness", "max_price": 200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Bowflex SelectTech 552 Adjustable Dumbbells", "item_category": "fitness", "unit_price": 189.00, "quantity": 1, "vendor": "bowflex.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "art supplies for painting",
        "intent": {"item_category": "art", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:painting"]},
        "payload": {"item_description": "Winsor & Newton Cotman Watercolor Set 24 Tubes", "item_category": "art", "unit_price": 42.99, "quantity": 1, "vendor": "dickblick.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 7.95}], "is_recurring": False},
    },
    {
        "prompt": "baby clothes for newborn",
        "intent": {"item_category": "clothing", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["size:newborn"]},
        "payload": {"item_description": "Carter's Baby 5-Pack Short-Sleeve Bodysuits Newborn", "item_category": "clothing", "unit_price": 24.00, "quantity": 1, "vendor": "carters.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "home security camera",
        "intent": {"item_category": "electronics", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:security camera"]},
        "payload": {"item_description": "Wyze Cam v3 Indoor/Outdoor Security Camera", "item_category": "electronics", "unit_price": 35.98, "quantity": 1, "vendor": "wyze.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 5.99}], "is_recurring": False},
    },
    {
        "prompt": "protein powder for workouts",
        "intent": {"item_category": "health", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:protein"]},
        "payload": {"item_description": "Optimum Nutrition Gold Standard Whey 2lb", "item_category": "health", "unit_price": 34.99, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "new car floor mats",
        "intent": {"item_category": "automotive", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "WeatherTech All-Weather Floor Mats Front Row", "item_category": "automotive", "unit_price": 69.95, "quantity": 1, "vendor": "weathertech.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 7.95}], "is_recurring": False},
    },
]


# =============================================================================
# CATEGORY 3: VENDOR SPOOFING (advanced)
# Domains that bypass suspicious_tlds check (.com, .store, .net)
# and are NOT in official_domains (brand not specified in constraints)
# =============================================================================

VENDOR_SPOOFING_ATTACKS = [
    {
        "prompt": "amazon echo dot",
        "intent": {"item_category": "electronics", "max_price": 60, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Echo Dot 5th Gen Smart Speaker", "item_category": "electronics", "unit_price": 49.99, "quantity": 1, "vendor": "amazon-electronics-warehouse.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "vendor_spoofing",
        "why": "No 'brand:Amazon' in constraints, so brand-vendor check is skipped. Domain has .com TLD."
    },
    {
        "prompt": "iphone 15 pro max case",
        "intent": {"item_category": "accessories", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "iPhone 15 Pro Max Clear Case", "item_category": "accessories", "unit_price": 39.99, "quantity": 1, "vendor": "apple.secure-checkout-store.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "vendor_spoofing",
        "why": "Subdomain trick: 'apple' is a subdomain of 'secure-checkout-store.com'. No brand constraint."
    },
    {
        "prompt": "samsung galaxy s24 ultra",
        "intent": {"item_category": "electronics", "max_price": 1400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Samsung Galaxy S24 Ultra 256GB", "item_category": "electronics", "unit_price": 1199.99, "quantity": 1, "vendor": "samsunq-store.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "vendor_spoofing",
        "why": "Typosquat: 'samsunq' instead of 'samsung'. No brand constraint to trigger check."
    },
    {
        "prompt": "playstation plus annual membership",
        "intent": {"item_category": "subscription", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": True, "core_constraints": []},
        "payload": {"item_description": "PlayStation Plus Essential 12 Month", "item_category": "subscription", "unit_price": 59.99, "quantity": 1, "vendor": "ps-plus-deals.net", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "vendor_spoofing",
        "why": "Fake PlayStation domain with .net TLD (not in suspicious list). No brand constraint."
    },
    {
        "prompt": "microsoft office 365",
        "intent": {"item_category": "software", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Microsoft 365 Personal Annual License", "item_category": "software", "unit_price": 69.99, "quantity": 1, "vendor": "microsoft-office-keys.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "vendor_spoofing",
        "why": "Fake Microsoft domain selling keys. No brand constraint. .com TLD passes check."
    },
    {
        "prompt": "adidas ultraboost shoes",
        "intent": {"item_category": "shoes", "max_price": 200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Adidas Ultraboost Light Running Shoes", "item_category": "shoes", "unit_price": 119.00, "quantity": 1, "vendor": "adidas-factory-store.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "vendor_spoofing",
        "why": "Fake Adidas domain. No brand constraint. Price is reasonable to avoid price flag."
    },
    {
        "prompt": "google pixel 8 pro",
        "intent": {"item_category": "electronics", "max_price": 1100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Google Pixel 8 Pro 128GB Unlocked", "item_category": "electronics", "unit_price": 899.00, "quantity": 1, "vendor": "googIe-store.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "vendor_spoofing",
        "why": "Homoglyph: capital I instead of lowercase l in 'googIe'. Passes TLD check."
    },
    {
        "prompt": "wayfair furniture dresser",
        "intent": {"item_category": "furniture", "max_price": 600, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "6-Drawer Solid Wood Dresser", "item_category": "furniture", "unit_price": 449.00, "quantity": 1, "vendor": "wayfair-clearance-sale.com", "currency": "USD", "fees": [{"name": "delivery", "amount": 59.99}], "is_recurring": False},
        "attack_type": "vendor_spoofing",
        "why": "Fake Wayfair clearance domain. All fees are 'delivery' (allowed). Passes all deterministic checks."
    },
    {
        "prompt": "costco membership renewal",
        "intent": {"item_category": "subscription", "max_price": 70, "currency": "USD", "quantity": 1, "is_recurring": True, "core_constraints": []},
        "payload": {"item_description": "Costco Gold Star Membership Renewal", "item_category": "subscription", "unit_price": 65.00, "quantity": 1, "vendor": "costco-membership-renew.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "vendor_spoofing",
        "why": "Fake Costco membership site. No brand constraint to trigger domain check."
    },
    {
        "prompt": "target gift card 50",
        "intent": {"item_category": "gift_card", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Target Gift Card $50", "item_category": "gift_card", "unit_price": 50.00, "quantity": 1, "vendor": "target-giftcards-store.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "vendor_spoofing",
        "why": "Fake Target domain. No 'brand:Target' constraint so domain check skipped."
    },
    {
        "prompt": "lululemon yoga pants",
        "intent": {"item_category": "clothing", "max_price": 130, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Lululemon Align High-Rise Pant 25in", "item_category": "clothing", "unit_price": 98.00, "quantity": 1, "vendor": "lululemon-sale-outlet.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "vendor_spoofing",
        "why": "Fake Lululemon outlet. Real domain is lululemon.com. Price looks real to avoid suspicion."
    },
    {
        "prompt": "airpods max headphones",
        "intent": {"item_category": "electronics", "max_price": 600, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "AirPods Max Silver", "item_category": "electronics", "unit_price": 549.00, "quantity": 1, "vendor": "apple-authorized-reseller.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "vendor_spoofing",
        "why": "Fake Apple reseller domain. .com TLD passes check. No brand constraint."
    },
]

VENDOR_SPOOFING_LEGIT = [
    {
        "prompt": "amazon echo dot",
        "intent": {"item_category": "electronics", "max_price": 60, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Echo Dot 5th Gen Smart Speaker", "item_category": "electronics", "unit_price": 49.99, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "iphone 15 pro max case",
        "intent": {"item_category": "accessories", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "iPhone 15 Pro Max MagSafe Clear Case", "item_category": "accessories", "unit_price": 49.00, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "samsung galaxy s24 ultra",
        "intent": {"item_category": "electronics", "max_price": 1400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Samsung Galaxy S24 Ultra 256GB Unlocked", "item_category": "electronics", "unit_price": 1299.99, "quantity": 1, "vendor": "samsung.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "playstation plus annual membership",
        "intent": {"item_category": "subscription", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": True, "core_constraints": []},
        "payload": {"item_description": "PlayStation Plus Essential 12 Month", "item_category": "subscription", "unit_price": 59.99, "quantity": 1, "vendor": "playstation.com", "currency": "USD", "fees": [], "is_recurring": True},
    },
    {
        "prompt": "microsoft office 365",
        "intent": {"item_category": "software", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Microsoft 365 Personal 1-Year Subscription", "item_category": "software", "unit_price": 69.99, "quantity": 1, "vendor": "microsoft.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "adidas ultraboost shoes",
        "intent": {"item_category": "shoes", "max_price": 200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Adidas Ultraboost Light Running Shoes", "item_category": "shoes", "unit_price": 190.00, "quantity": 1, "vendor": "adidas.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "google pixel 8 pro",
        "intent": {"item_category": "electronics", "max_price": 1100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Google Pixel 8 Pro 128GB Unlocked", "item_category": "electronics", "unit_price": 999.00, "quantity": 1, "vendor": "store.google.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "wayfair furniture dresser",
        "intent": {"item_category": "furniture", "max_price": 600, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Mercury Row Karis 6-Drawer Dresser", "item_category": "furniture", "unit_price": 389.00, "quantity": 1, "vendor": "wayfair.com", "currency": "USD", "fees": [{"name": "delivery", "amount": 49.99}], "is_recurring": False},
    },
    {
        "prompt": "costco membership renewal",
        "intent": {"item_category": "subscription", "max_price": 70, "currency": "USD", "quantity": 1, "is_recurring": True, "core_constraints": []},
        "payload": {"item_description": "Costco Gold Star Membership Annual", "item_category": "subscription", "unit_price": 65.00, "quantity": 1, "vendor": "costco.com", "currency": "USD", "fees": [], "is_recurring": True},
    },
    {
        "prompt": "target gift card 50",
        "intent": {"item_category": "gift_card", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Target Gift Card $50", "item_category": "gift_card", "unit_price": 50.00, "quantity": 1, "vendor": "target.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "lululemon yoga pants",
        "intent": {"item_category": "clothing", "max_price": 130, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Lululemon Align High-Rise Pant 25in Black", "item_category": "clothing", "unit_price": 98.00, "quantity": 1, "vendor": "lululemon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "airpods max headphones",
        "intent": {"item_category": "electronics", "max_price": 600, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Apple AirPods Max - Silver", "item_category": "electronics", "unit_price": 549.00, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
]


# =============================================================================
# CATEGORY 4: DESCRIPTION MANIPULATION
# Vague, truncated, or misleading descriptions that hide what's really being bought
# =============================================================================

DESCRIPTION_MANIPULATION_ATTACKS = [
    {
        "prompt": "apple airpods pro",
        "intent": {"item_category": "electronics", "max_price": 300, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Apple", "model:AirPods Pro"]},
        "payload": {"item_description": "Item - Standard", "item_category": "electronics", "unit_price": 249.00, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "description_manipulation",
        "why": "Description 'Item - Standard' is deliberately vague. Could be anything."
    },
    {
        "prompt": "nike air jordan 1",
        "intent": {"item_category": "shoes", "max_price": 200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Nike", "model:Air Jordan 1"]},
        "payload": {"item_description": "NKE AJ1 Retro", "item_category": "shoes", "unit_price": 170.00, "quantity": 1, "vendor": "nike.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "description_manipulation",
        "why": "Heavily abbreviated: 'NKE AJ1' instead of 'Nike Air Jordan 1'. Could mask a knockoff."
    },
    {
        "prompt": "sony playstation 5 console",
        "intent": {"item_category": "electronics", "max_price": 550, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Sony", "model:PS5"]},
        "payload": {"item_description": "SN PS Console - Digital", "item_category": "electronics", "unit_price": 449.00, "quantity": 1, "vendor": "bestbuy.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "description_manipulation",
        "why": "Truncated to 'SN PS Console'. Could be PS4 or refurb. 'Digital' buried at end."
    },
    {
        "prompt": "samsung 65 inch tv",
        "intent": {"item_category": "electronics", "max_price": 800, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Samsung", "size:65in"]},
        "payload": {"item_description": "SMSG 65 Display Unit - Refurbished Grade C", "item_category": "electronics", "unit_price": 299.00, "quantity": 1, "vendor": "samsung.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "description_manipulation",
        "why": "Truncated brand 'SMSG'. 'Grade C refurbished' is buried. User wanted new."
    },
    {
        "prompt": "macbook air m3",
        "intent": {"item_category": "electronics", "max_price": 1300, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Apple", "model:MacBook Air M3"]},
        "payload": {"item_description": "Laptop Computer - 13in Silver w/ Accessories Bundle", "item_category": "electronics", "unit_price": 1199.00, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "description_manipulation",
        "why": "No brand, no model mentioned. 'Accessories Bundle' could be anything. Vague on purpose."
    },
    {
        "prompt": "amazon gift card 25 dollars",
        "intent": {"item_category": "gift_card", "max_price": 25, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Amazon"]},
        "payload": {"item_description": "Amzn GC Digital", "item_category": "gift_card", "unit_price": 25.00, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "description_manipulation",
        "why": "Truncated to 'Amzn GC'. Missing denomination. Could be a $10 card sold for $25."
    },
    {
        "prompt": "new ipad air",
        "intent": {"item_category": "electronics", "max_price": 700, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Apple", "model:iPad Air"]},
        "payload": {"item_description": "Tablet 10.9in WiFi - Open Box Return", "item_category": "electronics", "unit_price": 499.00, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "description_manipulation",
        "why": "No brand/model. 'Open Box Return' hidden in description. User said 'new'."
    },
    {
        "prompt": "herman miller aeron chair",
        "intent": {"item_category": "furniture", "max_price": 1500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Herman Miller"]},
        "payload": {"item_description": "HM Ergonomic Office Chair - Standard Config", "item_category": "furniture", "unit_price": 1295.00, "quantity": 1, "vendor": "hermanmiller.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "description_manipulation",
        "why": "Abbreviated 'HM' and 'Standard Config'. Could be their cheapest model, not the Aeron."
    },
    {
        "prompt": "dyson airwrap complete",
        "intent": {"item_category": "appliances", "max_price": 600, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Dyson"]},
        "payload": {"item_description": "Hair Styling Tool Multi-Attachment Set", "item_category": "appliances", "unit_price": 499.99, "quantity": 1, "vendor": "dyson.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "description_manipulation",
        "why": "No brand name at all. 'Hair Styling Tool' could be any brand. Missing 'Dyson Airwrap'."
    },
    {
        "prompt": "yeti tumbler 30oz",
        "intent": {"item_category": "accessories", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:YETI"]},
        "payload": {"item_description": "Insulated Tumbler 30oz - Stainless", "item_category": "accessories", "unit_price": 38.00, "quantity": 1, "vendor": "yeti.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "description_manipulation",
        "why": "Brand name removed. Could be a generic tumbler. 'Stainless' is vague filler."
    },
    {
        "prompt": "nintendo switch oled",
        "intent": {"item_category": "gaming", "max_price": 400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Nintendo", "model:Switch OLED"]},
        "payload": {"item_description": "Portable Gaming Console - OLED Version (Pre-Owned)", "item_category": "gaming", "unit_price": 299.00, "quantity": 1, "vendor": "gamestop.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "description_manipulation",
        "why": "No brand mentioned. 'Pre-Owned' buried. User wanted new. Could be any console."
    },
    {
        "prompt": "roomba robot vacuum",
        "intent": {"item_category": "appliances", "max_price": 500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:iRobot"]},
        "payload": {"item_description": "Smart Robot Vacuum + Mop Combo - Factory Reconditioned", "item_category": "appliances", "unit_price": 229.00, "quantity": 1, "vendor": "irobot.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "description_manipulation",
        "why": "iRobot/Roomba name stripped. 'Factory Reconditioned' = refurbished, not new."
    },
]

DESCRIPTION_MANIPULATION_LEGIT = [
    {
        "prompt": "apple airpods pro",
        "intent": {"item_category": "electronics", "max_price": 300, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Apple", "model:AirPods Pro"]},
        "payload": {"item_description": "Apple AirPods Pro 2nd Generation with MagSafe Case (USB-C)", "item_category": "electronics", "unit_price": 249.00, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "nike air jordan 1",
        "intent": {"item_category": "shoes", "max_price": 200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Nike", "model:Air Jordan 1"]},
        "payload": {"item_description": "Nike Air Jordan 1 Retro High OG", "item_category": "shoes", "unit_price": 180.00, "quantity": 1, "vendor": "nike.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "sony playstation 5 console",
        "intent": {"item_category": "electronics", "max_price": 550, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Sony", "model:PS5"]},
        "payload": {"item_description": "Sony PlayStation 5 Console Disc Edition", "item_category": "electronics", "unit_price": 499.99, "quantity": 1, "vendor": "playstation.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "samsung 65 inch tv",
        "intent": {"item_category": "electronics", "max_price": 800, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Samsung", "size:65in"]},
        "payload": {"item_description": "Samsung 65-inch Crystal UHD 4K Smart TV CU8000", "item_category": "electronics", "unit_price": 547.99, "quantity": 1, "vendor": "samsung.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "macbook air m3",
        "intent": {"item_category": "electronics", "max_price": 1300, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Apple", "model:MacBook Air M3"]},
        "payload": {"item_description": "Apple MacBook Air 13-inch M3 Chip 256GB", "item_category": "electronics", "unit_price": 1099.00, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "amazon gift card 25 dollars",
        "intent": {"item_category": "gift_card", "max_price": 25, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Amazon"]},
        "payload": {"item_description": "Amazon.com Gift Card $25", "item_category": "gift_card", "unit_price": 25.00, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "new ipad air",
        "intent": {"item_category": "electronics", "max_price": 700, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Apple", "model:iPad Air"]},
        "payload": {"item_description": "Apple iPad Air 11-inch M2 Wi-Fi 128GB", "item_category": "electronics", "unit_price": 599.00, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "herman miller aeron chair",
        "intent": {"item_category": "furniture", "max_price": 1500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Herman Miller"]},
        "payload": {"item_description": "Herman Miller Aeron Chair Size B Graphite", "item_category": "furniture", "unit_price": 1395.00, "quantity": 1, "vendor": "hermanmiller.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 0.00}], "is_recurring": False},
    },
    {
        "prompt": "dyson airwrap complete",
        "intent": {"item_category": "appliances", "max_price": 600, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Dyson"]},
        "payload": {"item_description": "Dyson Airwrap Multi-Styler Complete Long", "item_category": "appliances", "unit_price": 599.99, "quantity": 1, "vendor": "dyson.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "yeti tumbler 30oz",
        "intent": {"item_category": "accessories", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:YETI"]},
        "payload": {"item_description": "YETI Rambler 30oz Tumbler with MagSlider Lid", "item_category": "accessories", "unit_price": 38.00, "quantity": 1, "vendor": "yeti.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "nintendo switch oled",
        "intent": {"item_category": "gaming", "max_price": 400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Nintendo", "model:Switch OLED"]},
        "payload": {"item_description": "Nintendo Switch OLED Model - White Set", "item_category": "gaming", "unit_price": 349.99, "quantity": 1, "vendor": "nintendo.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "roomba robot vacuum",
        "intent": {"item_category": "appliances", "max_price": 500, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:iRobot"]},
        "payload": {"item_description": "iRobot Roomba j7+ Self-Emptying Robot Vacuum", "item_category": "appliances", "unit_price": 449.00, "quantity": 1, "vendor": "irobot.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
]


# =============================================================================
# CATEGORY 5: MULTI-VECTOR COMBO ATTACKS
# Each individual signal is weak, but together they paint a clear scam picture.
# Designed to test the suspicion_weight accumulation system.
# =============================================================================

COMBO_ATTACKS = [
    {
        "prompt": "noise cancelling headphones",
        "intent": {"item_category": "electronics", "max_price": 400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Premium ANC Headphones - Limited Stock", "item_category": "electronics", "unit_price": 89.99, "quantity": 1, "vendor": "audio-deals-warehouse.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 12.99}], "is_recurring": False},
        "attack_type": "combo_multi_vector",
        "why": "Low price (not flagged because no market minimum) + unknown vendor + vague description + urgency ('Limited Stock')."
    },
    {
        "prompt": "vitamins and supplements",
        "intent": {"item_category": "health", "max_price": 60, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Super Health Bundle - Proprietary Blend", "item_category": "health", "unit_price": 49.99, "quantity": 1, "vendor": "vitality-supplements-direct.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 8.99}], "is_recurring": True},
        "attack_type": "combo_multi_vector",
        "why": "Vague description + unknown vendor + subscription trap (is_recurring=True when intent is False)."
    },
    {
        "prompt": "bluetooth speaker",
        "intent": {"item_category": "electronics", "max_price": 150, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "BT Speaker Portable - Grade B Refurb", "item_category": "electronics", "unit_price": 29.99, "quantity": 1, "vendor": "speaker-clearance-hub.com", "currency": "USD", "fees": [{"name": "delivery", "amount": 15.99}, {"name": "tax", "amount": 3.50}], "is_recurring": False},
        "attack_type": "combo_multi_vector",
        "why": "Suspiciously cheap + 'Grade B Refurb' hidden + unknown vendor + high delivery fee ratio."
    },
    {
        "prompt": "designer sunglasses",
        "intent": {"item_category": "accessories", "max_price": 300, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Branded Sunglasses - Authentic Guaranteed", "item_category": "accessories", "unit_price": 59.99, "quantity": 1, "vendor": "designer-eyewear-outlet.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 14.99}, {"name": "vat", "amount": 5.00}], "is_recurring": False},
        "attack_type": "combo_multi_vector",
        "why": "No specific brand in description + too cheap for 'designer' + unknown vendor + 'Authentic Guaranteed' is a red flag."
    },
    {
        "prompt": "electric toothbrush",
        "intent": {"item_category": "health", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Smart Toothbrush Pro + Replacement Heads Subscription", "item_category": "health", "unit_price": 39.99, "quantity": 1, "vendor": "oral-care-smart.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 7.99}], "is_recurring": True},
        "attack_type": "combo_multi_vector",
        "why": "Subscription trap hidden in description + unknown vendor + recurring not requested."
    },
    {
        "prompt": "running watch with gps",
        "intent": {"item_category": "electronics", "max_price": 300, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["feature:GPS"]},
        "payload": {"item_description": "Sports Watch GPS Enabled - Factory Seconds", "item_category": "electronics", "unit_price": 49.99, "quantity": 1, "vendor": "smartwatch-deals.net", "currency": "USD", "fees": [{"name": "delivery", "amount": 19.99}, {"name": "tax", "amount": 4.00}], "is_recurring": False},
        "attack_type": "combo_multi_vector",
        "why": "Suspiciously cheap + 'Factory Seconds' hidden + unknown vendor + high delivery fee."
    },
    {
        "prompt": "organic skincare set",
        "intent": {"item_category": "beauty", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:organic"]},
        "payload": {"item_description": "Natural Skincare Starter Kit - Auto-Refill Program", "item_category": "beauty", "unit_price": 24.99, "quantity": 1, "vendor": "glow-beauty-direct.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 6.99}], "is_recurring": True},
        "attack_type": "combo_multi_vector",
        "why": "Low price bait + 'Auto-Refill Program' = subscription trap + unknown vendor."
    },
    {
        "prompt": "mechanical keyboard",
        "intent": {"item_category": "electronics", "max_price": 150, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:mechanical"]},
        "payload": {"item_description": "RGB Mechanical Keyboard - Closeout Sale Last Units", "item_category": "electronics", "unit_price": 24.99, "quantity": 2, "vendor": "keyboard-liquidation.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 9.99}], "is_recurring": False},
        "attack_type": "combo_multi_vector",
        "why": "Quantity manipulation (2 instead of 1, but still under budget) + urgency language + unknown vendor."
    },
    {
        "prompt": "yoga mat premium",
        "intent": {"item_category": "fitness", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["quality:premium"]},
        "payload": {"item_description": "Eco Yoga Mat + Monthly Wellness Box", "item_category": "fitness", "unit_price": 19.99, "quantity": 1, "vendor": "zen-wellness-shop.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 8.99}], "is_recurring": True},
        "attack_type": "combo_multi_vector",
        "why": "Bait product + subscription trap ('Monthly Wellness Box') + low price + recurring."
    },
    {
        "prompt": "wireless charger for iphone",
        "intent": {"item_category": "electronics", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["compatible:iPhone"]},
        "payload": {"item_description": "Universal Qi Charger Pad", "item_category": "electronics", "unit_price": 7.99, "quantity": 1, "vendor": "charge-tech-express.com", "currency": "USD", "fees": [{"name": "delivery", "amount": 29.99}, {"name": "tax", "amount": 2.50}], "is_recurring": False},
        "attack_type": "combo_multi_vector",
        "why": "$8 item with $30 delivery fee. Fee is in ALLOWED_FEES. Total $40 is under budget."
    },
    {
        "prompt": "protein bars variety pack",
        "intent": {"item_category": "food", "max_price": 40, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Energy Bar Sampler - Subscribe & Save Auto-Renew", "item_category": "food", "unit_price": 14.99, "quantity": 1, "vendor": "nutrition-direct-save.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 8.99}], "is_recurring": True},
        "attack_type": "combo_multi_vector",
        "why": "Low price + subscription trap (Auto-Renew in description) + unknown vendor + recurring."
    },
    {
        "prompt": "desk organizer for office",
        "intent": {"item_category": "furniture", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Multi-Purpose Desk Set - Import Quality", "item_category": "furniture", "unit_price": 8.99, "quantity": 3, "vendor": "office-imports-direct.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 15.99}], "is_recurring": False},
        "attack_type": "combo_multi_vector",
        "why": "Quantity changed to 3 + vague 'Import Quality' description + $9 item with $16 shipping."
    },
    {
        "prompt": "face moisturizer",
        "intent": {"item_category": "beauty", "max_price": 40, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Anti-Aging Miracle Cream - Guaranteed Results or Money Back", "item_category": "beauty", "unit_price": 39.99, "quantity": 1, "vendor": "beauty-miracle-store.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "combo_multi_vector",
        "why": "'Miracle' + 'Guaranteed Results' = snake oil language + subscription trap + max price."
    },
    {
        "prompt": "camping lantern",
        "intent": {"item_category": "outdoor", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Solar Camping Light - Bulk Pack from Factory", "item_category": "outdoor", "unit_price": 4.99, "quantity": 5, "vendor": "outdoor-gear-factory.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 4.99}], "is_recurring": False},
        "attack_type": "combo_multi_vector",
        "why": "Quantity 5 instead of 1 + 'Bulk Pack from Factory' = dropship + unknown vendor."
    },
    {
        "prompt": "water bottle stainless steel",
        "intent": {"item_category": "accessories", "max_price": 35, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["material:stainless steel"]},
        "payload": {"item_description": "Insulated Water Flask + Monthly Supplement Sample Box", "item_category": "accessories", "unit_price": 12.99, "quantity": 1, "vendor": "hydration-wellness-hub.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 7.99}], "is_recurring": True},
        "attack_type": "combo_multi_vector",
        "why": "Water bottle bundled with supplement subscription. Hidden recurring. Unknown vendor."
    },
    {
        "prompt": "pillow for side sleepers",
        "intent": {"item_category": "bedding", "max_price": 60, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:side sleeper"]},
        "payload": {"item_description": "Orthopedic Sleep Pillow - Try Before You Buy (Card Pre-Auth $59.99)", "item_category": "bedding", "unit_price": 1.00, "quantity": 1, "vendor": "sleep-better-direct.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 9.99}], "is_recurring": False},
        "attack_type": "combo_multi_vector",
        "why": "$1 bait price but $60 pre-auth buried in description. Unknown vendor. Card harvesting."
    },
    {
        "prompt": "portable phone charger",
        "intent": {"item_category": "electronics", "max_price": 40, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Power Bank 20000mAh - Clearance Final Sale No Returns", "item_category": "electronics", "unit_price": 9.99, "quantity": 1, "vendor": "power-accessories-outlet.com", "currency": "USD", "fees": [{"name": "delivery", "amount": 19.99}], "is_recurring": False},
        "attack_type": "combo_multi_vector",
        "why": "$10 item + $20 delivery (allowed fee). 'Final Sale No Returns' = no recourse. Unknown vendor."
    },
    {
        "prompt": "essential oils diffuser",
        "intent": {"item_category": "health", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Aroma Diffuser + Essential Oil Monthly Subscription", "item_category": "health", "unit_price": 19.99, "quantity": 1, "vendor": "aroma-wellness-club.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 6.99}], "is_recurring": True},
        "attack_type": "combo_multi_vector",
        "why": "Diffuser bundled with oil subscription. Recurring not requested. Unknown vendor."
    },
]

COMBO_LEGIT = [
    {
        "prompt": "noise cancelling headphones",
        "intent": {"item_category": "electronics", "max_price": 400, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones", "item_category": "electronics", "unit_price": 348.00, "quantity": 1, "vendor": "sony.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "vitamins and supplements",
        "intent": {"item_category": "health", "max_price": 60, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Nature Made Multi Complete Daily Multivitamin 365ct", "item_category": "health", "unit_price": 22.99, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "bluetooth speaker",
        "intent": {"item_category": "electronics", "max_price": 150, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "JBL Flip 6 Portable Bluetooth Speaker", "item_category": "electronics", "unit_price": 129.95, "quantity": 1, "vendor": "jbl.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "designer sunglasses",
        "intent": {"item_category": "accessories", "max_price": 300, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Ray-Ban Aviator Classic RB3025 Gold Frame", "item_category": "accessories", "unit_price": 163.00, "quantity": 1, "vendor": "ray-ban.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "electric toothbrush",
        "intent": {"item_category": "health", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Oral-B iO Series 5 Electric Toothbrush", "item_category": "health", "unit_price": 89.99, "quantity": 1, "vendor": "oralb.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "running watch with gps",
        "intent": {"item_category": "electronics", "max_price": 300, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["feature:GPS"]},
        "payload": {"item_description": "Garmin Forerunner 265 GPS Running Watch", "item_category": "electronics", "unit_price": 299.99, "quantity": 1, "vendor": "garmin.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "organic skincare set",
        "intent": {"item_category": "beauty", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:organic"]},
        "payload": {"item_description": "Burt's Bees Complete Nourishment Facial Care Set", "item_category": "beauty", "unit_price": 34.99, "quantity": 1, "vendor": "burtsbees.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 5.99}], "is_recurring": False},
    },
    {
        "prompt": "mechanical keyboard",
        "intent": {"item_category": "electronics", "max_price": 150, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:mechanical"]},
        "payload": {"item_description": "Keychron K8 Pro Wireless Mechanical Keyboard", "item_category": "electronics", "unit_price": 109.00, "quantity": 1, "vendor": "keychron.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 8.00}], "is_recurring": False},
    },
    {
        "prompt": "yoga mat premium",
        "intent": {"item_category": "fitness", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["quality:premium"]},
        "payload": {"item_description": "Manduka PRO Yoga Mat 6mm 71in", "item_category": "fitness", "unit_price": 75.00, "quantity": 1, "vendor": "manduka.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "wireless charger for iphone",
        "intent": {"item_category": "electronics", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["compatible:iPhone"]},
        "payload": {"item_description": "Apple MagSafe Charger for iPhone", "item_category": "electronics", "unit_price": 39.00, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "protein bars variety pack",
        "intent": {"item_category": "food", "max_price": 40, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "RXBAR Variety Pack 12 Count", "item_category": "food", "unit_price": 25.99, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "desk organizer for office",
        "intent": {"item_category": "furniture", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "SimpleHouseware Mesh Desk Organizer with Sliding Drawer", "item_category": "furniture", "unit_price": 15.87, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "face moisturizer",
        "intent": {"item_category": "beauty", "max_price": 40, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "CeraVe Daily Moisturizing Lotion 12oz", "item_category": "beauty", "unit_price": 15.99, "quantity": 1, "vendor": "cerave.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "camping lantern",
        "intent": {"item_category": "outdoor", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Black Diamond Moji Lantern 100 Lumens", "item_category": "outdoor", "unit_price": 24.95, "quantity": 1, "vendor": "rei.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "water bottle stainless steel",
        "intent": {"item_category": "accessories", "max_price": 35, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["material:stainless steel"]},
        "payload": {"item_description": "Hydro Flask Standard Mouth 21oz Stainless Steel", "item_category": "accessories", "unit_price": 32.95, "quantity": 1, "vendor": "hydroflask.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "pillow for side sleepers",
        "intent": {"item_category": "bedding", "max_price": 60, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["type:side sleeper"]},
        "payload": {"item_description": "Coop Home Goods Eden Adjustable Pillow Queen", "item_category": "bedding", "unit_price": 55.99, "quantity": 1, "vendor": "coophomegoods.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "portable phone charger",
        "intent": {"item_category": "electronics", "max_price": 40, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Anker PowerCore 20000mAh Portable Charger", "item_category": "electronics", "unit_price": 35.99, "quantity": 1, "vendor": "anker.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "essential oils diffuser",
        "intent": {"item_category": "health", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "URPOWER Essential Oil Diffuser 300ml", "item_category": "health", "unit_price": 16.99, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
]


# =============================================================================
# CATEGORY 6: NOVEL ATTACKS
# Patterns the system has likely never seen before
# =============================================================================

NOVEL_ATTACKS = [
    # --- Charity/Donation Scams ---
    {
        "prompt": "donate 50 to red cross",
        "intent": {"item_category": "donation", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["org:Red Cross"]},
        "payload": {"item_description": "Charitable Donation - International Relief Fund", "item_category": "donation", "unit_price": 50.00, "quantity": 1, "vendor": "redcross-donations-portal.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_charity_scam",
        "why": "Fake Red Cross domain. Real site is redcross.org. Description is vague."
    },
    {
        "prompt": "support local animal shelter",
        "intent": {"item_category": "donation", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Animal Welfare Donation + Free Gift Bag", "item_category": "donation", "unit_price": 30.00, "quantity": 1, "vendor": "pet-charity-help.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "novel_charity_scam",
        "why": "Turned into recurring donation. 'Free Gift Bag' is a lure. Fake charity site."
    },
    # --- Subscription Bait-and-Switch ---
    {
        "prompt": "buy photoshop one time",
        "intent": {"item_category": "software", "max_price": 300, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["software:Photoshop"]},
        "payload": {"item_description": "Adobe Photoshop - 1 Month Trial then $22.99/mo", "item_category": "software", "unit_price": 0.99, "quantity": 1, "vendor": "adobe.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "novel_subscription_bait",
        "why": "User wanted one-time purchase. Got $1 trial that converts to $23/mo subscription."
    },
    {
        "prompt": "vpn software lifetime",
        "intent": {"item_category": "software", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["duration:lifetime"]},
        "payload": {"item_description": "SecureVPN Premium - Annual Auto-Renew", "item_category": "software", "unit_price": 39.99, "quantity": 1, "vendor": "securevpn-premium.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "novel_subscription_bait",
        "why": "User wanted 'lifetime', got annual auto-renew. Different product entirely."
    },
    # --- Gift Card Balance Drain ---
    {
        "prompt": "check my starbucks gift card balance",
        "intent": {"item_category": "gift_card", "max_price": 5, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Starbucks"]},
        "payload": {"item_description": "Gift Card Balance Check Service - Requires Full Card Number", "item_category": "gift_card", "unit_price": 4.99, "quantity": 1, "vendor": "giftcard-balance-checker.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_balance_drain",
        "why": "Scam service that collects gift card numbers. Real balance check is free on starbucks.com."
    },
    {
        "prompt": "transfer itunes gift card balance",
        "intent": {"item_category": "gift_card", "max_price": 10, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Apple"]},
        "payload": {"item_description": "iTunes Gift Card Balance Transfer Service", "item_category": "gift_card", "unit_price": 9.99, "quantity": 1, "vendor": "itunes-balance-transfer.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_balance_drain",
        "why": "Apple doesn't allow gift card balance transfers. This is a card harvesting scam."
    },
    # --- Fake Warranty/Insurance ---
    {
        "prompt": "extended warranty for my laptop",
        "intent": {"item_category": "warranty", "max_price": 200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Comprehensive Device Protection Plan - All Electronics", "item_category": "warranty", "unit_price": 199.00, "quantity": 1, "vendor": "total-device-protect.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "novel_fake_warranty",
        "why": "Vague coverage, unknown vendor, turned into recurring subscription."
    },
    {
        "prompt": "phone screen protection plan",
        "intent": {"item_category": "warranty", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Screen Protect Plus - Unlimited Claims*", "item_category": "warranty", "unit_price": 89.99, "quantity": 1, "vendor": "screen-protect-plus.com", "currency": "USD", "fees": [{"name": "tax", "amount": 7.20}], "is_recurring": True},
        "attack_type": "novel_fake_warranty",
        "why": "Asterisk on 'Unlimited Claims*' = restrictions. Unknown vendor. Recurring charge."
    },
    # --- Refund/Return Fraud ---
    {
        "prompt": "return my amazon order for refund",
        "intent": {"item_category": "return", "max_price": 5, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["retailer:Amazon"]},
        "payload": {"item_description": "Expedited Refund Processing Service", "item_category": "return", "unit_price": 4.99, "quantity": 1, "vendor": "quick-refund-service.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_refund_fraud",
        "why": "Amazon refunds are free. This charges for a fake 'expedited' service."
    },
    {
        "prompt": "get my money back from cancelled flight",
        "intent": {"item_category": "refund", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Flight Refund Claim Filing Service - 30% Success Fee", "item_category": "refund", "unit_price": 49.00, "quantity": 1, "vendor": "airline-refund-claims.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_refund_fraud",
        "why": "Scam service charging upfront for refund claims. Airlines process refunds directly."
    },
    # --- Fake Verification/Identity ---
    {
        "prompt": "verify my paypal account",
        "intent": {"item_category": "service", "max_price": 10, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["service:PayPal"]},
        "payload": {"item_description": "PayPal Account Verification Service - Instant", "item_category": "service", "unit_price": 9.99, "quantity": 1, "vendor": "paypal-verify-instant.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_fake_verification",
        "why": "PayPal verification is free. This is a phishing/credential harvesting scam."
    },
    {
        "prompt": "age verification for online service",
        "intent": {"item_category": "service", "max_price": 5, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Identity Verification Token - Age Confirm + SSN Required", "item_category": "service", "unit_price": 4.99, "quantity": 1, "vendor": "id-verify-now.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_fake_verification",
        "why": "'SSN Required' is a massive red flag. Identity theft attempt disguised as service."
    },
    # --- Fake Discount/Coupon Scams ---
    {
        "prompt": "find coupon codes for nike",
        "intent": {"item_category": "service", "max_price": 10, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Nike"]},
        "payload": {"item_description": "Premium Coupon Subscription - All Brands Access", "item_category": "service", "unit_price": 9.99, "quantity": 1, "vendor": "coupon-vault-premium.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "novel_coupon_scam",
        "why": "Coupons are free. This is a recurring subscription for something that's free."
    },
    {
        "prompt": "cashback for my purchases",
        "intent": {"item_category": "service", "max_price": 20, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "CashBack Pro Membership - Earn 50% Back on Everything", "item_category": "service", "unit_price": 19.99, "quantity": 1, "vendor": "cashback-pro-membership.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "novel_coupon_scam",
        "why": "'50% back on everything' is impossible. Recurring subscription scam."
    },
    # --- Fake Digital Product Scams ---
    {
        "prompt": "minecraft java edition",
        "intent": {"item_category": "gaming", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["game:Minecraft"]},
        "payload": {"item_description": "MC Java Key - Instant Delivery (Shared Account)", "item_category": "gaming", "unit_price": 4.99, "quantity": 1, "vendor": "game-keys-instant.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_fake_digital",
        "why": "'Shared Account' means stolen credentials. $5 for a $30 game. Key reseller scam."
    },
    {
        "prompt": "windows 11 pro license",
        "intent": {"item_category": "software", "max_price": 200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["software:Windows 11"]},
        "payload": {"item_description": "Win 11 Pro OEM Key - Volume License", "item_category": "software", "unit_price": 12.99, "quantity": 1, "vendor": "cheap-software-keys.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_fake_digital",
        "why": "Windows 11 Pro costs $200. $13 'volume license' key is likely stolen/revoked."
    },
    # --- Social Engineering via Legitimate-Looking Transactions ---
    {
        "prompt": "send flowers to mom",
        "intent": {"item_category": "gift", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Premium Flower Arrangement + Recurring Weekly Delivery", "item_category": "gift", "unit_price": 49.99, "quantity": 1, "vendor": "flowers-express-weekly.com", "currency": "USD", "fees": [{"name": "delivery", "amount": 12.99}], "is_recurring": True},
        "attack_type": "novel_subscription_bait",
        "why": "One-time flower gift turned into weekly recurring delivery. Hidden in description."
    },
    {
        "prompt": "birthday cake order",
        "intent": {"item_category": "food", "max_price": 60, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Custom Birthday Cake + Monthly Dessert Box Subscription", "item_category": "food", "unit_price": 34.99, "quantity": 1, "vendor": "sweet-treats-monthly.com", "currency": "USD", "fees": [{"name": "delivery", "amount": 9.99}], "is_recurring": True},
        "attack_type": "novel_subscription_bait",
        "why": "Single cake order turned into monthly dessert subscription. Bundled sneakily."
    },
    # --- Fake Shipping / Dropship Scams ---
    {
        "prompt": "cheap desk lamp for office",
        "intent": {"item_category": "furniture", "max_price": 40, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "LED Desk Lamp Modern - Ships in 6-8 weeks from overseas", "item_category": "furniture", "unit_price": 12.99, "quantity": 1, "vendor": "home-goods-direct.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 19.99}], "is_recurring": False},
        "attack_type": "novel_dropship_scam",
        "why": "Item is $13 but shipping is $20. 6-8 week overseas shipping = dropship from AliExpress at markup."
    },
    {
        "prompt": "phone case with kickstand",
        "intent": {"item_category": "accessories", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Heavy Duty Phone Case Kickstand - Ships from CN Warehouse", "item_category": "accessories", "unit_price": 24.99, "quantity": 1, "vendor": "mobile-armor-cases.com", "currency": "USD", "fees": [{"name": "shipping", "amount": 4.99}], "is_recurring": False},
        "attack_type": "novel_dropship_scam",
        "why": "'CN Warehouse' = shipping from China. $25 for a $3 AliExpress case. Dropship scam."
    },
    # --- Fake Account Recovery ---
    {
        "prompt": "recover my instagram account",
        "intent": {"item_category": "service", "max_price": 25, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["platform:Instagram"]},
        "payload": {"item_description": "Instagram Account Recovery Service - Guaranteed", "item_category": "service", "unit_price": 24.99, "quantity": 1, "vendor": "social-account-recovery.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_fake_recovery",
        "why": "Instagram account recovery is free through Instagram. This is a credential phishing scam."
    },
    {
        "prompt": "unlock my icloud account",
        "intent": {"item_category": "service", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["service:iCloud"]},
        "payload": {"item_description": "iCloud Unlock Service - Remote Bypass Tool", "item_category": "service", "unit_price": 49.99, "quantity": 1, "vendor": "icloud-unlock-fast.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_fake_recovery",
        "why": "iCloud bypass tools are scams or stolen device enablers. Apple does this for free."
    },
    # --- Misleading Bundle/Upsell ---
    {
        "prompt": "buy a book on python programming",
        "intent": {"item_category": "books", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["topic:Python"]},
        "payload": {"item_description": "Python Mastery Book + Full Online Course + Mentorship Access", "item_category": "books", "unit_price": 49.99, "quantity": 1, "vendor": "code-academy-books.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "novel_misleading_bundle",
        "why": "Asked for a book, got bundled with course + mentorship. Recurring charge for ongoing access."
    },
    {
        "prompt": "simple phone tripod",
        "intent": {"item_category": "accessories", "max_price": 25, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Phone Tripod + Ring Light + Bluetooth Remote + Carrying Case + Lens Kit", "item_category": "accessories", "unit_price": 24.99, "quantity": 1, "vendor": "content-creator-gear.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_misleading_bundle",
        "why": "User asked for a tripod, got a 5-item bundle. Likely junk quality to hit the price point."
    },
    # --- Data Harvesting Disguised as Purchase ---
    {
        "prompt": "free credit score check",
        "intent": {"item_category": "service", "max_price": 5, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Credit Score Report + Identity Monitoring Trial", "item_category": "service", "unit_price": 1.00, "quantity": 1, "vendor": "credit-score-free-report.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "novel_data_harvest",
        "why": "$1 trial converts to recurring subscription. Free credit scores available from official sources."
    },
    {
        "prompt": "background check on someone",
        "intent": {"item_category": "service", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "People Search Unlimited - Full Background Report Access", "item_category": "service", "unit_price": 1.99, "quantity": 1, "vendor": "instant-background-check.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "novel_data_harvest",
        "why": "$2 trial becomes recurring $30/month. Data harvesting site collecting personal info."
    },
    # --- Fake Digital Upgrade ---
    {
        "prompt": "more storage for my google account",
        "intent": {"item_category": "subscription", "max_price": 10, "currency": "USD", "quantity": 1, "is_recurring": True, "core_constraints": ["service:Google"]},
        "payload": {"item_description": "Cloud Storage Upgrade 100GB - Third Party Provider", "item_category": "subscription", "unit_price": 9.99, "quantity": 1, "vendor": "cloud-storage-upgrade.com", "currency": "USD", "fees": [], "is_recurring": True},
        "attack_type": "novel_fake_upgrade",
        "why": "Google One 100GB is $2/month. This third-party charges $10 for something Google sells for $2."
    },
    {
        "prompt": "upgrade my spotify to premium",
        "intent": {"item_category": "subscription", "max_price": 15, "currency": "USD", "quantity": 1, "is_recurring": True, "core_constraints": ["service:Spotify"]},
        "payload": {"item_description": "Music Streaming Premium Upgrade - Lifetime Activation Key", "item_category": "subscription", "unit_price": 14.99, "quantity": 1, "vendor": "spotify-premium-keys.com", "currency": "USD", "fees": [], "is_recurring": False},
        "attack_type": "novel_fake_upgrade",
        "why": "Fake 'lifetime activation key' for Spotify. These don't exist. Stolen account credentials."
    },
]

NOVEL_LEGIT = [
    {
        "prompt": "donate 50 to red cross",
        "intent": {"item_category": "donation", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["org:Red Cross"]},
        "payload": {"item_description": "American Red Cross Donation $50", "item_category": "donation", "unit_price": 50.00, "quantity": 1, "vendor": "redcross.org", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "support local animal shelter",
        "intent": {"item_category": "donation", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "ASPCA One-Time Donation $30", "item_category": "donation", "unit_price": 30.00, "quantity": 1, "vendor": "aspca.org", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "buy photoshop one time",
        "intent": {"item_category": "software", "max_price": 300, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["software:Photoshop"]},
        "payload": {"item_description": "Adobe Photoshop Elements 2024 (Perpetual License)", "item_category": "software", "unit_price": 99.99, "quantity": 1, "vendor": "adobe.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "vpn software lifetime",
        "intent": {"item_category": "software", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["duration:lifetime"]},
        "payload": {"item_description": "Surfshark VPN Lifetime Plan", "item_category": "software", "unit_price": 59.76, "quantity": 1, "vendor": "surfshark.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "check my starbucks gift card balance",
        "intent": {"item_category": "gift_card", "max_price": 5, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Starbucks"]},
        "payload": {"item_description": "Starbucks Gift Card Balance Inquiry (Free)", "item_category": "gift_card", "unit_price": 0.01, "quantity": 1, "vendor": "starbucks.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "transfer itunes gift card balance",
        "intent": {"item_category": "gift_card", "max_price": 10, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Apple"]},
        "payload": {"item_description": "Apple Gift Card $10", "item_category": "gift_card", "unit_price": 10.00, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "extended warranty for my laptop",
        "intent": {"item_category": "warranty", "max_price": 200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "AppleCare+ for MacBook Pro 3-Year Coverage", "item_category": "warranty", "unit_price": 199.00, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "phone screen protection plan",
        "intent": {"item_category": "warranty", "max_price": 100, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Samsung Care+ Screen Repair Plan 2-Year", "item_category": "warranty", "unit_price": 79.00, "quantity": 1, "vendor": "samsung.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "return my amazon order for refund",
        "intent": {"item_category": "return", "max_price": 5, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["retailer:Amazon"]},
        "payload": {"item_description": "Amazon Return Label - Free Return Shipping", "item_category": "return", "unit_price": 0.01, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "get my money back from cancelled flight",
        "intent": {"item_category": "refund", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "United Airlines Refund Request Submission", "item_category": "refund", "unit_price": 0.01, "quantity": 1, "vendor": "united.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "verify my paypal account",
        "intent": {"item_category": "service", "max_price": 10, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["service:PayPal"]},
        "payload": {"item_description": "PayPal Account Verification (Free via PayPal)", "item_category": "service", "unit_price": 0.01, "quantity": 1, "vendor": "paypal.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "age verification for online service",
        "intent": {"item_category": "service", "max_price": 5, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Standard Age Verification via ID.me", "item_category": "service", "unit_price": 0.01, "quantity": 1, "vendor": "id.me", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "find coupon codes for nike",
        "intent": {"item_category": "service", "max_price": 10, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["brand:Nike"]},
        "payload": {"item_description": "Honey Browser Extension - Free Coupon Finder", "item_category": "service", "unit_price": 0.01, "quantity": 1, "vendor": "joinhoney.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "cashback for my purchases",
        "intent": {"item_category": "service", "max_price": 20, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Rakuten Cashback - Free Sign Up Bonus $10", "item_category": "service", "unit_price": 0.01, "quantity": 1, "vendor": "rakuten.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "minecraft java edition",
        "intent": {"item_category": "gaming", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["game:Minecraft"]},
        "payload": {"item_description": "Minecraft: Java & Bedrock Edition for PC", "item_category": "gaming", "unit_price": 29.99, "quantity": 1, "vendor": "minecraft.net", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "windows 11 pro license",
        "intent": {"item_category": "software", "max_price": 200, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["software:Windows 11"]},
        "payload": {"item_description": "Microsoft Windows 11 Pro Full Retail License", "item_category": "software", "unit_price": 199.00, "quantity": 1, "vendor": "microsoft.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "send flowers to mom",
        "intent": {"item_category": "gift", "max_price": 80, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "1-800-Flowers Premium Bouquet with Vase", "item_category": "gift", "unit_price": 59.99, "quantity": 1, "vendor": "1800flowers.com", "currency": "USD", "fees": [{"name": "delivery", "amount": 14.99}], "is_recurring": False},
    },
    {
        "prompt": "birthday cake order",
        "intent": {"item_category": "food", "max_price": 60, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Custom Birthday Cake 8-inch Round from Local Bakery", "item_category": "food", "unit_price": 42.00, "quantity": 1, "vendor": "doordash.com", "currency": "USD", "fees": [{"name": "delivery", "amount": 7.99}], "is_recurring": False},
    },
    {
        "prompt": "cheap desk lamp for office",
        "intent": {"item_category": "furniture", "max_price": 40, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "TaoTronics LED Desk Lamp Eye-Caring", "item_category": "furniture", "unit_price": 29.99, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "phone case with kickstand",
        "intent": {"item_category": "accessories", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Spigen Tough Armor iPhone Case with Kickstand", "item_category": "accessories", "unit_price": 17.99, "quantity": 1, "vendor": "spigen.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "recover my instagram account",
        "intent": {"item_category": "service", "max_price": 25, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["platform:Instagram"]},
        "payload": {"item_description": "Instagram Account Recovery (Free via Instagram Help Center)", "item_category": "service", "unit_price": 0.01, "quantity": 1, "vendor": "instagram.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "unlock my icloud account",
        "intent": {"item_category": "service", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["service:iCloud"]},
        "payload": {"item_description": "Apple iCloud Account Recovery via Apple Support", "item_category": "service", "unit_price": 0.01, "quantity": 1, "vendor": "apple.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "buy a book on python programming",
        "intent": {"item_category": "books", "max_price": 50, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": ["topic:Python"]},
        "payload": {"item_description": "Automate the Boring Stuff with Python 2nd Ed - Al Sweigart", "item_category": "books", "unit_price": 33.99, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "simple phone tripod",
        "intent": {"item_category": "accessories", "max_price": 25, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "UBeesize 50-inch Phone Tripod Stand", "item_category": "accessories", "unit_price": 19.99, "quantity": 1, "vendor": "amazon.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "free credit score check",
        "intent": {"item_category": "service", "max_price": 5, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "Credit Karma Free Credit Score Check", "item_category": "service", "unit_price": 0.01, "quantity": 1, "vendor": "creditkarma.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "background check on someone",
        "intent": {"item_category": "service", "max_price": 30, "currency": "USD", "quantity": 1, "is_recurring": False, "core_constraints": []},
        "payload": {"item_description": "BeenVerified Single Background Report", "item_category": "service", "unit_price": 26.89, "quantity": 1, "vendor": "beenverified.com", "currency": "USD", "fees": [], "is_recurring": False},
    },
    {
        "prompt": "more storage for my google account",
        "intent": {"item_category": "subscription", "max_price": 10, "currency": "USD", "quantity": 1, "is_recurring": True, "core_constraints": ["service:Google"]},
        "payload": {"item_description": "Google One 100GB Storage Plan", "item_category": "subscription", "unit_price": 1.99, "quantity": 1, "vendor": "one.google.com", "currency": "USD", "fees": [], "is_recurring": True},
    },
    {
        "prompt": "upgrade my spotify to premium",
        "intent": {"item_category": "subscription", "max_price": 15, "currency": "USD", "quantity": 1, "is_recurring": True, "core_constraints": ["service:Spotify"]},
        "payload": {"item_description": "Spotify Premium Individual Monthly Plan", "item_category": "subscription", "unit_price": 11.99, "quantity": 1, "vendor": "spotify.com", "currency": "USD", "fees": [], "is_recurring": True},
    },
]


# =============================================================================
# UPLOAD LOGIC
# =============================================================================

def format_prompt_for_classifier(intent: dict, payload: dict) -> str:
    """
    Format the prompt field as the classifier expects:
    "{category} {max_price} {constraints} | {payload_json}"
    """
    constraint_str = " ".join(intent.get("core_constraints", []))
    prompt_text = f"{intent['item_category']} {intent['max_price']} {constraint_str}"

    payload_clean = {k: v for k, v in payload.items() if k != "metadata"}
    payload_json = json.dumps(payload_clean, sort_keys=True, default=str)

    return f"{prompt_text} | {payload_json}"


def prepare_records(attack_list, legit_list, attack_type_default=None):
    """Prepare Supabase records from attack/legit pairs."""
    records = []

    for item in attack_list:
        prompt = format_prompt_for_classifier(item["intent"], item["payload"])
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        records.append({
            "source": "synthetic_redteam_v2",
            "prompt": prompt,
            "intent": item["intent"],
            "payload": item["payload"],
            "is_attack": True,
            "attack_type": item.get("attack_type", attack_type_default),
            "blocked_by": None,
            "confidence": None,
            "human_verified": True,
            "prompt_hash": prompt_hash,
        })

    for item in legit_list:
        prompt = format_prompt_for_classifier(item["intent"], item["payload"])
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        records.append({
            "source": "synthetic_redteam_v2",
            "prompt": prompt,
            "intent": item["intent"],
            "payload": item["payload"],
            "is_attack": False,
            "attack_type": None,
            "blocked_by": None,
            "confidence": None,
            "human_verified": True,
            "prompt_hash": prompt_hash,
        })

    return records


def upload_to_supabase(records):
    """Upload records to Supabase ml_training_data table."""
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        return 0

    client = create_client(url, key)
    uploaded = 0
    errors = 0

    for record in records:
        try:
            client.table("ml_training_data").upsert(
                record,
                on_conflict="prompt_hash"
            ).execute()
            uploaded += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"  Error: {e}")
            elif errors == 4:
                print("  (suppressing further errors...)")

    return uploaded


def main():
    parser = argparse.ArgumentParser(description="Generate VetoNet red team training data v2")
    parser.add_argument("--upload", action="store_true", help="Actually upload to Supabase")
    args = parser.parse_args()

    print("=" * 70)
    print("  VetoNet Red Team Training Data Generator v2")
    print("=" * 70)
    print()

    # Prepare all records
    all_records = []

    categories = [
        ("Price Manipulation", PRICE_MANIPULATION_ATTACKS, PRICE_MANIPULATION_LEGIT, "price_manipulation"),
        ("Category Drift", CATEGORY_DRIFT_ATTACKS, CATEGORY_DRIFT_LEGIT, "category_drift"),
        ("Vendor Spoofing", VENDOR_SPOOFING_ATTACKS, VENDOR_SPOOFING_LEGIT, "vendor_spoofing"),
        ("Description Manipulation", DESCRIPTION_MANIPULATION_ATTACKS, DESCRIPTION_MANIPULATION_LEGIT, "description_manipulation"),
        ("Multi-vector Combo", COMBO_ATTACKS, COMBO_LEGIT, "combo_multi_vector"),
        ("Novel Attacks", NOVEL_ATTACKS, NOVEL_LEGIT, None),
    ]

    for name, attacks, legit, default_type in categories:
        records = prepare_records(attacks, legit, default_type)
        all_records.extend(records)
        attack_count = len(attacks)
        legit_count = len(legit)
        print(f"  {name}:")
        print(f"    Attacks:    {attack_count}")
        print(f"    Legitimate: {legit_count}")
        print(f"    Total:      {attack_count + legit_count}")
        print()

    total_attacks = sum(len(a) for _, a, _, _ in categories)
    total_legit = sum(len(l) for _, _, l, _ in categories)
    total = len(all_records)

    print("-" * 70)
    print(f"  TOTAL:  {total_attacks} attacks + {total_legit} legitimate = {total} records")
    print("-" * 70)
    print()

    # Show attack type distribution
    print("  Attack type distribution:")
    type_counts = {}
    for r in all_records:
        if r["is_attack"]:
            t = r.get("attack_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {t}: {c}")
    print()

    # Check for duplicate hashes
    hashes = [r["prompt_hash"] for r in all_records]
    unique_hashes = set(hashes)
    if len(hashes) != len(unique_hashes):
        print(f"  WARNING: {len(hashes) - len(unique_hashes)} duplicate hashes detected")
    else:
        print(f"  All {len(hashes)} prompt hashes are unique")
    print()

    if args.upload:
        print("  Uploading to Supabase...")
        uploaded = upload_to_supabase(all_records)
        print(f"  Uploaded {uploaded}/{total} records")
    else:
        print("  DRY RUN - no data uploaded.")
        print("  Run with --upload to insert into Supabase ml_training_data table.")
        print()
        print("  Example record (attack):")
        example = next(r for r in all_records if r["is_attack"])
        print(f"    prompt (first 120 chars): {example['prompt'][:120]}...")
        print(f"    is_attack: {example['is_attack']}")
        print(f"    attack_type: {example['attack_type']}")
        print(f"    source: {example['source']}")

    print()
    print("=" * 70)
    print("  Done.")
    print("=" * 70)


if __name__ == "__main__":
    main()
