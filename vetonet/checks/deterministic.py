"""
Deterministic checks for VetoNet.

These checks use pure Python logic with no LLM calls.
They are fast, predictable, and free.
"""

from vetonet.models import IntentAnchor, AgentPayload, CheckResult
from vetonet.config import VetoConfig, DEFAULT_VETO_CONFIG


# Fees that are generally acceptable
ALLOWED_FEES = {"tax", "sales tax", "vat", "shipping", "delivery"}

# Fees that are suspicious
SUSPICIOUS_FEES = {
    "service fee", "processing fee", "convenience fee",
    "handling fee", "platform fee", "admin fee",
    "priority fee", "express fee", "rush fee",
    "insurance", "protection", "warranty",
    "donation", "tip", "gratuity",
}

# Leet speak / obfuscation mapping for fee detection
LEET_MAP = str.maketrans({
    '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
    '7': 't', '@': 'a', '$': 's', '!': 'i',
})


def normalize_fee_name(name: str) -> str:
    """
    Normalize fee name to defeat obfuscation attacks.
    Handles: leet speak, hyphens, underscores, no spaces.
    """
    # Lowercase
    normalized = name.lower()
    # Convert leet speak: s3rvice -> service
    normalized = normalized.translate(LEET_MAP)
    # Remove hyphens and underscores completely (proc-essing -> processing)
    normalized = normalized.replace("-", "").replace("_", "")
    # Collapse multiple spaces
    normalized = " ".join(normalized.split())
    return normalized


def check_price(
    anchor: IntentAnchor,
    payload: AgentPayload,
    config: VetoConfig = DEFAULT_VETO_CONFIG,
) -> CheckResult:
    """
    Check if total transaction price is within the user's budget.

    Now considers: unit_price * quantity + fees
    """
    max_allowed = anchor.max_price * (1 + config.price_tolerance)
    total = payload.total_price

    if total > max_allowed:
        breakdown = f"${payload.unit_price:.2f} x {payload.quantity}"
        if payload.fees:
            breakdown += f" + ${payload.total_fees:.2f} fees"
        return CheckResult(
            name="price",
            passed=False,
            reason=f"Total ${total:.2f} ({breakdown}) exceeds max ${anchor.max_price:.2f}",
        )

    return CheckResult(
        name="price",
        passed=True,
        reason=f"Total ${total:.2f} within budget",
    )


def normalize_category(category: str) -> str:
    """Normalize category for comparison (handles plurals, spaces, etc.)."""
    normalized = category.lower().strip()
    # Remove trailing 's' for plural handling
    if normalized.endswith('s') and not normalized.endswith('ss'):
        normalized = normalized[:-1]
    # Replace spaces and dashes with underscores
    normalized = normalized.replace(" ", "_").replace("-", "_")
    return normalized


def check_category(
    anchor: IntentAnchor,
    payload: AgentPayload,
) -> CheckResult:
    """
    Check if transaction category matches the intent.

    Uses normalized comparison to handle variations like:
    - "gift_card" vs "gift_cards"
    - "Gift Card" vs "gift_card"
    """
    anchor_cat = normalize_category(anchor.item_category)
    payload_cat = normalize_category(payload.item_category)

    if payload_cat != anchor_cat:
        return CheckResult(
            name="category",
            passed=False,
            reason=f"Category mismatch: '{payload.item_category}' != '{anchor.item_category}'",
        )

    return CheckResult(
        name="category",
        passed=True,
        reason="Category matches",
    )


def check_vendor(
    payload: AgentPayload,
    config: VetoConfig = DEFAULT_VETO_CONFIG,
    anchor: IntentAnchor = None,
) -> CheckResult:
    """
    Check if the vendor is trusted or suspicious.

    Checks:
    1. Suspicious TLDs (.ru, .cn, .tk, etc.)
    2. Brand-vendor mismatch (amazon-giftcards.com is NOT amazon.com)
    3. Trusted vendor allowlist (optional)
    """
    vendor_lower = payload.vendor.lower()

    # Check for suspicious TLDs
    for tld in config.suspicious_tlds:
        if vendor_lower.endswith(tld):
            return CheckResult(
                name="vendor",
                passed=False,
                reason=f"Vendor '{payload.vendor}' has suspicious TLD '{tld}'",
            )

    # NEW: Check brand-vendor match
    # If intent specifies a brand, vendor must be the official domain
    if anchor and anchor.core_constraints:
        for constraint in anchor.core_constraints:
            if constraint.lower().startswith("brand:"):
                brand = constraint.split(":", 1)[1].lower().strip()

                # Map known brands to their official domains
                # Expanded list based on attack report findings
                official_domains = {
                    # Original 12
                    "amazon": ["amazon.com", "amazon.co.uk", "amazon.de", "amazon.ca", "amazon.fr"],
                    "apple": ["apple.com", "store.apple.com"],
                    "google": ["google.com", "play.google.com", "store.google.com"],
                    "netflix": ["netflix.com"],
                    "spotify": ["spotify.com"],
                    "nike": ["nike.com"],
                    "steam": ["steampowered.com", "store.steampowered.com"],
                    "playstation": ["playstation.com", "store.playstation.com"],
                    "xbox": ["xbox.com", "microsoft.com"],
                    "walmart": ["walmart.com"],
                    "target": ["target.com"],
                    "bestbuy": ["bestbuy.com"],
                    "ebay": ["ebay.com"],
                    # Added to prevent unlisted brand spoofing
                    "visa": ["visa.com", "usa.visa.com"],
                    "mastercard": ["mastercard.com", "mastercard.us"],
                    "starbucks": ["starbucks.com"],
                    "uber": ["uber.com"],
                    "lyft": ["lyft.com"],
                    "doordash": ["doordash.com"],
                    "grubhub": ["grubhub.com"],
                    "airbnb": ["airbnb.com"],
                    "sephora": ["sephora.com"],
                    "nordstrom": ["nordstrom.com"],
                    "adidas": ["adidas.com"],
                    "footlocker": ["footlocker.com"],
                    "gamestop": ["gamestop.com"],
                    "home depot": ["homedepot.com"],
                    "lowes": ["lowes.com"],
                    "costco": ["costco.com"],
                    "microsoft": ["microsoft.com", "store.microsoft.com"],
                    "hulu": ["hulu.com"],
                    "disney": ["disney.com", "disneyplus.com"],
                    "paramount": ["paramount.com", "paramountplus.com"],
                }

                if brand in official_domains:
                    is_official = any(vendor_lower == domain or vendor_lower.endswith("." + domain)
                                     for domain in official_domains[brand])
                    if not is_official:
                        return CheckResult(
                            name="vendor",
                            passed=False,
                            reason=f"Vendor '{payload.vendor}' is not official {brand.title()} domain. Expected: {official_domains[brand][0]}",
                        )

    # Check if trusted (informational, doesn't fail)
    is_trusted = vendor_lower in config.trusted_vendors
    status = "trusted" if is_trusted else "unknown"

    return CheckResult(
        name="vendor",
        passed=True,
        reason=f"Vendor '{payload.vendor}' is {status}",
    )


def check_price_anomaly(
    anchor: IntentAnchor,
    payload: AgentPayload,
    config: VetoConfig = DEFAULT_VETO_CONFIG,
) -> CheckResult:
    """
    Detect suspiciously low prices that indicate scams.

    If the price is significantly below the expected range,
    it's likely too good to be true.
    """
    threshold = anchor.max_price * config.price_anomaly_threshold

    if payload.unit_price < threshold:
        return CheckResult(
            name="price_anomaly",
            passed=False,
            reason=f"Unit price ${payload.unit_price:.2f} suspiciously low (< {config.price_anomaly_threshold:.0%} of ${anchor.max_price:.2f})",
        )

    return CheckResult(
        name="price_anomaly",
        passed=True,
        reason="Price within normal range",
    )


def check_quantity(
    anchor: IntentAnchor,
    payload: AgentPayload,
) -> CheckResult:
    """
    Check if quantity matches the user's intent.

    Catches attacks where agent orders more items than requested.
    """
    if payload.quantity > anchor.quantity:
        return CheckResult(
            name="quantity",
            passed=False,
            reason=f"Quantity {payload.quantity} exceeds requested {anchor.quantity}",
        )

    if payload.quantity < anchor.quantity:
        return CheckResult(
            name="quantity",
            passed=False,
            reason=f"Quantity {payload.quantity} less than requested {anchor.quantity}",
        )

    return CheckResult(
        name="quantity",
        passed=True,
        reason=f"Quantity matches ({payload.quantity})",
    )


def check_hidden_fees(
    payload: AgentPayload,
) -> CheckResult:
    """
    Detect suspicious hidden fees.

    Catches attacks where agent adds unauthorized fees like
    'service fee', 'processing fee', 'insurance', etc.

    Now handles obfuscation attempts like:
    - Leet speak: s3rvice -> service
    - Hyphenation: proc-essing -> processing
    - No spaces: conveniencefee -> convenience fee
    """
    suspicious_found = []

    for fee in payload.fees:
        # Normalize fee name to defeat obfuscation
        fee_name_normalized = normalize_fee_name(fee.name)
        fee_name_no_spaces = fee_name_normalized.replace(" ", "")

        # Check against suspicious fee patterns
        for suspicious in SUSPICIOUS_FEES:
            suspicious_no_spaces = suspicious.replace(" ", "")
            # Match either with or without spaces
            if suspicious in fee_name_normalized or suspicious_no_spaces in fee_name_no_spaces:
                suspicious_found.append(f"{fee.name}: ${fee.amount:.2f}")
                break

    if suspicious_found:
        return CheckResult(
            name="hidden_fees",
            passed=False,
            reason=f"Suspicious fees detected: {', '.join(suspicious_found)}",
        )

    return CheckResult(
        name="hidden_fees",
        passed=True,
        reason="No suspicious fees",
    )


def check_subscription_trap(
    anchor: IntentAnchor,
    payload: AgentPayload,
) -> CheckResult:
    """
    Detect subscription/recurring charge traps.

    Catches attacks where agent converts a one-time purchase
    into a recurring subscription.
    """
    if payload.is_recurring and not anchor.is_recurring:
        return CheckResult(
            name="subscription_trap",
            passed=False,
            reason="Transaction is recurring but user requested one-time purchase",
        )

    if not payload.is_recurring and anchor.is_recurring:
        return CheckResult(
            name="subscription_trap",
            passed=False,
            reason="Transaction is one-time but user requested subscription",
        )

    return CheckResult(
        name="subscription_trap",
        passed=True,
        reason="Recurring status matches intent",
    )


def check_currency_manipulation(
    anchor: IntentAnchor,
    payload: AgentPayload,
) -> CheckResult:
    """
    Detect currency manipulation attacks.

    Catches attacks where agent charges in a different currency,
    potentially at unfavorable exchange rates.
    """
    if payload.currency.upper() != anchor.currency.upper():
        return CheckResult(
            name="currency_manipulation",
            passed=False,
            reason=f"Currency mismatch: charging in {payload.currency} but user specified {anchor.currency}",
        )

    return CheckResult(
        name="currency_manipulation",
        passed=True,
        reason="Currency matches",
    )


# Suspicious email patterns commonly used in gift card scams
SCAM_EMAIL_PATTERNS = [
    r'urgent[._-]?payment',
    r'payment[._-]?required',
    r'irs[._-]?payment',
    r'tax[._-]?payment',
    r'tech[._-]?support',
    r'microsoft[._-]?support',
    r'apple[._-]?support',
    r'amazon[._-]?support',
    r'refund[._-]?dept',
    r'lottery[._-]?winner',
    r'prize[._-]?claim',
    r'emergency[._-]?fund',
    r'bitcoin[._-]?payment',
    r'crypto[._-]?transfer',
    r'wire[._-]?transfer',
    r'western[._-]?union',
    r'moneygram',
    r'gift[._-]?card[._-]?payment',
]

# Suspicious phrases in gift card descriptions
SCAM_DESCRIPTION_PATTERNS = [
    r'send\s+to\s*:\s*\S+@\S+',  # "send to: email@domain"
    r'email\s+to\s*:\s*\S+@\S+',  # "email to: email@domain"
    r'recipient\s*:\s*\S+@\S+',  # "recipient: email@domain"
    r'deliver\s+to\s*:\s*\S+@\S+',  # "deliver to: email@domain"
    r'for\s*:\s*\S+@\S+',  # "for: email@domain"
    r'@(gmail|yahoo|hotmail|outlook|protonmail)\.(com|net|org)',  # Common free email providers in description
    r'whatsapp\s*[+:]?\s*[\d\-\s]+',  # WhatsApp numbers
    r'telegram\s*[+:]?\s*[@\w]+',  # Telegram handles
    r'call\s+(me|us|back)\s+at',  # Call back scams
    r'(urgent|immediate|asap|emergency)\s+(payment|transfer|send)',  # Urgency language
    r'(irs|fbi|ssa|dea|ice)\s+(payment|fine|penalty)',  # Government impersonation
    r'(arrest|warrant|lawsuit)\s+',  # Legal threats
    r'(lottery|sweepstakes|prize|winner)\s+(claim|fee|payment)',  # Lottery scams
    r'(processing|activation|release)\s+fee',  # Fake fees
    r'(guaranteed|instant)\s+(return|profit|income)',  # Investment scams
    r'\+1[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{4}',  # US phone numbers
    r'\+\d{1,3}[-\s]?\d{6,12}',  # International phone numbers
]

# Nigerian prince / advance fee scam patterns
ADVANCE_FEE_SCAM_PATTERNS = [
    r'(prince|princess|king|royal|minister|diplomat)\s+(of\s+)?(nigeria|africa|ghana|congo|sudan)',
    r'(inheritance|estate|fortune|fund|money)\s+(of|worth|valued)\s+\$?\d+\s*(million|billion|m|b)',
    r'(deceased|late|departed)\s+(father|mother|uncle|relative|client|businessman)',
    r'(bank|account|fund)\s+in\s+(africa|nigeria|ghana|overseas)',
    r'(transfer|move|release)\s+(the\s+)?(fund|money|inheritance|estate)',
    r'(processing|transfer|legal|documentation)\s+fee',
    r'(stranded|stuck|trapped)\s+(fund|money|inheritance)',
    r'(confidential|secret|private)\s+(business|transaction|deal|proposal)',
    r'(god|blessing|divine)\s+(has\s+)?(directed|led|chosen)',
    r'(widow|orphan)\s+of\s+(late|deceased)',
    r'(oil|gold|diamond)\s+(contract|deal|business)',
    r'100%\s+(safe|secure|risk.?free)',
    r'(your\s+)?share.*(\d+|percent|%)',
]

# Grandparent / family emergency scam patterns
GRANDPARENT_SCAM_PATTERNS = [
    r'(grandma|grandpa|grandmother|grandfather|nana|papa|granny)',
    r'(grandson|granddaughter|grandchild)',
    r'(bail|jail|arrested|accident|hospital|emergency)',
    r"(don't|do\s*not)\s+(tell|inform)\s+(mom|dad|parents|anyone)",
    r'(please\s+)?keep\s+(this\s+)?(secret|quiet|between\s+us)',
    r'(in\s+)?(trouble|jail|arrested|custody)',
    r'(car\s+)?accident.*(need|send|wire)',
    r'(broken|hurt|injured).*(hospital|medical)',
    r'lawyer\s+(said|told|needs)',
    r'(must|need\s+to)\s+pay\s+(today|now|immediately|asap)',
    r'(western\s+union|moneygram|wire|gift\s+card)',
]

# Tech support scam patterns
TECH_SUPPORT_SCAM_PATTERNS = [
    r'(computer|pc|mac|device)\s+(is\s+)?(infected|hacked|compromised|at\s+risk)',
    r'(virus|malware|trojan|ransomware)\s+(detected|found|alert)',
    r'(microsoft|apple|google|windows|norton|mcafee)\s+(support|technician|security)',
    r'(remote\s+)?(access|control)\s+(to\s+)?(your\s+)?(computer|device)',
    r'(security\s+)?subscription\s+(expired|renew)',
    r'(refund|overpayment|overcharge).*(remote|access)',
    r'(call|contact)\s+(this\s+)?(number|support)',
    r'(your\s+)?(ip|computer)\s+(has\s+)?(been\s+)?(flagged|blocked|reported)',
    r'(unauthorized|suspicious)\s+(activity|login|access)',
]

# Romance scam patterns
ROMANCE_SCAM_PATTERNS = [
    r'(met|found)\s+(online|dating|app|website)',
    r'(send|wire|transfer)\s+(money|fund)',
    r"(can't|cannot)\s+(meet|video\s+call|facetime)",
    r'(military|deployed|overseas|oil\s+rig|ship|platform)',
    r'(stuck|stranded)\s+(in|at)\s+(airport|overseas|abroad)',
    r'(customs|duty|fee)\s+(to\s+)?(release|ship|send)',
    r'(plane|flight)\s+ticket',
    r'(medical|hospital|surgery)\s+(bill|emergency)',
    r'(investment|business)\s+(opportunity|deal)',
    r'(prove|show)\s+(your\s+)?(love|trust|commitment)',
    r'(please\s+)?trust\s+me',
    r'(our\s+)?(future|life)\s+together',
]

# Market value expectations for common high-value items (minimum realistic price)
# If an item sells for WAY below this, it's likely a scam
# NOTE: Only include items where low price is ALWAYS suspicious
# Exclude rentable items (yacht, car, boat) - $300 yacht RENTAL is fine
MARKET_VALUE_MINIMUMS = {
    # Electronics - these are never rented, always purchased
    "iphone": 400,
    "ipad": 250,
    "macbook": 600,
    "airpods": 80,
    "apple watch": 150,
    "samsung galaxy": 300,
    "ps5": 350,
    "playstation 5": 350,
    "playstation5": 350,
    "xbox series": 300,
    "nintendo switch": 200,
    "rtx 4090": 1200,
    "rtx 4080": 800,
    "rtx 3090": 600,
    "gpu": 150,
    "graphics card": 150,
    "laptop": 200,
    "gaming pc": 500,
    "gaming computer": 500,
    # Luxury items - counterfeits are the scam, not rentals
    "rolex": 3000,
    "omega": 1500,
    "louis vuitton": 500,
    "gucci": 300,
    "hermes": 500,
    "chanel": 500,
    "prada": 300,
}


def check_scam_patterns(
    payload: AgentPayload,
) -> CheckResult:
    """
    Detect common scam patterns in transaction descriptions.

    Catches attacks like:
    - Gift card scams (send to suspicious email)
    - Tech support scams
    - IRS/government impersonation
    - Lottery/prize scams
    - Romance scams (emergency funds)
    - Nigerian prince / advance fee scams
    - Grandparent / family emergency scams

    This is a DETERMINISTIC check - no LLM variance, 100% reliable.
    """
    import re

    description_lower = payload.item_description.lower()

    # Check for suspicious email patterns
    for pattern in SCAM_EMAIL_PATTERNS:
        if re.search(pattern, description_lower, re.IGNORECASE):
            return CheckResult(
                name="scam_pattern",
                passed=False,
                reason=f"Suspicious scam pattern detected in description",
            )

    # Check for suspicious description patterns
    for pattern in SCAM_DESCRIPTION_PATTERNS:
        if re.search(pattern, description_lower, re.IGNORECASE):
            match = re.search(pattern, description_lower, re.IGNORECASE)
            matched_text = match.group(0) if match else "pattern"
            return CheckResult(
                name="scam_pattern",
                passed=False,
                reason=f"Suspicious content detected: '{matched_text[:50]}'",
            )

    # Check for Nigerian prince / advance fee scam patterns
    for pattern in ADVANCE_FEE_SCAM_PATTERNS:
        if re.search(pattern, description_lower, re.IGNORECASE):
            match = re.search(pattern, description_lower, re.IGNORECASE)
            matched_text = match.group(0) if match else "advance fee pattern"
            return CheckResult(
                name="scam_pattern",
                passed=False,
                reason=f"Advance fee scam pattern detected: '{matched_text[:50]}'",
            )

    # Check for grandparent / family emergency scam patterns
    grandparent_matches = 0
    for pattern in GRANDPARENT_SCAM_PATTERNS:
        if re.search(pattern, description_lower, re.IGNORECASE):
            grandparent_matches += 1
    # Need at least 2 matches to flag (e.g., "grandma" + "bail" or "arrested" + "don't tell")
    if grandparent_matches >= 2:
        return CheckResult(
            name="scam_pattern",
            passed=False,
            reason=f"Family emergency scam pattern detected (grandparent scam)",
        )

    # Check for tech support scam patterns
    tech_support_matches = 0
    for pattern in TECH_SUPPORT_SCAM_PATTERNS:
        if re.search(pattern, description_lower, re.IGNORECASE):
            tech_support_matches += 1
    if tech_support_matches >= 2:
        return CheckResult(
            name="scam_pattern",
            passed=False,
            reason=f"Tech support scam pattern detected",
        )

    # Check for romance scam patterns
    romance_matches = 0
    for pattern in ROMANCE_SCAM_PATTERNS:
        if re.search(pattern, description_lower, re.IGNORECASE):
            romance_matches += 1
    if romance_matches >= 2:
        return CheckResult(
            name="scam_pattern",
            passed=False,
            reason=f"Romance scam pattern detected",
        )

    # Special check: Gift cards with external email recipients
    # Gift cards should be added to your own account, not sent to random emails
    if payload.item_category and 'gift' in payload.item_category.lower():
        # Check if there's any email address in the description
        email_match = re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', payload.item_description)
        if email_match:
            email = email_match.group(0)
            # Flag any email that looks suspicious
            suspicious_words = ['urgent', 'payment', 'required', 'support', 'help', 'claim', 'prize', 'winner', 'irs', 'tax']
            if any(word in email.lower() for word in suspicious_words):
                return CheckResult(
                    name="scam_pattern",
                    passed=False,
                    reason=f"Gift card sent to suspicious email: {email}",
                )

    return CheckResult(
        name="scam_pattern",
        passed=True,
        reason="No scam patterns detected",
    )


def check_market_value(
    payload: AgentPayload,
) -> CheckResult:
    """
    Detect suspiciously cheap items based on known market values.

    Catches attacks like:
    - $1 iPhone (market value: $400+)
    - $20 PS5 (market value: $350+)
    - $499 Rolex (market value: $3,000+)

    This is independent of user's max_price - it checks absolute market reality.

    NOTE: Skips rental/reservation items - $300 yacht RENTAL is fine,
    $300 yacht PURCHASE is a scam. This nuance requires semantic understanding.
    """
    import re

    description_lower = payload.item_description.lower()
    category_lower = (payload.item_category or "").lower()
    unit_price = payload.unit_price

    # Skip for rentals/reservations - pricing is completely different
    # $300/day yacht rental is normal, $300 yacht purchase is a scam
    rental_keywords = [
        'rental', 'rent', 'reservation', 'reserve', 'booking', 'book',
        'per day', 'per night', 'per hour', '/day', '/night', '/hour',
        'for 1 day', 'for 2 day', 'for 3 day', 'for 4 day', 'for 5 day',
        'for 1 night', 'for 2 night', 'for 3 night',
        'charter', 'hire', 'lease',
    ]

    if any(kw in description_lower or kw in category_lower for kw in rental_keywords):
        return CheckResult(
            name="market_value",
            passed=True,
            reason="Rental/reservation - market value check skipped",
        )

    # Check each known item against market minimums
    # Use word boundaries to avoid false positives (e.g., "car" in "gift card")
    for item_name, min_price in MARKET_VALUE_MINIMUMS.items():
        # Create regex pattern with word boundaries
        pattern = r'\b' + re.escape(item_name) + r'\b'
        if re.search(pattern, description_lower):
            if unit_price < min_price * 0.5:  # Allow 50% off (sales/used), but not 90% off
                return CheckResult(
                    name="market_value",
                    passed=False,
                    reason=f"Price ${unit_price:.2f} unrealistic for '{item_name}' (market minimum ~${min_price})",
                )

    return CheckResult(
        name="market_value",
        passed=True,
        reason="Price within realistic market range",
    )


# Crypto asset equivalence map - assets that users commonly confuse
# Key: what user might ask for, Value: list of NOT-equivalent assets
CRYPTO_SUBSTITUTIONS = {
    # Bitcoin variants - NOT the same
    "btc": ["wbtc", "wrapped bitcoin", "bitcoin cash", "bch", "bitcoin sv", "bsv", "rbtc", "renbtc", "tbtc", "hbtc", "sbtc"],
    "bitcoin": ["wbtc", "wrapped bitcoin", "bitcoin cash", "bch", "bitcoin sv", "bsv", "rbtc", "renbtc", "tbtc", "hbtc", "sbtc", "bitcoin gold", "btg"],

    # Ethereum variants - NOT the same
    "eth": ["weth", "steth", "reth", "cbeth", "eth2", "ethereum classic", "etc", "lido staked ether", "rocket pool eth"],
    "ethereum": ["weth", "wrapped ether", "steth", "staked ether", "reth", "ethereum classic", "etc", "lido", "rocket pool"],

    # Stablecoins - NOT equivalent despite being "stable"
    "usdc": ["usdt", "dai", "busd", "tusd", "usdp", "frax", "ust", "terrausd", "gusd", "lusd"],
    "usdt": ["usdc", "dai", "busd", "tusd", "usdp", "frax", "ust", "terrausd", "gusd", "lusd"],
    "dai": ["usdc", "usdt", "busd", "tusd", "usdp", "frax", "ust"],

    # Common high-value crypto
    "sol": ["wsol", "wrapped sol", "solana"],
    "solana": ["wsol", "wrapped sol"],
    "bnb": ["wbnb", "wrapped bnb"],
    "avax": ["wavax", "wrapped avax"],
    "matic": ["wmatic", "wrapped matic", "polygon"],
}


def check_crypto_substitution(
    anchor: IntentAnchor,
    payload: AgentPayload,
) -> CheckResult:
    """
    Detect crypto asset substitution attacks.

    Catches attacks where:
    - User asks for BTC, gets WBTC (wrapped Bitcoin - different risk profile)
    - User asks for ETH, gets stETH (staked ETH - illiquid, smart contract risk)
    - User asks for USDC, gets UST (now worthless)

    This is critical for crypto transactions where asset equivalence is NOT assumed.
    """
    # Only apply to crypto-related categories
    crypto_categories = {"crypto", "cryptocurrency", "bitcoin", "ethereum", "token", "coin", "defi"}

    category_lower = (anchor.item_category or "").lower()
    if not any(cat in category_lower for cat in crypto_categories):
        # Also check if description mentions crypto
        desc_lower = (payload.item_description or "").lower()
        if not any(crypto in desc_lower for crypto in ["btc", "bitcoin", "eth", "ethereum", "usdc", "usdt", "crypto", "token", "coin"]):
            return CheckResult(
                name="crypto_substitution",
                passed=True,
                reason="Not a crypto transaction",
            )

    # Extract what the user likely wanted from category
    category_lower = category_lower.replace("cryptocurrency", "").replace("crypto", "").strip()
    desc_lower = (payload.item_description or "").lower()

    # Check each crypto asset for substitution
    for intended_asset, bad_substitutes in CRYPTO_SUBSTITUTIONS.items():
        # Check if user's intent includes this asset
        if intended_asset in category_lower:
            # Check if payload description has a substitute
            for substitute in bad_substitutes:
                if substitute in desc_lower:
                    return CheckResult(
                        name="crypto_substitution",
                        passed=False,
                        reason=f"Crypto asset mismatch: requested '{intended_asset.upper()}' but getting '{substitute.upper()}' - these are different assets with different risks",
                    )

    # Also check item description for common patterns
    # e.g., description says "WBTC" when it should say "BTC"
    for intended_asset, bad_substitutes in CRYPTO_SUBSTITUTIONS.items():
        for substitute in bad_substitutes:
            # If description contains wrapped/staked version, check if it's what was intended
            if substitute in desc_lower:
                # Check if the original asset was mentioned in category or constraints
                if intended_asset in category_lower:
                    return CheckResult(
                        name="crypto_substitution",
                        passed=False,
                        reason=f"Crypto asset mismatch: likely wanted '{intended_asset.upper()}' but receiving '{substitute.upper()}'",
                    )

    # Final check: if description contains a wrapped/derivative asset, flag it
    # These are inherently suspicious unless explicitly requested
    WRAPPED_DERIVATIVES = [
        "wbtc", "wrapped bitcoin", "rbtc", "renbtc", "tbtc", "hbtc",
        "weth", "wrapped ether", "steth", "staked ether", "reth", "cbeth",
        "wsol", "wrapped sol",
        "wbnb", "wrapped bnb",
        "wavax", "wrapped avax",
        "wmatic", "wrapped matic",
    ]

    for derivative in WRAPPED_DERIVATIVES:
        if derivative in desc_lower:
            # Get the base asset
            base = derivative.replace("wrapped ", "").replace("staked ", "").replace("w", "", 1).upper()
            if base in ["BTC", "ETH", "SOL", "BNB", "AVAX", "MATIC"]:
                return CheckResult(
                    name="crypto_substitution",
                    passed=False,
                    reason=f"Wrapped/derivative crypto asset detected: '{derivative.upper()}' - this is NOT the same as {base} and has additional risks",
                )

    return CheckResult(
        name="crypto_substitution",
        passed=True,
        reason="No crypto asset substitution detected",
    )
